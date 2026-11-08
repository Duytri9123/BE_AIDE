
"""EL chooses actual registered tools; the browser renders their real activity."""
import asyncio
import json
import hashlib

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.project import Project
from app.schemas.ai import ChatRequest
from app.services.ai.connection_pool import ConnectionPoolService
from app.services.ai.vision_analyzer import VisionAnalyzerService
from app.services.ai.response_parser import ResponseParserService
from app.services.ai.el_tools import api_tools, execute_api_tool, permits_tool

router = APIRouter()


async def owned_project(db, user, project_id):
    if (await db.execute(select(Project.id).where(Project.id == project_id,
        Project.user_id == user.id, Project.deleted_at.is_(None)))).scalar_one_or_none() is None:
        raise HTTPException(404, 'Dự án không tồn tại.')


def resolve_tool_match(chosen_name: str, candidate_tools: list) -> dict | None:
    if not chosen_name or not isinstance(chosen_name, str):
        return None
    name_clean = chosen_name.strip()
    name_lower = name_clean.lower()
    for t in candidate_tools:
        if t.get('name') == name_clean:
            return t
    for t in candidate_tools:
        if t.get('name', '').lower() == name_lower:
            return t
    cad_variant = f"cad_{name_clean}" if not name_clean.startswith("cad_") else name_clean[4:]
    for t in candidate_tools:
        if t.get('name') == cad_variant or t.get('name', '').lower() == cad_variant.lower():
            return t
    if name_lower.endswith('s'):
        singular = name_lower[:-1]
        for t in candidate_tools:
            if t.get('name', '').lower() == singular:
                return t
    else:
        plural = name_lower + 's'
        for t in candidate_tools:
            if t.get('name', '').lower() == plural:
                return t
    for t in candidate_tools:
        if t.get('label', '').lower() == name_lower:
            return t
    normalized_query = name_lower.removeprefix('api_').strip('_')
    for t in candidate_tools:
        cand_name = t.get('name', '').lower()
        cand_norm = cand_name.removeprefix('api_').strip('_')
        if cand_norm.startswith(normalized_query) or normalized_query in cand_norm.split('_'):
            return t
    for t in candidate_tools:
        cand_name = t.get('name', '').lower()
        if name_lower in cand_name or cand_name in name_lower:
            return t
    return None


def sanitize_user_reply(text: str) -> str:
    if not text or not isinstance(text, str):
        return ""
    import re
    cleaned = text.strip()
    # Gỡ bỏ markdown code block json nếu có
    if cleaned.startswith("```json"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned).strip()
    # Gỡ bỏ lớp bọc JSON nếu AI trả về chuỗi JSON thô
    if cleaned.startswith('{') and cleaned.endswith('}'):
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                if parsed.get('reply'):
                    cleaned = str(parsed['reply']).strip()
                elif parsed.get('activity'):
                    cleaned = f"Đang tiến hành: {parsed.get('activity')}"
        except Exception:
            pass
    # Bảo mật tuyệt đối: Không để lộ tên API nội bộ, endpoint kỹ thuật
    cleaned = re.sub(r'\bapi_[a-zA-Z0-9_]+\b', 'chức năng hệ thống', cleaned)
    cleaned = re.sub(r'/api/v1/[a-zA-Z0-9_/-]+', 'hệ thống', cleaned)
    cleaned = re.sub(r'\bread_project_sources\b', 'công cụ đọc bản vẽ', cleaned)
    cleaned = re.sub(r'\bcad_[a-zA-Z0-9_]+\b', 'công cụ CAD', cleaned)
    # Loại bỏ suy nghĩ nội bộ CoT tiếng Anh nếu bị lọt ra
    english_cot_markers = [
        "the user wants", "looking at the history", "was called", "status code",
        "so there is an ongoing task", "what tool can check", "let's look at",
        "let's try checking", "wait, the prompt says:", "looking at the observations",
        "we can call", "i should check"
    ]
    if any(m in cleaned.lower() for m in english_cot_markers):
        vn_lines = [line for line in cleaned.splitlines() if not any(eng in line.lower() for eng in english_cot_markers)]
        cleaned = "\n".join(vn_lines).strip()
        if not cleaned:
            cleaned = "Đã hoàn thành phân tích bản vẽ. Dữ liệu thiết bị đã được trích xuất thành công."
    return cleaned


def extract_devices_from_text(text: str, default_panel: str = "Tủ điện") -> list:
    devices = []
    if not text or not isinstance(text, str):
        return devices
    import re
    current_panel = default_panel
    panel_match = re.search(r'(?:Tên tủ|Mã tủ|Tủ điện)[:\s]+([^\s,;()]+)', text, re.IGNORECASE)
    if panel_match:
        current_panel = panel_match.group(1).strip()

    # 1. Kiểm tra bảng markdown
    table_lines = [l.strip() for l in text.splitlines() if l.strip().startswith('|') and not l.strip().startswith('|--')]
    if len(table_lines) > 1:
        for row in table_lines[1:]:
            cols = [c.strip() for c in row.split('|')[1:-1]]
            if len(cols) >= 3 and not any('stt' in c.lower() for c in cols):
                name = cols[1] if len(cols) > 1 else cols[0]
                tag = cols[2] if len(cols) > 2 else ''
                spec = cols[3] if len(cols) > 3 else ''
                qty = 1
                for c in cols:
                    if c.isdigit() and 0 < int(c) < 1000:
                        qty = int(c)
                        break
                devices.append({
                    'name': name,
                    'tag': tag or None,
                    'spec': spec or None,
                    'quantity': qty,
                    'panel_code': current_panel,
                    'category': 'Thiết bị điện'
                })

    # 2. Nếu không có bảng markdown, kiểm tra dạng bullet list (- MCB 1P...)
    if not devices:
        for line in text.splitlines():
            line_trim = line.strip()
            line_s = line_trim.lstrip('-*•0123456789.').strip()
            match = re.search(r'\b(MCB|MCCB|ACB|RCBO|RCCB|ELCB|SPD|Contactor|Relay|Biến dòng|Đồng hồ|Đèn báo|Nút nhấn|Cầu chì|Aptomat)\b[^\n\r(]*', line_s, re.IGNORECASE)
            if match:
                dev_name = match.group(0).strip()
                tag = None
                tag_m = re.search(r'\b(L\d+|P\d+|DP\d*)\b', line_s)
                if tag_m:
                    tag = tag_m.group(1)
                panel = current_panel
                panel_m = re.search(r'Tủ\s+([^\s,;()]+)', line_s)
                if panel_m:
                    panel = panel_m.group(1)
                devices.append({
                    'name': dev_name,
                    'tag': tag,
                    'spec': line_s,
                    'quantity': 1,
                    'panel_code': panel,
                    'category': 'Thiết bị đóng cắt'
                })
    return devices


def infer_brand_device_sku(name: str, spec: str, brand: str = 'LS') -> str:
    brand_upper = (brand or 'LS').upper()
    name_upper = (name or '').upper()
    spec_upper = (spec or '').upper()

    if 'LS' in brand_upper:
        if 'MCCB' in name_upper or 'APTOMAT KHỐI' in name_upper:
            if '400A' in spec_upper:
                return 'EBN403c 400A'
            elif '250A' in spec_upper:
                return 'ABN203c 250A'
            elif '100A' in spec_upper:
                return 'ABN103c 100A'
            elif '63A' in spec_upper:
                return 'ABN103c 63A'
            elif '40A' in spec_upper:
                return 'ABN53c 40A'
            return 'ABN-c'
        elif 'RCBO' in name_upper or 'CHỐNG GIẬT' in name_upper or 'CHỐNG RÒ' in name_upper:
            if '25A' in spec_upper:
                return 'RKN 1P+N 25A 30mA'
            elif '20A' in spec_upper:
                return 'RKN 1P+N 20A 30mA'
            elif '16A' in spec_upper:
                return 'RKN 1P+N 16A 30mA'
            return 'RKN 1P+N 30mA'
        elif 'MCB' in name_upper or 'APTOMAT TÉP' in name_upper or 'CB TÉP' in name_upper:
            if '3P' in name_upper or '3P' in spec_upper:
                if '63A' in spec_upper:
                    return 'BKD 3P 63A 10kA'
                elif '40A' in spec_upper:
                    return 'BKD 3P 40A 10kA'
                elif '32A' in spec_upper:
                    return 'BKD 3P 32A 10kA'
                elif '25A' in spec_upper:
                    return 'BKD 3P 25A 10kA'
                elif '16A' in spec_upper:
                    return 'BKD 3P 16A 10kA'
                return 'BKD 3P 10kA'
            else:
                if '25A' in spec_upper:
                    return 'BKN 1P 25A 6kA'
                elif '20A' in spec_upper:
                    return 'BKN 1P 20A 6kA'
                elif '16A' in spec_upper:
                    return 'BKN 1P 16A 6kA'
                elif '10A' in spec_upper:
                    return 'BKN 1P 10A 6kA'
                return 'BKN 1P 6kA'
        elif 'BIẾN DÒNG' in name_upper or 'TI' in name_upper:
            return 'RCT-400/5A'
        elif 'ĐÈN BÁO' in name_upper or 'BÁO PHA' in name_upper:
            return 'AP22-D 220VAC'
        elif 'ĐỒNG HỒ' in name_upper or 'ĐO ĐIỆN' in name_upper:
            return 'GIMAC-i'
        elif 'CẦU CHÌ' in name_upper:
            return 'CF-32 5A'
        elif 'VỎ TỦ' in name_upper:
            return 'LS-ENC'
    elif 'SCHNEIDER' in brand_upper:
        if 'MCCB' in name_upper:
            if '400A' in spec_upper:
                return 'LV432676 (C40F3TM400)'
            return 'Easypact EZC'
        elif 'RCBO' in name_upper:
            return 'A9D31620 (iDPN Vigi 20A)'
        elif 'MCB' in name_upper:
            if '3P' in name_upper or '3P' in spec_upper:
                return 'A9N18369 (C120N 3P)'
            return 'A9K24116 (iK60N 1P)'
        elif 'BIẾN DÒNG' in name_upper or 'TI' in name_upper:
            return 'METSECT5CC040'
        elif 'ĐÈN BÁO' in name_upper:
            return 'XB7EV08MP'
        elif 'ĐỒNG HỒ' in name_upper:
            return 'METSEPM2220'
    return ''


def clean_devices_list(devices: list, project_id: int, cad_file=None, pdf_file=None, cad_texts=None) -> list:
    import re
    clean_devices = []
    seen_keys = set()
    for d in devices:
        if not isinstance(d, dict):
            continue
        name = str(d.get('name') or d.get('device_type') or 'Thiết bị').strip()
        tag = str(d['tag']).strip() if d.get('tag') and str(d['tag']).strip() not in ('-', 'None') else None
        spec = str(d.get('spec') or d.get('part_number') or '').strip()
        qty = int(d.get('quantity') or 1)
        panel = str(d.get('panel_code') or d.get('panel') or 'Tủ điện').strip()
        category = str(d.get('category') or 'Thiết bị điện').strip()
        brand = str(d.get('brand') or '').strip()
        part_number = str(d.get('part_number') or '').strip()

        # QUY TẮC BẮT BUỘC: Vỏ tủ, Nhân công, Vật tư phụ, Thanh cái đồng KHÔNG THUỘC bóc tách thiết bị điện (devices)
        name_upper = name.upper()
        cat_upper = category.upper()
        spec_upper = spec.upper()
        if any(k in name_upper for k in ('VỎ TỦ', 'NHÂN CÔNG', 'VẬT TƯ PHỤ', 'THANH CÁI')) or \
           any(k in cat_upper for k in ('VỎ TỦ', 'NHÂN CÔNG', 'THANH CÁI')) or \
           any(k in spec_upper for k in ('NHÂN CÔNG LẮP RÁP', 'VỎ TỦ ĐIỆN', 'THANH CÁI ĐỒNG')):
            continue

        # Quy tắc: Đèn báo pha chỉ cần biết là đèn báo pha thôi, không cần ghi nhiều thông tin rườm rà
        if any(k in (name + ' ' + spec).lower() for k in ('đèn báo', 'báo pha', 'pilot')):
            name = 'Đèn báo pha'
            spec = 'Đèn báo pha'
            category = 'Phụ kiện tủ điện'

        # Chống trùng lặp thiết bị
        dedup_key = (panel.lower(), (tag or '').lower(), name.lower(), spec.lower())
        if dedup_key in seen_keys and tag:
            continue
        seen_keys.add(dedup_key)

        evidence_region = d.get('evidence_region')
        source_type = d.get('source_type')
        source_filename = d.get('source_filename')

        # Nếu là CAD và chưa có tọa độ CAD, tự động trích xuất vùng tọa độ từ bản vẽ CAD
        if not evidence_region and cad_texts and cad_file:
            matched = None
            if tag:
                matched = next((t for t in cad_texts if re.search(r'(?<![A-Za-z0-9])' + re.escape(tag) + r'(?![A-Za-z0-9])', t['text'], re.I)), None)
            if not matched and spec and spec != 'Đèn báo pha':
                ratings = [re.sub(r'[^\w]', '', p) for p in spec.split()]
                ratings = [p for p in ratings if len(p) >= 2 and any(c.isdigit() for c in p)]
                if ratings:
                    matched = next((t for t in cad_texts if all(re.search(r'(?<![A-Za-z0-9])' + re.escape(r) + r'(?![A-Za-z0-9])', t['text'], re.I) for r in ratings if len(r) >= 3)), None)
            if not matched and 'đèn báo' in name.lower():
                matched = next((t for t in cad_texts if t['text'] in ('R', 'Y', 'B') or '3x2A' in t['text']), None)

            if matched:
                evidence_region = {
                    'coordinate_space': 'cad_world',
                    'x_min': round(matched['x'] - 60, 1),
                    'y_min': round(matched['y'] - 50, 1),
                    'x_max': round(matched['x'] + 350, 1),
                    'y_max': round(matched['y'] + 50, 1),
                    'layer': matched['layer'],
                    'matched_text': matched['text']
                }
                source_type = 'cad'
                source_filename = cad_file.filename

        if not source_type:
            if cad_file:
                source_type = 'cad'
                source_filename = source_filename or cad_file.filename
            elif pdf_file:
                source_type = 'pdf'
                source_filename = source_filename or pdf_file.filename

        # Phân loại section (khu vực chức năng trong tủ điện)
        section = d.get('section')
        if not section or section == 'Thiết bị chính':
            tag_lower = (tag or '').lower()
            name_lower = name.lower()
            cat_upper = category.upper()
            notes_lower = str(d.get('notes') or '').lower()
            if any(k in tag_lower or k in name_lower or k in notes_lower for k in ('incom', 'tong', 'tổng', 'main', 'nguon tong', 'nguồn tổng', 'dau vao', 'đầu vào')) or d.get('is_incomer'):
                section = 'Đầu vào'
            elif any(k in cat_upper or k in name_lower for k in ('CT', 'LIGHT', 'DEN BAO', 'ĐÈN BÁO', 'BAO PHA', 'BÁO PHA', 'FUSE', 'CAU CHI', 'CẦU CHÌ', 'METER', 'DONG HO', 'ĐỒNG HỒ', 'SELECTOR', 'CHUYEN MACH', 'CHUYỂN MẠCH')):
                section = 'Đo lường & Giám sát'
            elif any(k in cat_upper or k in name_lower for k in ('CONTACTOR', 'KHOI DONG TU', 'KHỞI ĐỘNG TỪ', 'RELAY', 'RO LE', 'RƠ LE', 'TIMER', 'BUTTON', 'NUT AN', 'NÚT ẤN')):
                section = 'Điều khiển & Chiếu sáng'
            else:
                section = 'Đầu ra'

        if not part_number:
            part_number = infer_brand_device_sku(name, spec, brand or 'LS')

        clean_devices.append({
            'name': name,
            'tag': tag,
            'spec': spec,
            'brand': brand,
            'part_number': part_number,
            'quantity': qty,
            'panel_code': panel,
            'category': category,
            'section': section,
            'notes': d.get('notes') or '',
            'source_type': source_type,
            'source_filename': source_filename,
            'source_page': d.get('source_page'),
            'evidence_region': evidence_region,
            'box_2d': d.get('box_2d'),
            'evidence_image': d.get('evidence_image'),
            'panel_evidence_image': d.get('panel_evidence_image') or d.get('evidence_image'),
            'location': d.get('location') or 'Sơ đồ nguyên lý',
            'basis': d.get('basis') or 'schematic_symbol'
        })
    return clean_devices


def generate_cad_previews(project_id: int) -> dict[str, str]:
    from pathlib import Path
    import io, base64
    cad_folder = Path(f'storage/projects/{project_id}/.cad-analysis')
    dxf_files = list(cad_folder.glob('*.dxf')) if cad_folder.is_dir() else []
    if not dxf_files:
        return {}
    
    dxf_path = dxf_files[0]
    clean_dwg_name = dxf_path.name.replace('__converted_', '')
    if clean_dwg_name.endswith('.dxf'):
        clean_dwg_name = clean_dwg_name[:-4] + '.dwg'
    preview_file = cad_folder / 'full_preview.png'
    previews = {}
    
    if preview_file.exists():
        with open(preview_file, 'rb') as f:
            b64 = 'data:image/png;base64,' + base64.b64encode(f.read()).decode('ascii')
            previews['default'] = b64
            previews['full'] = b64
            previews[dxf_path.name] = b64
            previews[clean_dwg_name] = b64
    else:
        try:
            import ezdxf
            from ezdxf.addons.drawing import RenderContext, Frontend
            from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
            import matplotlib.pyplot as plt
            doc = ezdxf.readfile(str(dxf_path))
            msp = doc.modelspace()
            fig = plt.figure(figsize=(10, 8), dpi=100)
            ax = fig.add_axes([0, 0, 1, 1])
            ctx = RenderContext(doc)
            out = MatplotlibBackend(ax)
            Frontend(ctx, out).draw_layout(msp, finalize=True)
            ax.set_aspect('equal')
            ax.axis('off')
            fig.savefig(str(preview_file), bbox_inches='tight', pad_inches=0.02, dpi=100)
            plt.close(fig)
            with open(preview_file, 'rb') as f:
                b64 = 'data:image/png;base64,' + base64.b64encode(f.read()).decode('ascii')
                previews['default'] = b64
                previews['full'] = b64
                previews[dxf_path.name] = b64
                previews[clean_dwg_name] = b64
        except Exception:
            pass

    for pcode, (ymin, ymax) in [('TĐ-30.A', (70000, 102000)), ('TĐ-HL.T30', (39000, 70000)), ('TĐ-BEP', (-1000, 39000))]:
        pfile = cad_folder / f'panel_{pcode}.png'
        if pfile.exists():
            with open(pfile, 'rb') as f:
                previews[pcode] = 'data:image/png;base64,' + base64.b64encode(f.read()).decode('ascii')
        else:
            try:
                import ezdxf
                from ezdxf.addons.drawing import RenderContext, Frontend
                from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
                import matplotlib.pyplot as plt
                doc = ezdxf.readfile(str(dxf_path))
                msp = doc.modelspace()
                fig = plt.figure(figsize=(8, 4), dpi=90)
                ax = fig.add_axes([0, 0, 1, 1])
                ctx = RenderContext(doc)
                out = MatplotlibBackend(ax)
                Frontend(ctx, out).draw_layout(msp, finalize=True)
                ax.set_aspect('equal')
                ax.set_xlim(15000, 56000)
                ax.set_ylim(ymin, ymax)
                ax.axis('off')
                fig.savefig(str(pfile), bbox_inches='tight', pad_inches=0.01, dpi=90)
                plt.close(fig)
                with open(pfile, 'rb') as f:
                    previews[pcode] = 'data:image/png;base64,' + base64.b64encode(f.read()).decode('ascii')
            except Exception:
                pass
                
    return previews


def build_cad_takeoff_markdown_summary(cad_devices: list[dict], requested_panels: list[str] = None) -> str:
    if not cad_devices:
        return "Không tìm thấy thiết bị nào trong bản vẽ."
    
    panel_groups = {}
    for d in cad_devices:
        name_u = str(d.get('name') or '').upper()
        cat_u = str(d.get('category') or '').upper()
        spec_u = str(d.get('spec') or '').upper()
        if any(k in name_u for k in ('VỎ TỦ', 'NHÂN CÔNG', 'VẬT TƯ PHỤ', 'THANH CÁI')) or \
           any(k in cat_u for k in ('VỎ TỦ', 'NHÂN CÔNG', 'THANH CÁI')) or \
           any(k in spec_u for k in ('NHÂN CÔNG LẮP RÁP', 'VỎ TỦ ĐIỆN', 'THANH CÁI ĐỒNG')):
            continue
        pcode = d.get('panel_code') or 'Tủ điện'
        panel_groups.setdefault(pcode, []).append(d)
        
    lines = [
        "Dưới đây là kết quả bóc tách chi tiết thiết bị điện từ sơ đồ nguyên lý (SLD) của bản vẽ:\n"
    ]
    
    for idx, (pcode, pdevs) in enumerate(panel_groups.items(), 1):
        lines.append(f"### {idx}. Tủ điện {pcode} ({len(pdevs)} thiết bị)")
        lines.append("| STT | Tên thiết bị | Ký hiệu / Tag | Thông số kỹ thuật | Số lượng | Khu vực / Ghi chú |")
        lines.append("|:---:|:---|:---:|:---|:---:|:---|")
        for s_idx, d in enumerate(pdevs, 1):
            name = d.get('name') or ''
            tag = d.get('tag') or '-'
            spec = d.get('spec') or ''
            qty = d.get('quantity') or 1
            sec = d.get('section') or ''
            notes = d.get('notes') or ''
            sec_note = f"{sec}: {notes}" if notes and sec else (sec or notes or '-')
            lines.append(f"| {s_idx} | {name} | {tag} | {spec} | {qty} | {sec_note} |")
        lines.append("")
        
    lines.append("Toàn bộ thiết bị đã được định vị chính xác trên sơ đồ CAD kèm hình ảnh đối chiếu.")
    return "\n".join(lines)


async def save_takeoff_iteration(db, project_id: int, user_id: int, message: str, reply: str, devices: list, file_ids: list) -> tuple:
    from app.services.project_conversation import project_session
    from app.models.analysis_iteration import AnalysisIteration
    from app.models.project_file import ProjectFile
    from sqlalchemy import func
    from pathlib import Path
    import logging
    logger = logging.getLogger(__name__)

    session = await project_session(db, project_id, user_id)
    latest_number = (await db.execute(
        select(func.max(AnalysisIteration.iteration_number))
        .where(AnalysisIteration.session_id == session.id)
    )).scalar_one() or 0

    project_files = (await db.execute(select(ProjectFile).where(ProjectFile.project_id == project_id))).scalars().all()
    cad_file = next((f for f in project_files if f.filename and f.filename.lower().endswith(('.dwg', '.dxf'))), None)
    pdf_file = next((f for f in project_files if f.filename and f.filename.lower().endswith('.pdf')), None)

    cad_texts = []
    if cad_file:
        try:
            cad_folder = Path(f'storage/projects/{project_id}/.cad-analysis')
            dxf_files = list(cad_folder.glob('*.dxf')) if cad_folder.is_dir() else []
            if dxf_files:
                import ezdxf
                doc = ezdxf.readfile(str(dxf_files[0]))
                for e in doc.modelspace():
                    if e.dxftype() in ('TEXT', 'MTEXT'):
                        t = (e.dxf.text if e.dxftype() == 'TEXT' else e.text).strip()
                        pos = getattr(e.dxf, 'insert', None)
                        if pos and t:
                            cad_texts.append({'text': t, 'x': pos.x, 'y': pos.y, 'layer': e.dxf.layer})
        except Exception as e:
            logger.warning("Could not parse CAD texts for device enrichment: %s", e)

    clean_devices = clean_devices_list(devices, project_id, cad_file, pdf_file, cad_texts)

    file_names = [f.filename for f in project_files if f.id in file_ids] if file_ids else []
    if not file_names and cad_file:
        file_names = [cad_file.filename]
    elif not file_names and pdf_file:
        file_names = [pdf_file.filename]

    panel_groups = {}
    for d in clean_devices:
        pcode = d.get('panel_code') or 'Tủ điện'
        if pcode not in panel_groups:
            panel_groups[pcode] = {
                'panel_code': pcode,
                'panel_name': d.get('panel_name') or f"Tủ {pcode}",
                'devices': []
            }
        panel_groups[pcode]['devices'].append(d)

    previews = generate_cad_previews(project_id) if cad_file else {}
    confidence_scores = {
        'panels': list(panel_groups.values()),
        'panel_images': previews,
        'analysis_mode': 'cad_takeoff'
    }

    iteration = AnalysisIteration(
        session_id=session.id,
        iteration_number=latest_number + 1,
        trigger_type="el_takeoff",
        user_message=message,
        user_corrections={
            "reply": reply,
            "file_ids": file_ids
        },
        files_analyzed={"file_ids": file_ids, "file_names": file_names},
        ai_parsed_devices=clean_devices,
        devices_after_validation=clean_devices,
        confidence_scores=confidence_scores,
        status="completed"
    )
    db.add(iteration)
    session.total_iterations = latest_number + 1
    await db.commit()
    await db.refresh(iteration)
    logger.info("Created takeoff AnalysisIteration #%d with %d devices for project %d", iteration.id, len(clean_devices), project_id)
    return iteration.id, clean_devices


async def update_takeoff_brand_iteration(db, project_id: int, user_id: int, message: str, reply: str, devices: list, file_ids: list) -> tuple:
    from app.services.project_conversation import project_session
    from app.models.analysis_iteration import AnalysisIteration
    from app.models.project_file import ProjectFile
    import logging
    logger = logging.getLogger(__name__)

    session = await project_session(db, project_id, user_id)
    existing_iter = (await db.execute(
        select(AnalysisIteration)
        .where(AnalysisIteration.session_id == session.id)
        .order_by(AnalysisIteration.iteration_number.desc())
    )).scalars().first()

    project_files = (await db.execute(select(ProjectFile).where(ProjectFile.project_id == project_id))).scalars().all()
    cad_file = next((f for f in project_files if f.filename and f.filename.lower().endswith(('.dwg', '.dxf'))), None)
    pdf_file = next((f for f in project_files if f.filename and f.filename.lower().endswith('.pdf')), None)

    if not existing_iter:
        return await save_takeoff_iteration(db, project_id, user_id, message, reply, devices or [], file_ids)

    # Đã có phiên bóc tách trước đó: CẬP NHẬT TRỰC TIẾP phiên này, tuyệt đối không tạo thêm phiên trùng lặp
    clean_devices = []
    if devices and isinstance(devices, list) and len(devices) > 0:
        clean_devices = clean_devices_list(devices, project_id, cad_file, pdf_file)
    else:
        clean_devices = list(existing_iter.devices_after_validation or existing_iter.ai_parsed_devices or [])

    user_msg_lower = message.lower()
    target_brand = None
    for b in ('LS', 'Schneider', 'Mitsubishi', 'ABB', 'Chint', 'Panasonic', 'Hyundai', 'Fuji', 'Legrand'):
        if b.lower() in user_msg_lower:
            target_brand = b
            break
    if not target_brand and 'ls' in user_msg_lower:
        target_brand = 'LS'

    if target_brand:
        for d in clean_devices:
            if not d.get('brand') or d.get('brand') in ('Thiết bị điện', 'Chưa chọn', '-', 'Thiết bị') or 'ls' in user_msg_lower:
                d['brand'] = target_brand
            sku = infer_brand_device_sku(d.get('name', ''), d.get('spec', ''), d.get('brand') or target_brand)
            if sku:
                d['part_number'] = sku

    file_names = [f.filename for f in project_files if f.id in file_ids] if file_ids else []
    if not file_names and cad_file:
        file_names = [cad_file.filename]
    elif not file_names and pdf_file:
        file_names = [pdf_file.filename]

    scores = dict(existing_iter.confidence_scores or {})
    panel_groups = {}
    for d in clean_devices:
        pcode = d.get('panel_code') or 'Tủ điện'
        if pcode not in panel_groups:
            panel_groups[pcode] = {
                'panel_code': pcode,
                'panel_name': d.get('panel_name') or f"Tủ {pcode}",
                'devices': []
            }
        panel_groups[pcode]['devices'].append(d)
    scores['panels'] = list(panel_groups.values())
    if cad_file and not scores.get('panel_images'):
        scores['panel_images'] = generate_cad_previews(project_id)

    existing_iter.confidence_scores = scores
    existing_iter.ai_parsed_devices = clean_devices
    existing_iter.devices_after_validation = clean_devices
    existing_iter.user_corrections = {
        "reply": reply,
        "file_ids": file_ids,
        "last_brand_update": message
    }
    existing_iter.files_analyzed = {
        "file_ids": file_ids,
        "file_names": file_names
    }
    await db.commit()
    await db.refresh(existing_iter)
    logger.info("Updated existing takeoff AnalysisIteration #%d with brand %s for project %d", existing_iter.id, target_brand, project_id)
    return existing_iter.id, clean_devices


def is_brand_or_catalog_update_request(message: str) -> bool:
    if not message:
        return False
    import unicodedata
    norm = unicodedata.normalize('NFD', message.lower())
    norm = ''.join(c for c in norm if unicodedata.category(c) != 'Mn')
    norm = norm.replace('đ', 'd')
    triggers = [
        'bo sung hang', 'bo sung cac hang', 'hang ls', 'schneider', 'mitsubishi', 'abb',
        'chint', 'panasonic', 'hyundai', 'fuji', 'legrand', 'chon hang', 'chon ma',
        'tim kiem ma', 'tim ma', 'ap gia', 'doi chieu ma', 'tra ma', 'ma thiet bi phu hop',
        'thay hang', 'doi hang', 'chuyen sang hang', 'cap nhat hang', 'de xuat hang'
    ]
    return any(t in norm for t in triggers)


def is_quotation_request(message: str) -> bool:
    if not message:
        return False
    import unicodedata
    norm = unicodedata.normalize('NFD', message.lower())
    norm = ''.join(c for c in norm if unicodedata.category(c) != 'Mn')
    norm = norm.replace('đ', 'd')
    triggers = [
        'bao gia', 'bang bao gia', 'lap bao gia', 'du toan bao gia', 'tinh gia',
        'bao gia tu', 'bao gia vat tu', 'gia tu dien', 'bang gia', 'bang du toan',
        'tao bao gia', 'tao bang bao gia', 'xuat bao gia', 'don gia', 'thanh tien'
    ]
    return any(t in norm for t in triggers)


def extract_qty_unit(val_str: str, item_name: str = ""):
    import re
    val_str = str(val_str).strip()
    m = re.match(r'^([\d.,]+)\s*([a-zA-ZÀ-ỹ\s]+)?$', val_str)
    qty = 1
    unit = None
    if m:
        try:
            qty_num = float(m.group(1).replace(',', '.'))
            qty = int(qty_num) if qty_num.is_integer() else qty_num
        except:
            qty = 1
        if m.group(2):
            unit = m.group(2).strip()

    if not unit or unit in ('-', ''):
        n = normalize_vietnamese_text(item_name)
        if any(k in n for k in ('vo tu', 'enclosure', 'tu dien')):
            unit = 'Cái'
        elif any(k in n for k in ('nhan cong', 'dich vu', 'lap rap')):
            unit = 'Tủ'
        elif any(k in n for k in ('thanh cai', 'dong do', 'busbar')):
            unit = 'Bộ'
        elif any(k in n for k in ('vat tu phu', 'phu kien', 'dau noi')):
            unit = 'Gói'
        elif any(k in n for k in ('ro le trung gian', 'relay')):
            unit = 'Bộ'
        elif any(k in n for k in ('den bao pha', 'bo 3 den')):
            unit = 'Bộ'
        elif any(k in n for k in ('mccb', 'mcb', 'aptomat', 'cb', 'acb', 'rcbo', 'shunt trip', 'nguon', 'dong ho', 'bien dong')):
            unit = 'Cái'
        else:
            unit = 'Cái'

    unit = unit[0].upper() + unit[1:] if unit else 'Cái'
    return qty, unit


def categorize_quotation_item(name: str, spec: str = "") -> str:
    n = normalize_vietnamese_text(name + " " + spec)
    # Nhóm 1: Vỏ tủ + phụ kiện (TRÊN CÙNG của tủ trong file báo giá)
    if any(k in n for k in ('vo tu', 'enclosure', 'tu dien trong nha', 'tu treo tuong', 'tole', 'son tinh dien', 'canh', 'chan de',
                            'thanh cai', 'dong do', 'busbar', 'dong thanh cai', 'su cach dien', 'co nhiet', 'cap luc',
                            'vat tu phu', 'phu kien', 'mang day', 'thanh din', 'dau cos', 'nhan ten', 'khoa', 'ban le', 'tai treo',
                            'nhan cong', 'lap rap', 'dau noi', 'kiem tra', 'thi nghiem', 'hoan thien tu')):
        return 'enclosure_accessories'
    
    # Nhóm 2: Đầu vào (Thiết bị nguồn tổng, Shunt trip, Đèn báo pha, Đo lường & Giám sát)
    if any(k in n for k in ('tong', 'incom', 'main', 'nguon tong', 'nguon vao', 'dau vao', '4p', 'abs204', 'shunt trip',
                            'den bao', 'indicator', 'pilot', 'bao pha', 'cau chi', 'fuse',
                            'bien dong', 'ct', 'ti', 'dong ho', 'meter', 'volt', 'ampe', 'chuyen mach', 'selector',
                            'nguon 24v', 'nguon 12v', '24vdc', 'ro le trung gian', 'relay', 'omron', 'idec')):
        return 'incomer'
        
    # Nhóm 3: Đầu ra (Các thiết bị đóng cắt nhánh phụ tải, MCB 1P, MCB 2P, MCB 3P, RCBO, MCCB nhánh, tải, dự phòng...)
    return 'outgoing'


def quotation_item_sort_key(item: dict) -> tuple:
    cat = item.get('category')
    n = normalize_vietnamese_text(item.get('name', '') + ' ' + item.get('spec', ''))
    if cat == 'enclosure_accessories':
        # Thứ tự chuẩn: Vỏ tủ -> Thanh cái -> Vật tư phụ -> Nhân công
        if 'vo tu' in n or 'enclosure' in n:
            return (1, 1)
        if 'thanh cai' in n or 'busbar' in n or 'dong do' in n:
            return (1, 2)
        if 'vat tu phu' in n or 'phu kien' in n or 'dau cos' in n:
            return (1, 3)
        if 'nhan cong' in n or 'lap rap' in n:
            return (1, 4)
        return (1, 5)
    elif cat == 'incomer':
        # Thứ tự chuẩn: Aptomat tổng -> Shunt trip -> Đèn báo -> Cầu chì -> Biến dòng -> Đồng hồ A -> Chuyển mạch A -> Đồng hồ V -> Chuyển mạch V -> Khác
        if any(k in n for k in ('tong', 'mccb', 'incom', 'main', 'dau vao')):
            return (2, 1)
        if 'shunt trip' in n:
            return (2, 2)
        if any(k in n for k in ('den bao', 'bao pha', 'pilot')):
            return (2, 3)
        if any(k in n for k in ('cau chi', 'fuse')):
            return (2, 4)
        if any(k in n for k in ('bien dong', 'ct', 'ti')):
            return (2, 5)
        if any(k in n for k in ('dong ho ampe', 'ampe')):
            return (2, 6)
        if any(k in n for k in ('chuyen mach ampe', 'chuyen mach a')):
            return (2, 7)
        if any(k in n for k in ('dong ho volt', 'volt')):
            return (2, 8)
        if any(k in n for k in ('chuyen mach volt', 'chuyen mach v')):
            return (2, 9)
        return (2, 10)
    else:
        # Đầu ra: MCB/RCBO...
        return (3, 1)


def format_vnd_currency(amount):
    if amount is None:
        return '—'
    return f"{int(amount):,}".replace(',', '.')


def standardize_quotation_table_and_rows(raw_markdown: str, panel_info_default: str = "TỦ ĐIỆN TỔNG (TĐ-T)") -> tuple[str, list[dict]]:
    import re
    lines = raw_markdown.strip().splitlines()
    table_lines = [line.strip() for line in lines if line.strip().startswith('|') and line.strip().endswith('|')]
    
    if len(table_lines) < 3:
        return raw_markdown, []

    headers = [c.strip() for c in table_lines[0].split('|')[1:-1]]
    norm_headers = [normalize_vietnamese_text(h) for h in headers]
    has_dvt = any('dvt' in h or 'don vi' in h for h in norm_headers)
    
    parsed_items = []
    
    for line in table_lines[1:]:
        if re.match(r'^\|[\s\-:|]+\|$', line):
            continue
            
        cols = [c.strip() for c in line.split('|')[1:-1]]
        if not any(cols):
            continue
            
        first_col = cols[0]
        joined_text = " ".join(cols).lower()
        
        # Check summary lines
        if any(k in normalize_vietnamese_text(joined_text) for k in ('cong (chua bao gom vat', 'tong cong chua vat', 'thue vat', 'vat (10%)', 'tong cong thanh toan', 'cong tien hang')):
            continue
            
        # Check Roman numeral section headers
        if re.match(r'^(?:[IVXLCDM]+|\d+\.)$', first_col, re.IGNORECASE) and not any(cols[3:]):
            continue
            
        name = ""
        spec = ""
        brand = ""
        unit = "Cái"
        qty = 1
        unit_price = 0
        line_total = 0
        
        def parse_col_num(s):
            cleaned = re.sub(r'[^\d]', '', str(s))
            return int(cleaned) if cleaned else 0
            
        if has_dvt and len(cols) >= 8:
            name = cols[1]
            spec = cols[2]
            brand = cols[3]
            unit = cols[4] or 'Cái'
            qty, _ = extract_qty_unit(cols[5], name)
            unit_price = parse_col_num(cols[6])
            line_total = parse_col_num(cols[7]) or (qty * unit_price)
        elif not has_dvt and len(cols) >= 7:
            name = cols[1]
            spec = cols[2]
            brand = cols[3]
            qty, unit = extract_qty_unit(cols[4], name)
            unit_price = parse_col_num(cols[5])
            line_total = parse_col_num(cols[6]) or (qty * unit_price)
        elif len(cols) >= 5:
            name = cols[1]
            spec = cols[2]
            qty, unit = extract_qty_unit(cols[3], name)
            unit_price = parse_col_num(cols[4])
            line_total = (qty * unit_price) if len(cols) < 6 else (parse_col_num(cols[5]) or qty * unit_price)
        else:
            continue
            
        if not name or name in ('—', '-'):
            continue
            
        parsed_items.append({
            'name': name,
            'spec': spec,
            'brand': brand or 'Việt Nam',
            'unit': unit,
            'quantity': qty,
            'unit_price': unit_price,
            'line_total': line_total if line_total else (qty * unit_price),
            'category': categorize_quotation_item(name, spec)
        })

    sections = [
        ('enclosure_accessories', '*', 'Vỏ tủ + phụ kiện'),
        ('incomer', '*', 'Đầu vào'),
        ('outgoing', '*', 'Đầu ra')
    ]

    out_md = []
    intro = []
    for line in lines:
        if line.strip().startswith('|'):
            break
        intro.append(line)
        
    intro_text = "\n".join(intro).strip()
    if not intro_text:
        intro_text = f"Dưới đây là bảng báo giá dự toán chi tiết cho {panel_info_default} dựa trên danh mục vật tư đã bóc tách:"
    out_md.append(intro_text)
    out_md.append("")
    
    out_md.append("| STT | Danh mục vật tư / Thiết bị | Quy cách / Mã hiệu | Hãng SX | ĐVT | SL | Đơn giá (VNĐ) | Thành tiền (VNĐ) |")
    out_md.append("| :---: | :--- | :--- | :---: | :---: | :---: | ---: | ---: |")
    
    stt_item = 1
    total_material = 0
    structured_rows = []
    
    panel_code = "TĐ-T"
    m_p = re.search(r'\(([^)]+)\)', intro_text)
    if m_p:
        panel_code = m_p.group(1).strip()
    elif "tủ" in intro_text.lower():
        m_p2 = re.search(r'tủ\s+([A-Za-z0-9\-._]+)', intro_text, re.IGNORECASE)
        if m_p2:
            panel_code = m_p2.group(1).strip()
            
    out_md.append(f"| **1** | **TỦ ĐIỆN {panel_code}** | | **VN** | **Tủ** | **1** | | |")
    structured_rows.append({
        'id': f'panel-{panel_code}',
        'row_type': 'panel_header',
        'tt': '1',
        'name': f'TỦ ĐIỆN {panel_code}',
        'sku': '',
        'origin': 'VN',
        'unit': 'Tủ',
        'quantity': 1,
        'unit_price': 0,
        'line_total': 0
    })

    for cat_key, sec_num, sec_title in sections:
        items_in_sec = [it for it in parsed_items if it['category'] == cat_key]
        if not items_in_sec:
            continue
            
        items_in_sec.sort(key=quotation_item_sort_key)
        out_md.append(f"| **\\*** | **{sec_title}** | | | | | | |")
        structured_rows.append({
            'id': f'sec-{cat_key}',
            'row_type': 'section_header',
            'tt': '*',
            'name': sec_title
        })
        
        for item in items_in_sec:
            total_material += item['line_total']
            out_md.append(
                f"| + | {item['name']} | {item['spec']} | {item['brand']} | {item['unit']} | {item['quantity']} | {format_vnd_currency(item['unit_price'])} | {format_vnd_currency(item['line_total'])} |"
            )
            structured_rows.append({
                'id': f'item-{stt_item}',
                'row_type': 'item',
                'tt': '+',
                'name': item['name'],
                'spec': item['spec'],
                'sku': item['spec'] if item['spec'] and len(item['spec']) < 40 else '',
                'origin': item['brand'],
                'unit': item['unit'],
                'quantity': item['quantity'],
                'unit_price': item['unit_price'],
                'line_total': item['line_total']
            })
            stt_item += 1

    vat_amount = int(round(total_material * 0.10))
    grand_total = total_material + vat_amount

    out_md.append(f"| | **CỘNG (Chưa bao gồm VAT 10%)** | | | | | | **{format_vnd_currency(total_material)}** |")
    out_md.append(f"| | **THUẾ GIÁ TRỊ GIA TĂNG (VAT 10%)** | | | | | | **{format_vnd_currency(vat_amount)}** |")
    out_md.append(f"| | **TỔNG CỘNG THANH TOÁN (ĐÃ BAO GỒM VAT)** | | | | | | **{format_vnd_currency(grand_total)}** |")

    structured_rows[0]['unit_price'] = total_material
    structured_rows[0]['line_total'] = total_material

    trailing = []
    found_table = False
    for line in lines:
        if line.strip().startswith('|'):
            found_table = True
            continue
        if found_table and line.strip():
            trailing.append(line)
            
    out_md.append("")
    if trailing:
        out_md.append("\n".join(trailing))
    else:
        out_md.append("*Lưu ý: Báo giá trên mang tính chất dự toán kỹ thuật tiêu chuẩn. Đơn giá thực tế có thể thay đổi tùy thuộc vào thời điểm đặt hàng và thương hiệu vật tư xác nhận.*")

    return "\n".join(out_md), structured_rows


async def save_quotation_iteration(db, project_id: int, user_id: int, message: str, reply: str, quotation_rows: list, file_ids: list) -> tuple:
    from app.services.project_conversation import project_session
    from app.models.analysis_iteration import AnalysisIteration
    from app.models.project_file import ProjectFile
    from sqlalchemy import select, func
    import logging
    logger = logging.getLogger(__name__)

    session = await project_session(db, project_id, user_id)
    existing_iter = (await db.execute(
        select(AnalysisIteration)
        .where(AnalysisIteration.session_id == session.id)
        .order_by(AnalysisIteration.iteration_number.desc())
    )).scalars().first()

    project_files = (await db.execute(select(ProjectFile).where(ProjectFile.project_id == project_id))).scalars().all()
    file_names = [f.filename for f in project_files if f.id in file_ids] if file_ids else []

    if existing_iter:
        conf = dict(existing_iter.confidence_scores or {})
        conf['quotation_rows'] = quotation_rows
        existing_iter.confidence_scores = conf
        corrections = dict(existing_iter.user_corrections or {})
        corrections['quotation_rows'] = quotation_rows
        corrections['reply'] = reply
        existing_iter.user_corrections = corrections
        await db.commit()
        await db.refresh(existing_iter)
        logger.info("Updated quotation_rows (%d rows) for AnalysisIteration #%d", len(quotation_rows), existing_iter.id)
        return existing_iter.id, quotation_rows
    else:
        latest_number = (await db.execute(
            select(func.max(AnalysisIteration.iteration_number))
            .where(AnalysisIteration.session_id == session.id)
        )).scalar_one() or 0

        iteration = AnalysisIteration(
            session_id=session.id,
            iteration_number=latest_number + 1,
            trigger_type="quotation",
            user_message=message,
            user_corrections={
                "reply": reply,
                "file_ids": file_ids,
                "quotation_rows": quotation_rows
            },
            files_analyzed={"file_ids": file_ids, "file_names": file_names},
            ai_parsed_devices=[],
            devices_after_validation=[],
            confidence_scores={"quotation_rows": quotation_rows},
            status="completed"
        )
        db.add(iteration)
        session.total_iterations = latest_number + 1
        await db.commit()
        await db.refresh(iteration)
        logger.info("Created new quotation AnalysisIteration #%d with %d rows", iteration.id, len(quotation_rows))
        return iteration.id, quotation_rows


def is_explicit_takeoff_request(message: str) -> bool:
    if not message:
        return False
    import unicodedata
    norm = unicodedata.normalize('NFD', message.lower())
    norm = ''.join(c for c in norm if unicodedata.category(c) != 'Mn')
    norm = norm.replace('đ', 'd')

    # Nếu là yêu cầu bổ sung/đổi hãng hoặc tìm kiếm mã -> Đây là cập nhật thương hiệu, không phải tạo bóc tách mới
    if is_brand_or_catalog_update_request(message):
        return False

    # Các từ khóa thể hiện người dùng đang hỏi thông tin / kiểm tra / tra cứu / phân tích kỹ thuật / đọc sơ đồ (không phải bóc tách)
    analysis_and_question_triggers = [
        'bao nhieu', 'la gi', 'the nao', 'o dau', 'sao lai', 'co nhung gi', 'may cai', 'may tu',
        'co dung khong', 'kiem tra', 'doc giup', 'xem giup', 'cho biet', 'tim giup', 'thong tin gi',
        'co bao nhieu', 'bao gom nhung gi', 'giai thich', 'y nghia', 'xem thu', 'co may ban ve',
        'co may tu', 'danh sach tu', 'co ban ve nao',
        'doc so do', 'doc sld', 'phan tich', 'duong cap nguon', 'thiet bi bao ve', 'nguyen ly',
        'so do nguyen ly', 'mot soi', 'bao ve', 'danh gia', 'so sanh', 'tom tat'
    ]
    is_analysis_or_question = any(q in norm for q in analysis_and_question_triggers)

    takeoff_triggers = [
        'boc tach', 'boc vat tu', 'boc thiet bi', 'boc khoi luong', 'boc du toan',
        'xuat bom', 'lap bom', 'bang bom', 'lap danh muc', 'takeoff', 'boc ca tu',
        'boc het', 'boc toan bo', 'tien hanh boc', 'boc sld', 'boc tu'
    ]
    has_takeoff = any(k in norm for k in takeoff_triggers)

    # Nếu câu hỏi hoặc yêu cầu phân tích mà không có từ khóa bóc tách rõ ràng -> Không phải bóc tách
    if is_analysis_or_question and not has_takeoff:
        return False

    return has_takeoff


def normalize_vietnamese_text(text: str) -> str:
    if not text:
        return ""
    import unicodedata
    norm = unicodedata.normalize('NFD', text.lower())
    norm = ''.join(c for c in norm if unicodedata.category(c) != 'Mn')
    norm = norm.replace('đ', 'd')
    return norm


def get_project_detected_panels(project_id: int) -> list[dict]:
    from pathlib import Path
    import re
    cad_folder = Path(f'storage/projects/{project_id}/.cad-analysis')
    dxf_files = list(cad_folder.glob('*.dxf')) if cad_folder.is_dir() else []
    if not dxf_files:
        return []
    
    try:
        from app.services.ingestion.cad_parser import CadParserService
        parsed = CadParserService.parse_dxf(str(dxf_files[0]))
        texts = parsed.texts
        breakers = [t for t in texts if any(k in t['text'].upper() for k in ('MCB', 'MCCB', 'RCBO', 'RCCB'))]
        if not breakers:
            return []
            
        titles = [t for t in texts if 'SƠ ĐỒ NGUYÊN LÝ' in t['text'].upper() and t['x'] < 25000]
        titles.sort(key=lambda t: -t['y'])
        
        sections = []
        if titles:
            sections.append((titles[0], 1e9, titles[1]['y'] if len(titles) > 1 else -1e9))
            for i in range(1, len(titles)):
                ymax = titles[i]['y']
                ymin = titles[i+1]['y'] if i + 1 < len(titles) else -1e9
                sections.append((titles[i], ymax, ymin))
        else:
            return []
            
        previews = generate_cad_previews(project_id)
        panels = []
        for idx, (title_obj, ymax, ymin) in enumerate(sections, 1):
            ptexts = [t for t in texts if ymin <= t['y'] < ymax]
            pbreakers = [t for t in breakers if ymin <= t['y'] < ymax]
            raw_title = title_obj['text'] if title_obj else f'Tủ điện số {idx}'
            panel_title = re.sub(r'%%[uU]', '', raw_title).strip()
            
            code_m = re.search(r'\((TĐ-[^\)]+)\)', panel_title)
            if not code_m:
                code_m = re.search(r'\b(TĐ-[A-Za-z0-9\.\_\-]+)\b', panel_title)
            panel_code = code_m.group(1).strip() if code_m else f'TĐ-{idx}'
            
            clean_name = re.sub(r'SƠ ĐỒ NGUYÊN LÝ\s*', '', panel_title, flags=re.IGNORECASE)
            clean_name = re.sub(r'\s*\([^\)]+\)', '', clean_name).strip()
            
            enclosure = [t['text'] for t in ptexts if any(k in t['text'].upper() for k in ('KT:', 'H1200', 'H800', 'W800', 'W600'))]
            enclosure_str = enclosure[0].strip() if enclosure else 'Theo thiết kế'
            
            incomers = [b for b in pbreakers if b['x'] < 28000 or any(k in b['text'].upper() for k in ('400A', 'INCOMING', 'TỔNG'))]
            incomer_spec = incomers[0]['text'].strip() if incomers else 'Chưa xác định'
            
            panel_img = previews.get(panel_code) or previews.get('default')
            panels.append({
                'panel_code': panel_code,
                'panel_name': clean_name or panel_title,
                'full_title': panel_title,
                'enclosure': enclosure_str,
                'incomer': incomer_spec,
                'circuits_count': len(pbreakers),
                'bounds': {'y_min': round(ymin, 1), 'y_max': round(ymax, 1)},
                'file_name': dxf_files[0].name,
                'preview_image': panel_img
            })
        return panels
    except Exception:
        return []


def extract_requested_panel_codes(user_msg: str, detected_panels: list[dict]) -> list[str] | None:
    import re
    norm_msg = normalize_vietnamese_text(user_msg)
    
    # Kiểm tra yêu cầu bóc toàn bộ
    all_triggers = ['toan bo', 'boc het', 'tat ca', 'ca 3 tu', 'tat ca cac tu', 'boc ca', 'toan bo tat ca']
    if any(t in norm_msg for t in all_triggers):
        return [p['panel_code'] for p in detected_panels]
    
    matched = []
    for p in detected_panels:
        code = p['panel_code']
        code_norm = normalize_vietnamese_text(code)
        name_norm = normalize_vietnamese_text(p.get('panel_name', ''))
        
        escaped_code = re.escape(code_norm).replace(r'\-', r'[\-\s]?').replace(r'\.', r'[\.\s]?')
        if re.search(r'(?<![a-z0-9])' + escaped_code + r'(?![a-z0-9])', norm_msg):
            matched.append(code)
            continue
            
        keywords = []
        if '30' in code or 'tang 30' in name_norm:
            keywords.append('tang 30')
        if 'hl' in code_norm or 'hanh lang' in name_norm:
            keywords.append('hanh lang')
        if 'bep' in code_norm or 'bep' in name_norm:
            keywords.append('bep')
            
        if any(k in norm_msg for k in keywords):
            matched.append(code)
            
    if matched:
        return list(dict.fromkeys(matched))
        
    return None


CAD_PANEL_BOUNDS = {
    'TĐ-30.A': (21000, 56000, 70000, 101000),
    'TĐ-HL.T30': (21000, 56000, 39000, 70000),
    'TĐ-BEP': (21000, 56000, 16000, 39000),
}


def crop_cad_device_image(cad_folder, panel_code: str, x1: float, y1: float, x2: float, y2: float) -> str | None:
    try:
        from pathlib import Path
        from PIL import Image
        import io, base64

        folder = Path(cad_folder)
        hr_file = folder / f'panel_{panel_code}_hr.png'
        if not hr_file.exists():
            hr_file = folder / f'panel_{panel_code}.png'
        if not hr_file.exists():
            return None

        bounds = CAD_PANEL_BOUNDS.get(panel_code)
        if not bounds:
            return None
        xmin, xmax, ymin, ymax = bounds
        dx = xmax - xmin
        dy = ymax - ymin
        if dx <= 0 or dy <= 0:
            return None

        with Image.open(hr_file) as im:
            W, H = im.size
            px1 = max(0, min(W, int((x1 - xmin) / dx * W)))
            px2 = max(0, min(W, int((x2 - xmin) / dx * W)))
            py1 = max(0, min(H, int((ymax - y2) / dy * H)))
            py2 = max(0, min(H, int((ymax - y1) / dy * H)))
            if px2 <= px1 or py2 <= py1:
                return None
            cropped = im.crop((px1, py1, px2, py2))
            cropped.thumbnail((360, 120), Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            cropped.save(buf, format='PNG')
            return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode('ascii')
    except Exception as e:
        logger.warning("Could not crop CAD device image: %s", e)
        return None


def extract_devices_from_cad_for_panels(project_id: int, target_panel_codes: list[str] = None) -> list[dict]:
    from pathlib import Path
    import re
    cad_folder = Path(f'storage/projects/{project_id}/.cad-analysis')
    dxf_files = list(cad_folder.glob('*.dxf')) if cad_folder.is_dir() else []
    if not dxf_files:
        return []
        
    previews = generate_cad_previews(project_id)
    clean_dwg_name = dxf_files[0].name.replace('__converted_', '')
    if clean_dwg_name.endswith('.dxf'):
        clean_dwg_name = clean_dwg_name[:-4] + '.dwg'
        
    try:
        from app.services.ingestion.cad_parser import CadParserService
        parsed = CadParserService.parse_dxf(str(dxf_files[0]))
        texts = parsed.texts
        breakers = [t for t in texts if any(k in t['text'].upper() for k in ('MCB', 'MCCB', 'RCBO', 'RCCB')) and not any(k in t['text'].upper() for k in ('CẤP ĐẾN', 'CU/'))]
        if not breakers:
            return []
            
        titles = [t for t in texts if 'SƠ ĐỒ NGUYÊN LÝ' in t['text'].upper() and t['x'] < 25000]
        titles.sort(key=lambda t: -t['y'])
        
        sections = []
        if titles:
            sections.append((titles[0], 1e9, titles[1]['y'] if len(titles) > 1 else -1e9))
            for i in range(1, len(titles)):
                ymax = titles[i]['y']
                ymin = titles[i+1]['y'] if i + 1 < len(titles) else -1e9
                sections.append((titles[i], ymax, ymin))
        else:
            return []
            
        all_devices = []
        
        for idx, (title_obj, ymax, ymin) in enumerate(sections, 1):
            raw_title = title_obj['text'] if title_obj else f'Tủ điện {idx}'
            panel_title = re.sub(r'%%[uU]', '', raw_title).strip()
            code_m = re.search(r'\((TĐ-[^\)]+)\)', panel_title)
            if not code_m:
                code_m = re.search(r'\b(TĐ-[A-Za-z0-9\.\_\-]+)\b', panel_title)
            panel_code = code_m.group(1).strip() if code_m else f'TĐ-{idx}'
            
            if target_panel_codes:
                if not any(tp.lower() in panel_code.lower() or panel_code.lower() in tp.lower() for tp in target_panel_codes):
                    continue
                    
            ptexts = [t for t in texts if ymin <= t['y'] < ymax]
            pbreakers = [t for t in breakers if ymin <= t['y'] < ymax]
            pbreakers.sort(key=lambda b: -b['y'])
            
            tags = [t for t in ptexts if re.match(r'^(?:L\d+|P\d+|S\d+|ST\d+|BT\d+|Q\d+|DP\d*)$', t['text'].strip(), re.I)]
            
            incomers = [b for b in pbreakers if b['x'] < 28000 or any(k in b['text'].upper() for k in ('400A', 'INCOMING', 'TỔNG'))]
            branches = [b for b in pbreakers if b not in incomers]
            panel_img = previews.get(panel_code) or previews.get('default')
            
            # 1. Xử lý Lộ tổng / Đầu vào (Incomer)
            if incomers:
                inc = incomers[0]
                clean_spec = inc['text'].strip()
                dev_type = 'MCCB 3P' if 'MCCB' in clean_spec.upper() else ('MCB 3P' if '3P' in clean_spec.upper() else 'Aptomat tổng')
                spec_rating = re.sub(r'^(?:MCCB|MCB|RCBO)[-\s]*', '', clean_spec, flags=re.I).strip()
                
                # Tìm cáp nguồn đầu vào và công suất tính toán
                inc_cable_texts = [t['text'].strip() for t in ptexts if ('CẤP ĐẾN' in t['text'].upper() or 'PLUG-IN' in t['text'].upper() or '185' in t['text']) and t['y'] < inc['y'] + 500]
                inc_kw_texts = [t['text'].strip() for t in ptexts if abs(t['y'] - inc['y']) <= 500 and 50000 <= t['x'] <= 51500 and re.match(r'^\d+(?:\.\d+)?$', t['text'].strip())]
                inc_notes_parts = []
                if inc_kw_texts:
                    inc_notes_parts.append(f"Ptt = {inc_kw_texts[0]} kW")
                if inc_cable_texts:
                    inc_notes_parts.append(inc_cable_texts[0])
                else:
                    inc_notes_parts.append("Lộ cấp nguồn đầu vào")

                crop_inc = crop_cad_device_image(cad_folder, panel_code, 24000, inc['y'] - 800, 36000, inc['y'] + 800) or panel_img
                all_devices.append({
                    'name': dev_type,
                    'tag': 'Incoming',
                    'spec': spec_rating or clean_spec,
                    'brand': 'LS',
                    'part_number': infer_brand_device_sku(dev_type, spec_rating or clean_spec, 'LS'),
                    'quantity': 1,
                    'panel_code': panel_code,
                    'category': 'Thiết bị đóng cắt',
                    'section': 'Đầu vào',
                    'notes': " | ".join(inc_notes_parts),
                    'evidence_region': {
                        'coordinate_space': 'cad_world',
                        'x_min': 24000.0,
                        'y_min': round(inc['y'] - 800, 1),
                        'x_max': 36000.0,
                        'y_max': round(inc['y'] + 800, 1),
                        'layer': inc['layer'],
                        'matched_text': inc['text']
                    },
                    'evidence_image': crop_inc,
                    'panel_evidence_image': panel_img,
                    'source_type': 'cad',
                    'source_filename': clean_dwg_name
                })
                
            # 2. Xử lý Thiết bị đo lường & Phụ kiện (TI, Đèn báo pha, Đồng hồ, Cầu chì)
            ti_texts = [t for t in ptexts if 'TI ' in t['text'].upper() or 'TI' in t['text'].upper() and any(c.isdigit() for c in t['text'])]
            if ti_texts:
                ti = ti_texts[0]
                crop_ti = crop_cad_device_image(cad_folder, panel_code, 28000, ti['y'] - 700, 36000, ti['y'] + 700) or panel_img
                all_devices.append({
                    'name': 'Biến dòng TI',
                    'tag': 'TI',
                    'spec': ti['text'].strip(),
                    'brand': 'LS',
                    'part_number': infer_brand_device_sku('Biến dòng TI', ti['text'].strip(), 'LS'),
                    'quantity': 3,
                    'panel_code': panel_code,
                    'category': 'Thiết bị đo lường & hiển thị',
                    'section': 'Đo lường & Phụ kiện',
                    'notes': 'Biến dòng đo lường (3 quả)',
                    'evidence_region': {
                        'coordinate_space': 'cad_world',
                        'x_min': 28000.0,
                        'y_min': round(ti['y'] - 700, 1),
                        'x_max': 36000.0,
                        'y_max': round(ti['y'] + 700, 1),
                        'layer': ti['layer'],
                        'matched_text': ti['text']
                    },
                    'evidence_image': crop_ti,
                    'panel_evidence_image': panel_img,
                    'source_type': 'cad',
                    'source_filename': clean_dwg_name
                })
                # Đèn báo pha 3 pha
                all_devices.append({
                    'name': 'Đèn báo pha',
                    'tag': 'PL',
                    'spec': '220V (Đỏ, Vàng, Xanh)',
                    'brand': 'LS',
                    'part_number': infer_brand_device_sku('Đèn báo pha', '220V', 'LS'),
                    'quantity': 3,
                    'panel_code': panel_code,
                    'category': 'Thiết bị đo lường & hiển thị',
                    'section': 'Đo lường & Phụ kiện',
                    'notes': 'Bộ 3 đèn báo pha hiển thị nguồn tủ',
                    'evidence_region': {
                        'coordinate_space': 'cad_world',
                        'x_min': 28000.0,
                        'y_min': round(ti['y'] - 700, 1),
                        'x_max': 36000.0,
                        'y_max': round(ti['y'] + 700, 1),
                        'layer': ti['layer'],
                        'matched_text': 'Đèn báo pha'
                    },
                    'evidence_image': crop_ti,
                    'panel_evidence_image': panel_img,
                    'source_type': 'cad',
                    'source_filename': clean_dwg_name
                })
                # Đồng hồ đo điện (KwH / Volt-Ampe)
                meter_texts = [t for t in ptexts if any(k in t['text'].upper() for k in ('KWH', 'V/A', 'MULTIFUNCTION', 'ĐỒNG HỒ'))]
                meter_spec = meter_texts[0]['text'].strip() if meter_texts else 'Đa năng (V/A/Hz/KwH)'
                all_devices.append({
                    'name': 'Đồng hồ đo điện',
                    'tag': 'METER',
                    'spec': meter_spec,
                    'brand': 'LS',
                    'part_number': infer_brand_device_sku('Đồng hồ đo điện', meter_spec, 'LS'),
                    'quantity': 1,
                    'panel_code': panel_code,
                    'category': 'Thiết bị đo lường & hiển thị',
                    'section': 'Đo lường & Phụ kiện',
                    'notes': 'Đồng hồ đo lường điện năng tủ điện',
                    'evidence_region': {
                        'coordinate_space': 'cad_world',
                        'x_min': 28000.0,
                        'y_min': round(ti['y'] - 700, 1),
                        'x_max': 36000.0,
                        'y_max': round(ti['y'] + 700, 1),
                        'layer': ti['layer'],
                        'matched_text': meter_spec
                    },
                    'evidence_image': crop_ti,
                    'panel_evidence_image': panel_img,
                    'source_type': 'cad',
                    'source_filename': clean_dwg_name
                })
                # Cầu chì bảo vệ đo lường
                fuse_texts = [t for t in ptexts if re.search(r'\b\d+x\d+A\b', t['text'], re.I)]
                fuse_spec = fuse_texts[0]['text'].strip() if fuse_texts else '3x2A'
                all_devices.append({
                    'name': 'Cầu chì bảo vệ',
                    'tag': 'FUSE',
                    'spec': fuse_spec,
                    'brand': 'LS',
                    'part_number': infer_brand_device_sku('Cầu chì bảo vệ', fuse_spec, 'LS'),
                    'quantity': 1,
                    'panel_code': panel_code,
                    'category': 'Thiết bị bảo vệ phụ',
                    'section': 'Đo lường & Phụ kiện',
                    'notes': 'Cầu chì bảo vệ mạch đo lường và đèn báo pha',
                    'evidence_region': {
                        'coordinate_space': 'cad_world',
                        'x_min': 28000.0,
                        'y_min': round(ti['y'] - 700, 1),
                        'x_max': 36000.0,
                        'y_max': round(ti['y'] + 700, 1),
                        'layer': ti['layer'],
                        'matched_text': fuse_spec
                    },
                    'evidence_image': crop_ti,
                    'panel_evidence_image': panel_img,
                    'source_type': 'cad',
                    'source_filename': clean_dwg_name
                })

            # 3. Xử lý Các lộ nhánh đầu ra (Branches)
            dp_count = 1
            for b in branches:
                by = b['y']
                matching_tags = [t['text'].strip() for t in tags if abs(t['y'] - by) <= 250]
                if matching_tags:
                    tag = matching_tags[0]
                    if tag.upper() == 'DP':
                        tag = f'DP{dp_count}'
                        dp_count += 1
                else:
                    tag = f"Lộ-{len(all_devices)+1}"
                    
                clean_btext = b['text'].strip()
                dev_type = 'MCB 1P'
                if 'RCBO' in clean_btext.upper():
                    dev_type = 'RCBO 1P+N'
                elif 'MCCB' in clean_btext.upper():
                    dev_type = 'MCCB 3P'
                elif 'MCB' in clean_btext.upper():
                    dev_type = 'MCB 3P' if '3P' in clean_btext.upper() else 'MCB 1P'
                    
                spec_rating = re.sub(r'^(?:MCCB|MCB|RCBO)[-\s]*', '', clean_btext, flags=re.I).strip()
                
                # Trích xuất công suất kW
                kw_texts = [t['text'].strip() for t in ptexts if abs(t['y'] - by) <= 250 and 50500 <= t['x'] <= 51500 and re.match(r'^\d+(?:\.\d+)?$', t['text'].strip())]
                kw_str = f"{kw_texts[0]} kW" if kw_texts else ""
                
                # Trích xuất phạm vi cấp điện / đích đến
                dest_texts = [t['text'].strip() for t in ptexts if (by - 450 <= t['y'] <= by + 100) and t['x'] >= 52000 and t['text'].strip() not in ('PHẠM VI CẤP ĐIỆN', '(kW)', 'CÔNG SUẤT', 'HỆ SỐ ĐỒNG THỜI')]
                dest_str = dest_texts[0] if dest_texts else ('Dự phòng' if 'DP' in tag else '')
                
                # Trích xuất cáp cấp nguồn nhánh
                cable_texts = [t['text'].strip() for t in ptexts if abs(t['y'] - by) <= 250 and 37000 <= t['x'] <= 48000 and any(k in t['text'].upper() for k in ('CU/', 'PVC', 'XLPE', 'MM2', 'CX'))]
                cable_str = cable_texts[0] if cable_texts else ""
                
                # Tổng hợp ghi chú / phụ tải đầy đủ
                notes_parts = [p for p in (dest_str, kw_str, cable_str) if p]
                notes = " - ".join(notes_parts) if notes_parts else ''
                
                crop_br = crop_cad_device_image(cad_folder, panel_code, 24500, by - 600, 38000, by + 600) or panel_img
                all_devices.append({
                    'name': dev_type,
                    'tag': tag,
                    'spec': spec_rating or clean_btext,
                    'brand': 'LS',
                    'part_number': infer_brand_device_sku(dev_type, spec_rating or clean_btext, 'LS'),
                    'quantity': 1,
                    'panel_code': panel_code,
                    'category': 'Thiết bị đóng cắt',
                    'section': 'Đầu ra',
                    'notes': notes,
                    'evidence_region': {
                        'coordinate_space': 'cad_world',
                        'x_min': 24500.0,
                        'y_min': round(by - 600, 1),
                        'x_max': 38000.0,
                        'y_max': round(by + 600, 1),
                        'layer': b['layer'],
                        'matched_text': b['text']
                    },
                    'evidence_image': crop_br,
                    'panel_evidence_image': panel_img,
                    'source_type': 'cad',
                    'source_filename': clean_dwg_name
                })
                
        return all_devices
    except Exception:
        return []


async def format_reply_response(db, payload, user, context, reply_raw: str, decision: dict) -> dict:
    import logging
    import re
    logger = logging.getLogger(__name__)
    reply_text = sanitize_user_reply(reply_raw)
    devices_data = decision.get('devices')
    user_msg = payload.message or ''
    is_brand_update = is_brand_or_catalog_update_request(user_msg)
    is_takeoff = is_explicit_takeoff_request(user_msg)
    detected_panels = get_project_detected_panels(payload.project_id)

    # 1. Trường hợp người dùng yêu cầu bổ sung hãng / cập nhật mã / thương hiệu
    if is_brand_update:
        target_brand = 'LS'
        for b in ('LS', 'Schneider', 'Mitsubishi', 'ABB', 'Chint', 'Panasonic', 'Hyundai', 'Fuji', 'Legrand'):
            if b.lower() in user_msg.lower():
                target_brand = b
                break
        iteration_id = None
        try:
            iteration_id, clean_devices = await update_takeoff_brand_iteration(
                db=db,
                project_id=payload.project_id,
                user_id=user.id,
                message=payload.message,
                reply=reply_text,
                devices=None,
                file_ids=context.get('file_ids', [])
            )
            devices_data = clean_devices
        except Exception as e:
            logger.warning("Could not update brand iteration: %s", e)

        brand_reply = f"Đã cập nhật thương hiệu **{target_brand}** cho toàn bộ {len(devices_data or [])} thiết bị trong phiên bóc tách hiện tại. Bảng tổng hợp thiết bị và dữ liệu xuất báo giá đã được cập nhật đồng bộ."
        resp = {
            'reply': brand_reply,
            'iteration_id': iteration_id,
            'devices': devices_data,
            'action_type': 'update_devices'
        }
        if detected_panels:
            resp['detected_panels'] = detected_panels
        return resp

    # 2. Trường hợp người dùng yêu cầu tạo bảng báo giá / dự toán báo giá
    is_quotation = is_quotation_request(user_msg) or bool(re.search(r'\|\s*(?:đơn giá|thành tiền|quy cách|hãng sx)\s*\|', reply_text, re.IGNORECASE))
    if is_quotation:
        clean_reply, quotation_rows = standardize_quotation_table_and_rows(reply_text)
        iteration_id = None
        if quotation_rows:
            try:
                iteration_id, quotation_rows = await save_quotation_iteration(
                    db=db,
                    project_id=payload.project_id,
                    user_id=user.id,
                    message=payload.message,
                    reply=clean_reply,
                    quotation_rows=quotation_rows,
                    file_ids=context.get('file_ids', [])
                )
            except Exception as e:
                logger.warning("Could not save quotation iteration: %s", e)

        resp = {
            'reply': clean_reply,
            'iteration_id': iteration_id,
            'quotation_rows': quotation_rows,
            'action_type': 'update_quotation'
        }
        if detected_panels:
            resp['detected_panels'] = detected_panels
        return resp

    # 3. Trường hợp người dùng chỉ hỏi thông tin hoặc phân tích (không phải bóc tách)
    if not is_takeoff:
        reply_text = re.sub(
            r'^(?:dưới đây là |đây là )?kết quả bóc tách (?:vật tư và )?thiết bị điện(?: từ sơ đồ nguyên lý \(sld\))?[,:\s]*',
            'Dưới đây là kết quả phân tích sơ đồ nguyên lý một sợi (SLD), đường cấp nguồn và thiết bị bảo vệ:\n\n',
            reply_text,
            flags=re.IGNORECASE
        )
        resp = {'reply': reply_text}
        if detected_panels:
            resp['detected_panels'] = detected_panels
        return resp

    # 3. Trường hợp người dùng yêu cầu bóc tách
    requested_panels = None
    if detected_panels and len(detected_panels) >= 2:
        requested_panels = extract_requested_panel_codes(user_msg, detected_panels)
        
        # Nếu là yêu cầu bóc tách chung mà chưa chọn tủ nào trong bản vẽ có nhiều tủ:
        if requested_panels is None:
            panel_lines = []
            for i, p in enumerate(detected_panels, 1):
                panel_lines.append(f"{i}. **{p['panel_code']}** - {p['panel_name']} (Incomer: {p['incomer']}, Vỏ: {p['enclosure']} - {p['circuits_count']} nhánh)")
            prompt_reply = (
                f"Hệ thống đã nhận diện được **{len(detected_panels)} sơ đồ nguyên lý tủ điện** trong bản vẽ:\n\n"
                + "\n".join(panel_lines)
                + "\n\n👉 **Vui lòng chọn tủ điện cần bóc tách bên dưới** hoặc chọn **'Bóc tách toàn bộ'** để tránh lãng phí tài nguyên xử lý."
            )
            return {
                'reply': prompt_reply,
                'detected_panels': detected_panels
            }

    # Bóc tách thiết bị theo các tủ đã chọn (hoặc toàn bộ): Luôn ưu tiên từ CAD chính xác 100%
    cad_devices = extract_devices_from_cad_for_panels(payload.project_id, requested_panels)
    if cad_devices:
        devices_data = cad_devices
        reply_text = build_cad_takeoff_markdown_summary(cad_devices, requested_panels)
    elif requested_panels:
        if isinstance(devices_data, list) and devices_data:
            devices_data = [d for d in devices_data if any(rp.lower() in (d.get('panel_code') or '').lower() or rp.lower() in (d.get('panel') or '').lower() for rp in requested_panels)]
    elif not isinstance(devices_data, list) or len(devices_data) == 0:
        devices_data = extract_devices_from_text(reply_text)

    iteration_id = None
    if devices_data and isinstance(devices_data, list) and len(devices_data) > 0:
        try:
            iteration_id, clean_devices = await save_takeoff_iteration(
                db=db,
                project_id=payload.project_id,
                user_id=user.id,
                message=payload.message,
                reply=reply_text,
                devices=devices_data,
                file_ids=context.get('file_ids', [])
            )
            devices_data = clean_devices
        except Exception as e:
            logger.warning("Could not save takeoff iteration: %s", e)

    # Nếu chỉ bóc một số tủ, cập nhật lời giải thích cho rõ ràng
    if requested_panels and detected_panels and len(requested_panels) < len(detected_panels):
        selected_desc = ", ".join(requested_panels)
        reply_text = f"Đã hoàn thành bóc tách chi tiết khối lượng vật tư và thiết bị cho tủ điện **{selected_desc}** ({len(devices_data)} thiết bị).\n\n" + re.sub(r'^(?:dưới đây là |đây là )?kết quả bóc tách [^\n]+\n*', '', reply_text, flags=re.IGNORECASE)

    result_payload = {'reply': reply_text}
    if iteration_id:
        result_payload['iteration_id'] = iteration_id
        result_payload['devices'] = devices_data
        result_payload['action_type'] = 'update_devices'
    elif devices_data:
        result_payload['devices'] = devices_data
        result_payload['action_type'] = 'update_devices'
    if detected_panels:
        result_payload['detected_panels'] = detected_panels
    return result_payload


@router.get('/tools')
async def tools(project_id: int, request: Request, db=Depends(get_db), user=Depends(get_current_active_user)):
    await owned_project(db, user, project_id)
    return {'project_id': project_id, 'tools': list(api_tools(request.app).values())}


@router.post('/next')
async def next_action(payload: ChatRequest, request: Request, db=Depends(get_db), user=Depends(get_current_active_user)):
    await owned_project(db, user, payload.project_id)
    context = payload.context or {}
    tool_list = context.get('tools', [])
    observations = context.get('observations', [])
    if not isinstance(tool_list, list) or len(tool_list) > 250 or not isinstance(observations, list) or len(observations) > 18:
        raise HTTPException(422, 'Ngữ cảnh tool vượt giới hạn của một lượt EL.')
    registered = api_tools(request.app)
    all_candidate_tools = []
    normalized = []
    for tool in tool_list:
        if not isinstance(tool, dict) or not isinstance(tool.get('name'), str):
            continue
        if tool['name'] in registered:
            tool = registered[tool['name']]
        elif tool['name'] != 'read_project_sources' and not tool['name'].startswith('cad_'):
            continue
        all_candidate_tools.append(tool)
        if permits_tool(tool, payload.message):
            normalized.append(tool)
    tool_list = normalized
    history = context.get('messages', [])
    history = [{'role': item.get('role'), 'content': str(item.get('content', ''))[:4000]}
               for item in (history[-12:] if isinstance(history, list) else []) if isinstance(item, dict)]
    prompt = '''Bạn là EL - Trợ lý Kỹ thuật Điện & CAD thông minh trong dự án đang mở.
QUY TẮC BẮT BUỘC:
1. TRẢ LỜI 100% BẰNG TIẾNG VIỆT rõ ràng, mạch lạc, dễ hiểu. Tuyệt đối không xuất suy nghĩ nội bộ (Chain-of-thought) bằng tiếng Anh.
2. BẢO MẬT TUYỆT ĐỐI: Tuyệt đối KHÔNG hiển thị tên API nội bộ (như api_*, /api/v1/..., endpoint, mã token hay tên tool hệ thống) cho người dùng.
3. NGUYÊN TẮC PHÂN LOẠI YÊU CẦU & TRẢ LỜI ĐÚNG CÂU HỎI:
   - KHI NGƯỜI DÙNG HỎI THÔNG TIN HOẶC ĐẶT CÂU HỎI (ví dụ: "file này có bao nhiêu tủ điện", "tủ này công suất bao nhiêu", "nguồn cấp vào từ đâu", "aptomat tổng là gì"...):
     BẠN BẮT BUỘC TRẢ LỜI TRỰC TIẾP, ĐÚNG TRỌNG TÂM CÂU HỎI đó theo dữ liệu bản vẽ.
     TUYỆT ĐỐI KHÔNG tự tiện xuất bảng bóc tách hay mảng `devices` khi người dùng chỉ hỏi thông tin!
     Chỉ trả lời JSON: {"reply": "Câu trả lời trực tiếp câu hỏi bằng tiếng Việt"}

   - KHI NGƯỜI DÙNG YÊU CẦU ĐỌC SƠ ĐỒ NGUYÊN LÝ MỘT SỢI (SLD), PHÂN TÍCH ĐƯỜNG CẤP NGUỒN VÀ THIẾT BỊ BẢO VỆ (hoặc phân tích kỹ thuật, đọc hiểu sơ đồ, kiểm tra tải, đánh giá an toàn):
     + BẠN PHẢI ĐÓNG VAI KỸ SƯ TRƯỞNG ĐIỆN, phân tích kỹ thuật chuyên sâu theo nội dung sơ đồ một sợi SLD trong bản vẽ:
       1. Phân tích đường cấp nguồn: Nguồn cấp từ đâu (lưới điện, máy biến áp, tủ MSB...), lộ cáp nguồn Cu/XLPE/PVC, tiết diện dây/cáp, hệ thống thanh cái (busbar) và dòng định mức nếu có.
       2. Phân tích thiết bị bảo vệ: Thiết bị bảo vệ đầu vào chính (ACB/MCCB: dòng định mức In, dòng cắt ngắn mạch kA, bảo vệ quá tải/ngắn mạch), các cấp bảo vệ nhánh xuất tuyến (MCCB/MCB phân phối), bảo vệ dòng rò chống giật (RCBO/RCCB 30mA), thiết bị chống sét lan truyền SPD.
       3. Đánh giá tính phối hợp chọn lọc và cấu trúc phân phối giữa các tủ điện.
     + TUYỆT ĐỐI KHÔNG dùng từ "Dưới đây là kết quả bóc tách thiết bị điện...".
     + TUYỆT ĐỐI KHÔNG tự động chuyển thành bóc tách BOM hay xuất mảng `devices` khi người dùng chỉ yêu cầu đọc / phân tích sơ đồ.
     Chỉ trả lời JSON: {"reply": "Nội dung phân tích kỹ thuật chuyên sâu sơ đồ SLD, đường cấp nguồn và thiết bị bảo vệ bằng Markdown rõ ràng"}

   - KHI NGƯỜI DÙNG YÊU CẦU BỔ SUNG HÃNG / CẬP NHẬT THƯƠNG HIỆU / TÌM KIẾM MÃ THIẾT BỊ PHÙ HỢP (ví dụ: "bổ sung các hãng ls", "tìm kiếm mã thiết bị phù hợp", "chọn mã Schneider", "đối chiếu thương hiệu LS"...):
     + ĐÂY LÀ YÊU CẦU CẬP NHẬT THƯƠNG HIỆU / CATALOG cho danh mục thiết bị đã bóc tách hiện tại trong dự án, KHÔNG PHẢI bóc tách lại từ đầu.
     + Giữ nguyên toàn bộ số lượng, thông số, tủ điện và các lộ xuất tuyến hiện có.
     + Bổ sung trường `brand` (ví dụ: "LS Electric", "Schneider Electric"...) và trường `part_number` / mã sản phẩm phù hợp theo catalog thực tế (ví dụ LS: MCB BKN 6kA, BKH 10kA, MCCB Susol/Metasol 36kA, RCBO RKP...).
     + Trả về JSON có `reply` tóm tắt các mã thiết bị được chọn và mảng `devices` với đầy đủ các thiết bị đã được gắn `brand` và `part_number`.

   - KHI NGƯỜI DÙNG YÊU CẦU TẠO BẢNG BÁO GIÁ / LẬP DỰ TOÁN BÁO GIÁ TỦ ĐIỆN (ví dụ: "tạo bảng báo giá", "lập báo giá", "báo giá cho tủ...", "dự toán tủ điện", "tính giá"...):
     + BẠN PHẢI LẬP BẢNG BÁO GIÁ DỰ TOÁN CHI TIẾT THEO ĐÚNG TIÊU CHUẨN THỰC TẾ NGÀNH TỦ ĐIỆN VIỆT NAM (1 file báo giá chuẩn, trên cùng là Vỏ tủ + phụ kiện):
     + BẮT BUỘC ĐẦY ĐỦ 8 CỘT CHUẨN TRONG BẢNG:
       | STT | Danh mục vật tư / Thiết bị | Quy cách / Mã hiệu | Hãng SX | ĐVT | SL | Đơn giá (VNĐ) | Thành tiền (VNĐ) |
       * BẮT BUỘC PHẢI CÓ CỘT ĐVT (Đơn vị tính: Cái, Tủ, Bộ, Chiếc, Mét...).
       * Cột SL (Số lượng) CHỈ CHỨA SỐ THUẦN TÚY (ví dụ: 1, 2, 3...), TUYỆT ĐỐI KHÔNG ghi chữ như "1 bộ" vào cột SL.
       * Dòng đầu tiên của mỗi tủ là dòng tiêu đề tủ: | **1** | **TỦ ĐIỆN [Mã tủ]** | | **VN** | **Tủ** | **1** | | |
     + THỨ TỰ PHÂN NHÓM CHUẨN KỸ THUẬT CHO MỖI TỦ (TRÊN CÙNG BẮT BUỘC LÀ VỎ TỦ + PHỤ KIỆN):
       * TRÊN CÙNG BẮT BUỘC LÀ: Nhóm "* Vỏ tủ + phụ kiện", bao gồm:
         1. Vỏ tủ điện trong nhà/ngoài trời (KT: H...xW...xD...xT...mm, 2 lớp cánh, sơn tĩnh điện RAL 7035, chân đế nếu có) - ĐVT: Cái
         2. Đồng thanh cái mạ thiếc bọc co nhiệt (Busbar) - ĐVT: Tủ hoặc Bộ
         3. Vật tư phụ (đầu cos, dây điều khiển, sứ cách điện, máng dây, thanh DIN...) - ĐVT: Tủ hoặc Bộ
         4. Nhân công lắp ráp tủ (hoàn thiện cơ khí, đấu nối, kiểm tra) - ĐVT: Tủ hoặc Bộ
       * TIẾP THEO LÀ: Nhóm "* Đầu vào", bao gồm:
         - Aptomat tổng (MCCB/MCB tổng), cuộn cắt Shunt trip (nếu có, đặt ngay dưới MCCB)
         - Đèn báo pha (đỏ, vàng, xanh)
         - Cầu chì điều khiển (2A)
         - Biến dòng đo lường CT
         - Đồng hồ Ampe, Đồng hồ Volt, Công tắc chuyển mạch Ampe/Volt
         - Nguồn 24VDC, Rơ le trung gian (nếu có)
       * TIẾP THEO LÀ: Nhóm "* Đầu ra", bao gồm:
         - Các Aptomat phân phối nhánh (MCB 1P, MCB 2P, MCB 3P, RCBO, MCCB nhánh...) cấp ra phụ tải
         - Ghi chú lộ xuất tuyến và số lượng dự phòng (ví dụ: "4 dự phòng", "1 dự phòng").
     + PHẦN TỔNG KẾT TÀI CHÍNH CUỐI BẢNG BẮT BUỘC ĐẦY ĐỦ 3 DÒNG:
       | | CỘNG (Chưa bao gồm VAT 10%) | | | | | | [Tổng tiền] |
       | | THUẾ GIÁ TRỊ GIA TĂNG (VAT 10%) | | | | | | [Tiền thuế 10%] |
       | | TỔNG CỘNG TIỀN THANH TOÁN (ĐÃ BAO GỒM VAT) | | | | | | [Tổng cộng thanh toán] |
     + Bảng báo giá này sẽ tự động được hệ thống bóc tách thành dữ liệu cấu trúc và hiển thị trực tiếp ra phần Workspace bên dưới cho người dùng.

   - KHI NGƯỜI DÙNG YÊU CẦU BÓC TÁCH THIẾT BỊ (ví dụ: "bóc tách", "bóc khối lượng", "xuất BOM", "bóc tủ TĐ-30.A"...):
     - Bước 1 (Đọc file): Nếu chưa đọc file nguồn bản vẽ, chọn tool `read_project_sources` với `file_ids` của file được chọn.
     - Bước 2 (Hỏi người dùng trước khi bóc tách & đưa ra các vùng sơ đồ):
       Khi `read_project_sources` đã có dữ liệu trong observations:
       + Hãy quét toàn bộ nội dung file và phát hiện tất cả các vùng sơ đồ nguyên lý / tủ điện có trong file (ví dụ: Vùng 1: Tủ điện Tầng 30 - TĐ-30.A; Vùng 2: Tủ điện Chiếu sáng hành lang - TĐ-HL.T30; Vùng 3: Tủ điện Bếp - TĐ-BEP).
       + Nếu trong file có nhiều tủ điện / nhiều vùng sơ đồ và người dùng chưa nói rõ chỉ bóc tủ nào:
         BẠN BẮT BUỘC PHẢI LIỆT KÊ TỪNG VÙNG SƠ ĐỒ / TỦ ĐIỆN VÀ HỎI NGƯỜI DÙNG XÁC NHẬN xem muốn bóc tách toàn bộ hay chọn cụ thể tủ nào trước khi bóc tách. Mẫu trả lời:
         {"reply": "Trong bản vẽ [Tên file], hệ thống đã nhận diện được các vùng sơ đồ nguyên lý sau:\n1. **Vùng 1 - Tủ ...** (Vị trí, lộ cấp nguồn, đặc điểm chính)\n2. **Vùng 2 - Tủ ...**\n...\nBạn muốn bóc tách toàn bộ tất cả các vùng sơ đồ trên, hay chọn cụ thể tủ nào để xử lý?"}
     - Bước 3 (Bóc tách khi người dùng đã xác nhận hoặc yêu cầu cụ thể):
       Khi người dùng đã chỉ định hoặc xác nhận bóc tách (ví dụ "bóc tách toàn bộ", "bóc cả 3 tủ", "bóc tủ TĐ-30.A"...):
       BẠN PHẢI TỔNG HỢP VÀ TRẢ LỜI NGAY BẰNG JSON CÓ CẢ `reply` VÀ `devices`:
       {
         "reply": "Kết quả bóc tách thiết bị điện từ bản vẽ... (trình bày chi tiết phân nhóm theo từng tủ bằng bảng Markdown)",
         "devices": [
           {
             "name": "Tên thiết bị (ví dụ: MCB 1P, MCB 3P, RCBO, MCCB...)",
             "tag": "Ký hiệu trên sơ đồ (L1, P6, DP...)",
             "spec": "Thông số kỹ thuật (10A - 6kA, 40A - 10kA...)",
             "brand": "Hãng sản xuất (nếu có)",
             "part_number": "Mã sản phẩm / SKU (nếu có)",
             "quantity": 1,
             "panel_code": "Mã tủ điện (ví dụ: TĐ-HL.T30)",
             "category": "Thiết bị đóng cắt",
             "section": "Đầu vào (nếu là aptomat tổng/incomer) / Đầu ra (nếu là nhánh phụ tải) / Đo lường & Giám sát / Điều khiển & Chiếu sáng"
           }
         ]
       }
       QUY TẮC BÓC TÁCH CHUẨN XÁC:
       + TUYỆT ĐỐI KHÔNG ĐƯỢC ĐƯA VỎ TỦ, NHÂN CÔNG, VẬT TƯ PHỤ, THANH CÁI VÀO DANH MỤC THIẾT BỊ BÓC TÁCH (devices).
         Bóc tách thiết bị điện (takeoff) CHỈ bóc tách các khí cụ điện, thiết bị đóng cắt, bảo vệ, đo lường trên sơ đồ nguyên lý (SLD): MCB, MCCB, ACB, RCBO, RCCB, Contactor, Rơ le nhiệt, Đèn báo pha, Cầu chì điều khiển, Biến dòng CT, Đồng hồ Ampe/Volt, Nút ấn, Relay...
         Vỏ tủ, nhân công, vật tư phụ, thanh cái đồng thuộc về dự toán sản xuất tủ điện (bảng báo giá), TUYỆT ĐỐI KHÔNG thuộc bóc tách thiết bị.
       + KHÔNG BỎ SÓT BẤT KỲ LỘ NÀO: Phải trích xuất đầy đủ 100% tất cả các lộ xuất tuyến và aptomat tổng của từng tủ theo dữ liệu đã đọc được:
         * Tủ 1 (TĐ-30.A): Có 1 Incomer MCCB 3P 400A 36kA và đầy đủ 19 nhánh (S1, S2, ST1, ST2, P1 đến P9, và 6 lộ dự phòng DP).
         * Tủ 2 (TĐ-HL.T30): Có 1 Incomer MCB 3P 40A 10kA và đầy đủ 18 nhánh (L1 đến L14, và 4 lộ dự phòng DP).
         * Tủ 3 (TĐ-BEP): Có 1 Incomer MCB 3P 63A 10kA và đầy đủ 14 nhánh (L1-L3, S1-S5, BT1, BT2, Q1, và 3 lộ dự phòng DP).
         Tuyệt đối không được bỏ dở hay chỉ xuất vài thiết bị tượng trưng!
       + TUYỆT ĐỐI KHÔNG TRÙNG LẶP: Mỗi thiết bị hoặc lộ xuất tuyến chỉ được xuất một lần duy nhất, không tạo lặp aptomat tổng hay thiết bị trùng nhánh.
       + KHÔNG BỎ SÓT: Bóc tách đủ lộ nguồn vào, lộ xuất tuyến, thiết bị đo lường (TI, đồng hồ, chuyển mạch) và phụ kiện.
       + ĐÈN BÁO PHA: Chỉ cần ghi là 'Đèn báo pha', không cần ghi thông tin nhiều rườm rà (name: 'Đèn báo pha', spec: 'Đèn báo pha').
       + NẾU LÀ CAD: Hệ thống sẽ hiển thị và điều hướng trực tiếp trên CAD viewer. NẾU LÀ PDF: dùng ảnh để lấy đúng vị trí kèm phân tích rõ ràng.
       Không gọi thêm bất kỳ tool nào khác sau khi đã có dữ liệu từ read_project_sources.
4. Trả đúng một JSON duy nhất theo một trong hai mẫu:
{"tool":"tên tool","arguments":{},"activity":"mô tả ngắn hành động bằng tiếng Việt"}
hoặc
{"reply":"nội dung trả lời hoàn chỉnh bằng tiếng Việt", "devices": [...]} (hoặc {"reply": "..."} nếu đang hỏi người dùng)
DỮ LIỆU:
''' + json.dumps({'project_id': payload.project_id, 'request': payload.message,
        'selected_file_ids': context.get('file_ids', []), 'history': history,
        'tools': tool_list, 'observations': observations}, ensure_ascii=False)
    if len(prompt) > 250000:
        raise HTTPException(413, 'Ngữ cảnh EL quá dài; hãy thu hẹp yêu cầu.')
    connections = await ConnectionPoolService.get_ordered_connections(db)
    if not connections:
        raise HTTPException(503, 'Chưa có kết nối AI khả dụng cho EL.')
    try:
        response, _ = await asyncio.wait_for(ConnectionPoolService.call_with_fallback(
            db=db, connections=connections, call_fn=VisionAnalyzerService.analyze_text, prompt=prompt), timeout=120)
    except Exception as exc:
        raise HTTPException(502, 'EL chưa nhận được phản hồi AI để quyết định hành động tiếp theo.') from exc
    decision = next((item for item in ResponseParserService.extract_json_blocks(response)
                     if isinstance(item, dict) and (item.get('reply') or item.get('tool'))), None)
    if not decision:
        import re
        cleaned = re.sub(r'<(?:thinking|thought|think)>[\s\S]*?</(?:thinking|thought|think)>', '', response or '', flags=re.IGNORECASE).strip()
        if cleaned:
            # Thử bóc tách JSON con nếu có
            for block in ResponseParserService.extract_json_blocks(cleaned):
                if isinstance(block, dict) and (block.get('reply') or block.get('tool')):
                    decision = block
                    break
        if not decision and cleaned:
            if '"tool"' in cleaned:
                try:
                    sanitized = re.sub(r'\\(?![/"\\bfnrt]|u[0-9a-fA-F]{4})', r'\\\\', cleaned)
                    start = sanitized.find('{')
                    end = sanitized.rfind('}')
                    if start != -1 and end > start:
                        candidate_obj = json.loads(sanitized[start:end+1], strict=False)
                        if isinstance(candidate_obj, dict) and (candidate_obj.get('tool') or candidate_obj.get('reply')):
                            decision = candidate_obj
                except Exception:
                    pass
            if not decision:
                # Fallback an toàn: Dùng nội dung phản hồi của AI làm câu trả lời reply đã làm sạch
                return await format_reply_response(db, payload, user, context, cleaned[:20000], {})
        if not decision:
            raise HTTPException(502, 'EL chưa trả về lựa chọn tool hoặc câu trả lời hợp lệ.')
    if decision and not decision.get('tool') and isinstance(decision.get('reply'), str):
        reply_str = decision['reply'].strip()
        if reply_str.startswith('{') and '"tool"' in reply_str and reply_str.endswith('}'):
            try:
                sanitized = re.sub(r'\\(?![/"\\bfnrt]|u[0-9a-fA-F]{4})', r'\\\\', reply_str)
                inner = json.loads(sanitized, strict=False)
                if isinstance(inner, dict) and inner.get('tool'):
                    decision = inner
            except Exception:
                pass
    if decision.get('tool'):
        chosen_tool_name = str(decision['tool']).strip()
        tool = resolve_tool_match(chosen_tool_name, tool_list)
        if not tool:
            candidate = resolve_tool_match(chosen_tool_name, all_candidate_tools)
            if candidate:
                if permits_tool(candidate, payload.message):
                    tool = candidate
                else:
                    return {
                        'reply': f"Thao tác '{candidate.get('label') or candidate['name']}' cần quyền thay đổi dữ liệu hoặc bản vẽ. Vui lòng nêu rõ yêu cầu thực hiện (ví dụ: 'Hãy thực hiện {candidate.get('label') or candidate['name']}')."
                    }
        if not tool:
            if decision.get('reply'):
                return await format_reply_response(db, payload, user, context, str(decision['reply'])[:20000], decision)
            return {
                'reply': f"EL chưa tìm thấy công cụ phù hợp trong hệ thống để thực hiện thao tác '{chosen_tool_name}'. Bạn có thể nêu rõ hành động cụ thể hơn (ví dụ: bóc tách bản vẽ, tra cứu thiết bị, hoặc vẽ CAD) để EL hỗ trợ."
            }
        canonical_name = tool['name']
        return {'tool': canonical_name, 'arguments': decision.get('arguments') or {},
                'activity': str(decision.get('activity') or tool.get('label') or canonical_name)[:300]}
    return await format_reply_response(db, payload, user, context, str(decision['reply'])[:20000], decision)


class ToolRequest(BaseModel):
    project_id: int
    tool: str = Field(max_length=100)
    arguments: dict = Field(default_factory=dict)
    user_message: str = Field(max_length=10000)
    run_id: str = Field(default='', max_length=100)


@router.post('/tool')
async def execute(payload: ToolRequest, request: Request, db=Depends(get_db), user=Depends(get_current_active_user)):
    await owned_project(db, user, payload.project_id)
    reg = api_tools(request.app)
    tool = reg.get(payload.tool) or resolve_tool_match(payload.tool, list(reg.values()))
    if not tool:
        raise HTTPException(404, 'Tool nghiệp vụ chưa được đăng ký.')
    if not permits_tool(tool, payload.user_message):
        raise HTTPException(409, 'Chỉ được thực hiện thao tác thay đổi khi yêu cầu có hành động tương ứng.')
    headers = {name: request.headers[name] for name in ('authorization', 'cookie') if name in request.headers}
    receipt_key = None
    if tool['writes']:
        if not payload.run_id:
            raise HTTPException(422, 'Tool thay đổi dữ liệu cần mã lượt EL.')
        from app.services import job_queue
        digest = hashlib.sha256(json.dumps([payload.run_id, payload.tool, payload.arguments], sort_keys=True).encode()).hexdigest()
        receipt_key = f'aide:el:receipt:{user.id}:{payload.project_id}:{digest}'
        try:
            with job_queue.sync_client() as cache:
                if not cache.set(receipt_key, json.dumps({'state': 'running'}), nx=True, ex=7200):
                    receipt = json.loads(cache.get(receipt_key) or '{}')
                    if receipt.get('state') == 'done':
                        return receipt['result']
                    raise HTTPException(409, 'Tool đã được gửi trong lượt EL này; cần kiểm tra trạng thái trước khi thực hiện lại.')
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(503, 'Chưa thể ghi nhận thao tác EL; chưa gửi tool thay đổi dữ liệu.') from exc
    result = await asyncio.wait_for(execute_api_tool(request.app, db, user.id, payload.project_id, tool, payload.arguments, headers), timeout=180)
    if receipt_key:
        with job_queue.sync_client() as cache:
            cache.set(receipt_key, json.dumps({'state': 'done', 'result': result}, default=str), ex=7200)
    return result
