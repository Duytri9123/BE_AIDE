"""
Cabinet Sheet Processor & CAD Sanitizer Service
------------------------------------------------
Dịch vụ xử lý, trích xuất và làm sạch bản vẽ CAD tủ điện:
1. clean_equipment_blocks: Loại bỏ nhãn tên/thông số kỹ thuật text thừa bên trong
   các block thiết bị (MCB, MCCB, rơ le, chống sét, phụ kiện...), ngăn ngừa tình trạng
   chữ bị xoay dọc, lộn ngược hoặc đè lên thanh cái và chi tiết cơ khí.
   Bảo toàn 100% Khung bản vẽ, Bảng thông số kỹ thuật và các Dimension kích thước.
2. extract_sheet: Trích xuất khung bản vẽ chính xác bằng bounding box hình học
   (bbox.extents) với ngưỡng dung sai (boundary tolerance), loại bỏ khung bản vẽ lân cận.
3. render_highres_previews: Kết xuất SVG (inlined CSS) và PNG độ phân giải cao 2800px.
"""
from __future__ import annotations

import io
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple, Union

import ezdxf
from ezdxf import bbox
from ezdxf.addons.drawing import Frontend, RenderContext, svg, layout
from ezdxf.addons.drawing.config import Configuration, ColorPolicy, BackgroundPolicy

PRESERVE_TITLE_KEYWORDS = [
    'khung', 'bảng', 'bang', 'thông số', 'thong so',
    'tuan anh', 'tuananh', 'a$c4', 'title', 'border',
    'logo', 'stam', 'khungten', 'khungchuan'
]


def clean_equipment_blocks(
    doc: ezdxf.document.Drawing,
    preserve_keywords: Optional[List[str]] = None
) -> int:
    """
    Xóa toàn bộ ký hiệu chữ (TEXT, MTEXT, ATTRIB, ATTDEF) bên trong các block thiết bị.
    Giữ lại hình học cơ khí (đường bao, cần gạt, cực đấu nối, vít bắt thanh cái).
    Bảo toàn block kích thước (*D...) và khung tên/bảng thông số kỹ thuật.
    """
    keywords = [k.lower() for k in (preserve_keywords or PRESERVE_TITLE_KEYWORDS)]
    deleted_count = 0

    for b in doc.blocks:
        name = b.name
        # Bỏ qua Layout Spaces
        if name.startswith('*Model_Space') or name.startswith('*Paper_Space'):
            continue
        # Bỏ qua block kích thước dimension
        if name.startswith('*D') or name.startswith('*d'):
            continue
        # Bỏ qua Khung tên và Bảng thông số
        name_lower = name.lower()
        if any(k in name_lower for k in keywords):
            continue

        # Xóa nhãn text thừa trong block thiết bị
        to_delete = [e for e in b if e.dxftype() in ('TEXT', 'MTEXT', 'ATTRIB', 'ATTDEF')]
        for e in to_delete:
            b.delete_entity(e)
            deleted_count += 1

    return deleted_count


def extract_sheet(
    source_dxf_path: Union[str, Path],
    output_dxf_path: Union[str, Path],
    sheet_bounds: Optional[Tuple[float, float, float, float]] = None,
    clean_equipment: bool = True
) -> dict:
    """
    Trích xuất một khung bản vẽ đơn lẻ từ file DXF nguồn có nhiều sheet hoặc vùng lân cận.
    - Dùng bbox.extents([e]) để kiểm tra giao cắt hình học thực tế.
    - Dung sai lọc cạnh lân cận: tolerance = 5.0 mm.
    - Tự động tịnh tiến gốc tọa độ về (0, 0).
    - Làm sạch ký hiệu chữ trên thiết bị nếu clean_equipment = True.
    """
    source_path = Path(source_dxf_path)
    output_path = Path(output_dxf_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = ezdxf.readfile(str(source_path))
    msp = doc.modelspace()

    # Nếu có sheet_bounds (xmin, ymin, xmax, ymax)
    if sheet_bounds:
        xmin, ymin, xmax, ymax = sheet_bounds
        tol = 5.0
        to_delete = []
        for e in msp:
            try:
                b = bbox.extents([e])
                if not b.has_data:
                    continue
                # Nếu nằm hoàn toàn bên ngoài sheet
                if b.extmax.x <= (xmin + tol) or b.extmin.x >= (xmax - tol) or \
                   b.extmax.y <= (ymin + tol) or b.extmin.y >= (ymax - tol):
                    to_delete.append(e)
            except Exception:
                pass

        for e in to_delete:
            msp.delete_entity(e)

        # Dịch chuyển về (0, 0)
        if xmin != 0.0 or ymin != 0.0:
            for e in msp:
                try:
                    e.translate(-xmin, -ymin, 0)
                except Exception:
                    pass

    # Làm sạch text thiết bị
    deleted_texts = 0
    if clean_equipment:
        deleted_texts = clean_equipment_blocks(doc)

    doc.update_extents()
    doc.saveas(str(output_path))

    final_box = bbox.extents(msp)
    return {
        "output_path": str(output_path),
        "deleted_equipment_texts": deleted_texts,
        "width": final_box.size.x if final_box.has_data else 0.0,
        "height": final_box.size.y if final_box.has_data else 0.0,
        "extmin": (final_box.extmin.x, final_box.extmin.y) if final_box.has_data else (0.0, 0.0),
        "extmax": (final_box.extmax.x, final_box.extmax.y) if final_box.has_data else (0.0, 0.0),
    }


def render_highres_previews(
    dxf_path: Union[str, Path],
    svg_path: Union[str, Path],
    png_path: Union[str, Path],
    sheet_width: float = 5346.0,
    sheet_height: float = 3781.0,
    png_width: int = 2800,
    python_ocr_bin: Optional[str] = None
) -> dict:
    """
    Kết xuất file SVG (inlined CSS) và file PNG chất lượng cao.
    """
    dxf_p = Path(dxf_path)
    svg_p = Path(svg_path)
    png_p = Path(png_path)
    svg_p.parent.mkdir(parents=True, exist_ok=True)
    png_p.parent.mkdir(parents=True, exist_ok=True)

    doc = ezdxf.readfile(str(dxf_p))
    msp = doc.modelspace()

    # 1. Render SVG
    backend = svg.SVGBackend()
    cfg = Configuration(
        color_policy=ColorPolicy.COLOR,
        background_policy=BackgroundPolicy.BLACK,
        min_lineweight=0.35,
        lineweight_scaling=2.0
    )
    frontend = Frontend(RenderContext(doc), backend, config=cfg)
    frontend.draw_layout(msp)

    page = layout.Page(width=sheet_width, height=sheet_height, units=layout.Units.mm, margins=layout.Margins(0, 0, 0, 0))
    svg_raw = backend.get_string(page)

    # Inline CSS class attributes into paths
    styles = {}
    for m in re.finditer(r'\.([A-Za-z0-9]+)\s*\{([^}]+)\}', svg_raw):
        cls_name = m.group(1)
        props_str = m.group(2)
        props = {}
        for p in props_str.split(';'):
            p = p.strip()
            if ':' in p:
                k, v = p.split(':', 1)
                props[k.strip()] = v.strip()
        styles[cls_name] = props

    def repl_path(m):
        full_tag = m.group(0)
        cls_match = re.search(r'class="([^"]+)"', full_tag)
        if not cls_match:
            return full_tag
        cls = cls_match.group(1)
        st = styles.get(cls, {})
        stroke = st.get('stroke', 'none')
        stroke_w = st.get('stroke-width', 'none')
        stroke_op = st.get('stroke-opacity', '1')
        fill = st.get('fill', 'none')
        fill_op = st.get('fill-opacity', '1')

        if stroke_w != 'none':
            try:
                w_val = float(stroke_w)
                w_val = max(550, int(w_val * 12))
                stroke_w = str(w_val)
            except Exception:
                stroke_w = '550'

        attribs = []
        if stroke != 'none':
            attribs.append(f'stroke="{stroke}"')
            attribs.append(f'stroke-width="{stroke_w}"')
            if stroke_op != '1':
                attribs.append(f'stroke-opacity="{stroke_op}"')
        else:
            attribs.append('stroke="none"')

        if fill != 'none':
            attribs.append(f'fill="{fill}"')
            if fill_op != '1':
                attribs.append(f'fill-opacity="{fill_op}"')
        else:
            attribs.append('fill="none"')

        return re.sub(r'class="[^"]+"', ' '.join(attribs), full_tag)

    svg_inlined = re.sub(r'<path\s+[^>]+>', repl_path, svg_raw)
    svg_p.write_text(svg_inlined, encoding='utf-8')

    # 2. Render PNG via PyMuPDF (fitz)
    py_bin = python_ocr_bin or r'BE_AIDE/.venv-ocr/Scripts/python.exe'
    render_code = f"""
import fitz
doc_pdf = fitz.open(r'{svg_p}')
p0 = doc_pdf[0]
scale = {png_width} / p0.rect.width
pix = p0.get_pixmap(matrix=fitz.Matrix(scale, scale))
pix.save(r'{png_p}')
"""
    try:
        subprocess.run([py_bin, '-c', render_code], check=True, capture_output=True)
    except Exception as exc:
        # Fallback to direct import if inside environment
        try:
            import fitz
            doc_pdf = fitz.open(str(svg_p))
            p0 = doc_pdf[0]
            scale = png_width / p0.rect.width
            pix = p0.get_pixmap(matrix=fitz.Matrix(scale, scale))
            pix.save(str(png_p))
        except Exception as inner_exc:
            pass

    return {
        "svg_path": str(svg_p),
        "png_path": str(png_p),
        "svg_size": svg_p.stat().st_size if svg_p.exists() else 0,
        "png_size": png_p.stat().st_size if png_p.exists() else 0,
    }

