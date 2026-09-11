from dataclasses import dataclass, field
import logging
import re
import ezdxf
from ezdxf import bbox as ezdxf_bbox
from pathlib import Path
from typing import List

from app.core.exceptions import CADParsingError
from app.core.device_patterns import DevicePatterns, DeviceMatch

logger = logging.getLogger(__name__)

@dataclass
class CadParseResult:
    layers: list[dict] = field(default_factory=list)
    blocks: list[dict] = field(default_factory=list)
    texts: list[dict] = field(default_factory=list)
    bounds: dict = field(default_factory=dict)
    devices: list[DeviceMatch] = field(default_factory=list)  # Extracted devices from text labels
    is_reliable: bool = True  # True nếu đọc được cấu trúc (DXF), False nếu chỉ quét binary thô (DWG)

class CadParserService:
    @staticmethod
    def parse_dxf(file_path: str) -> CadParseResult:
        """Đọc file DXF và trích xuất thông tin thiết bị, nhãn text."""
        if not Path(file_path).exists():
            raise CADParsingError(
                f"File DXF không tồn tại: {file_path}",
                {"path": file_path}
            )
        
        try:
            logger.info(f"Parsing DXF file: {file_path}")
            doc = ezdxf.readfile(file_path)
            
            layers = CadParserService.get_layer_info(doc)
            blocks = CadParserService.extract_device_blocks(doc)
            texts = CadParserService.extract_text_labels(doc)
            bounds = CadParserService.calculate_bounds(doc)
            
            # Extract devices from text labels using advanced patterns
            devices = CadParserService.extract_devices_from_texts(texts)
            
            logger.info(
                f"Parsed DXF: {len(layers)} layers, {len(blocks)} blocks, "
                f"{len(texts)} texts, {len(devices)} devices"
            )
            
            return CadParseResult(
                layers=layers,
                blocks=blocks,
                texts=texts,
                bounds=bounds,
                devices=devices
            )
        except ezdxf.DXFStructureError as e:
            logger.error(f"DXF structure error: {str(e)}")
            raise CADParsingError(
                f"File DXF bị hỏng hoặc định dạng không hợp lệ: {str(e)}",
                {"path": file_path, "error": str(e)}
            )
        except PermissionError:
            raise CADParsingError(
                f"Không có quyền đọc file DXF: {file_path}",
                {"path": file_path}
            )
        except Exception as e:
            logger.error(f"Failed to parse DXF: {str(e)}", exc_info=True)
            raise CADParsingError(
                f"Lỗi khi đọc file DXF: {str(e)}",
                {"path": file_path, "error": str(e)}
            )

    @staticmethod
    def extract_device_blocks(doc) -> list[dict]:
        blocks = []
        msp = doc.modelspace()
        for entity in msp.query('INSERT'):
            blocks.append({
                "name": entity.dxf.name,
                "x": entity.dxf.insert.x,
                "y": entity.dxf.insert.y,
                "layer": entity.dxf.layer
            })
        return blocks

    @staticmethod
    def extract_text_labels(doc) -> list[dict]:
        texts = []
        msp = doc.modelspace()
        
        # 1. Extract regular TEXT and MTEXT entities
        for entity in msp.query('TEXT MTEXT'):
            txt_val = entity.plain_text() if entity.dxftype() == 'MTEXT' else entity.dxf.text
            if txt_val and txt_val.strip():
                texts.append({
                    "text": txt_val.strip(),
                    "x": entity.dxf.insert.x if hasattr(entity.dxf, 'insert') else 0,
                    "y": entity.dxf.insert.y if hasattr(entity.dxf, 'insert') else 0,
                    "layer": getattr(entity.dxf, 'layer', '0')
                })
                
        # 2. Extract Block Attributes (ATTRIB) attached to block insertions (INSERT)
        for insert in msp.query('INSERT'):
            try:
                if hasattr(insert, 'attribs'):
                    for att in insert.attribs:
                        val = getattr(att.dxf, 'text', '') or ''
                        if val and val.strip():
                            texts.append({
                                "text": val.strip(),
                                "x": att.dxf.insert.x if hasattr(att.dxf, 'insert') else 0,
                                "y": att.dxf.insert.y if hasattr(att.dxf, 'insert') else 0,
                                "layer": getattr(att.dxf, 'layer', '0')
                            })
            except Exception:
                continue

        return texts

    # Các chuỗi metadata nội bộ DWG thường gây false-positive khi quét binary
    _DWG_JUNK_PREFIXES = (
        "AcDb", "ACAD_", "ObjectDBX", "AcDb", "Ac", "ACIS",
        "ISM", "AEC", "AECDTL", "AECC", "AcSm", "ADSK",
        "%<", "{\\f", "{\\F", "DIMSTYLE", "TABLESTYLE",
        "MLINESTYLE", "PLOTSTYLE", "VISUALSTYLE",
    )

    @staticmethod
    def _sanitize_text(text: str) -> str:
        """Loại bỏ surrogate characters và ký tự không encode được UTF-8."""
        # Loại bỏ surrogate pairs/lone surrogates (\uD800-\uDFFF) gây crash UTF-8 encoding
        cleaned = text.encode('utf-8', errors='surrogatepass').decode('utf-8', errors='replace')
        # Thay thế ký tự replacement (\ufffd) bằng khoảng trắng
        cleaned = cleaned.replace('\ufffd', ' ')
        # Loại bỏ khoảng trắng thừa
        return ' '.join(cleaned.split()).strip()

    @staticmethod
    def _is_dwg_junk(text: str) -> bool:
        """Kiểm tra chuỗi có phải metadata nội bộ DWG (không phải text bản vẽ thực sự)."""
        if not text or len(text) < 3:
            return True
        upper = text.upper()
        for prefix in CadParserService._DWG_JUNK_PREFIXES:
            if upper.startswith(prefix.upper()):
                return True
        # Lọc chuỗi chỉ chứa hex/binary pattern, hoặc chuỗi quá nhiều ký tự đặc biệt
        alpha_count = sum(1 for c in text if c.isalpha())
        if len(text) > 5 and alpha_count / len(text) < 0.3:
            return True
        return False

    @staticmethod
    def extract_strings_from_dwg(file_path: str) -> List[dict]:
        """Trích xuất chuỗi ký tự văn bản có nghĩa từ file DWG nhị phân.
        
        LƯU Ý: Kết quả từ quét binary DWG KHÔNG đáng tin cậy. 
        Chỉ tìm được một phần nhỏ text, không có tọa độ, dễ nhầm metadata nội bộ thành text bản vẽ.
        """
        found_texts = []
        try:
            with open(file_path, "rb") as f:
                content = f.read()

            import re
            keywords = ["MCCB", "MCB", "ACB", "RCBO", "RCCB", "CONTACTOR", "METER", "LIGHT", "TONG", "INCOMER", "AMP", "KA"]
            
            # Extract ASCII strings (length between 3 and 80)
            ascii_matches = re.findall(rb'[\x20-\x7E]{3,80}', content)
            seen = set()
            for m in ascii_matches:
                try:
                    s = m.decode('ascii', errors='ignore').strip()
                    s = CadParserService._sanitize_text(s)
                    if s and s not in seen and not CadParserService._is_dwg_junk(s) and any(k in s.upper() for k in keywords):
                        seen.add(s)
                        found_texts.append({"text": s, "x": 0, "y": 0, "layer": "DWG_RAW"})
                except Exception:
                    pass

            # Extract UTF-16LE strings
            utf16_matches = re.findall(rb'(?:[\x20-\x7E]\x00){3,80}', content)
            for m in utf16_matches:
                try:
                    s = m.decode('utf-16le', errors='ignore').strip()
                    s = CadParserService._sanitize_text(s)
                    if s and s not in seen and not CadParserService._is_dwg_junk(s) and any(k in s.upper() for k in keywords):
                        seen.add(s)
                        found_texts.append({"text": s, "x": 0, "y": 0, "layer": "DWG_RAW"})
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"Error reading DWG binary strings: {str(e)}")
        return found_texts

    @staticmethod
    def parse_cad(file_path: str) -> CadParseResult:
        """Đọc và trích xuất thông tin thiết bị từ file CAD (hỗ trợ cả DXF và DWG)."""
        ext = file_path.split(".")[-1].lower() if "." in file_path else ""
        if ext == "dxf":
            return CadParserService.parse_dxf(file_path)
        elif ext == "dwg":
            texts = CadParserService.extract_strings_from_dwg(file_path)
            devices = CadParserService.extract_devices_from_texts(texts)
            return CadParseResult(
                layers=[],
                blocks=[],
                texts=texts,
                bounds={"min_x": 0, "min_y": 0, "max_x": 1000, "max_y": 1000, "width": 1000, "height": 1000},
                devices=devices,
                is_reliable=False  # DWG binary scan KHÔNG đáng tin cậy
            )
        else:
            return CadParseResult()

    @staticmethod
    def get_layer_info(doc) -> list[dict]:
        layers = []
        try:
            for layer in doc.layers:
                layers.append({
                    "name": layer.dxf.name,
                    "color": layer.dxf.color,
                    "linetype": layer.dxf.linetype
                })
        except Exception as e:
            logger.warning(f"Error extracting layer info: {str(e)}")
        return layers
    
    @staticmethod
    def calculate_bounds(doc) -> dict:
        """Tính toán bounding box thực tế từ tất cả entities"""
        try:
            msp = doc.modelspace()

            # ezdxf resolves entity geometry (including lines, polylines, text
            # and nested inserts). The previous hasattr(entity,
            # "bounding_box") approach omitted most ordinary DXF entities and
            # often returned a zero-sized drawing.
            extents = ezdxf_bbox.extents(msp, fast=True)
            if extents.has_data:
                min_x, min_y = float(extents.extmin.x), float(extents.extmin.y)
                max_x, max_y = float(extents.extmax.x), float(extents.extmax.y)
                width, height = max_x - min_x, max_y - min_y
                if width > 0 and height > 0:
                    return {
                        "min_x": min_x,
                        "min_y": min_y,
                        "max_x": max_x,
                        "max_y": max_y,
                        "width": width,
                        "height": height,
                    }
            
            min_x = float('inf')
            min_y = float('inf')
            max_x = float('-inf')
            max_y = float('-inf')
            
            entity_count = 0
            for entity in msp:
                try:
                    # Try to get bounding box from entity
                    if hasattr(entity, 'bounding_box'):
                        bbox = entity.bounding_box
                        if bbox:
                            (bmin_x, bmin_y, _), (bmax_x, bmax_y, _) = bbox
                            min_x = min(min_x, bmin_x)
                            min_y = min(min_y, bmin_y)
                            max_x = max(max_x, bmax_x)
                            max_y = max(max_y, bmax_y)
                            entity_count += 1
                    # Fallback: use insert point for INSERT entities
                    elif entity.dxftype() == 'INSERT' and hasattr(entity.dxf, 'insert'):
                        x, y = entity.dxf.insert.x, entity.dxf.insert.y
                        min_x = min(min_x, x)
                        min_y = min(min_y, y)
                        max_x = max(max_x, x)
                        max_y = max(max_y, y)
                        entity_count += 1
                except Exception as e:
                    continue
            
            if min_x == float('inf') or entity_count == 0:
                logger.warning("No entities with valid bounds found in DXF")
                return {"min_x": 0, "min_y": 0, "max_x": 0, "max_y": 0, "width": 0, "height": 0}
            
            width = max_x - min_x
            height = max_y - min_y
            
            logger.info(f"Calculated bounds from {entity_count} entities: {width:.2f} x {height:.2f}")
            
            return {
                "min_x": float(min_x),
                "min_y": float(min_y),
                "max_x": float(max_x),
                "max_y": float(max_y),
                "width": float(width),
                "height": float(height)
            }
        except Exception as e:
            logger.error(f"Error calculating bounds: {str(e)}")
            return {"min_x": 0, "min_y": 0, "max_x": 0, "max_y": 0, "width": 0, "height": 0}
    
    @staticmethod
    def extract_panels_from_texts(texts: List[dict]) -> List[dict]:
        """Phát hiện các mã tủ và tên tủ điện từ nhãn CAD."""
        panels = []
        seen = set()
        for t in texts:
            val = t.get("text", "").strip()
            if not val or len(val) < 3 or val.endswith("mm"):
                continue

            # Tìm mã tủ kỹ thuật (MSB-01, DB-01, LP-01, TĐ-01...)
            match_code = re.search(r'\b(?:CC\s+)?([T][ĐDS][\.\-_A-Za-z0-9]+|\b(?:MSB|MDB|DB|LP|MCC)[\-_0-9A-Za-z]+)', val, re.IGNORECASE)
            if match_code:
                code = match_code.group(1).upper()
                if code not in seen and len(code) >= 3 and not code.endswith("MM"):
                    seen.add(code)
                    panels.append({
                        "panel_code": code,
                        "panel_name": f"Tủ điện {code}",
                        "x": t.get("x", 0),
                        "y": t.get("y", 0)
                    })

            # Tìm tiêu đề tủ đầy đủ
            match_title = re.search(r'(?:SƠ ĐỒ\s+)?(TỦ\s*ĐIỆN\s+[^\n\r]+)', val, re.IGNORECASE)
            if match_title:
                title = match_title.group(1).strip()
                if title not in seen:
                    seen.add(title)
                    panels.append({
                        "panel_code": title.split()[-1] if len(title.split()) > 2 else "DB",
                        "panel_name": title,
                        "x": t.get("x", 0),
                        "y": t.get("y", 0)
                    })

        return panels

    @staticmethod
    def format_cad_for_ai(cad_res: CadParseResult) -> str:
        """Định dạng toàn bộ nhãn văn bản và khối CAD theo trật tự không gian để AI LLM đọc hiểu SLD."""
        texts = cad_res.texts
        if not texts:
            return "Bản vẽ CAD không chứa văn bản ghi chú thiết bị."

        # Nhóm văn bản theo cột dọc (trục X) vì sơ đồ 1 sợi thường vẽ theo từng lộ dọc
        sorted_texts = sorted(texts, key=lambda t: (round(t.get("x", 0) / 40.0), -t.get("y", 0)))
        
        lines = []
        lines.append("=== DANH SÁCH NHÃN VĂN BẢN VÀ THÔNG SỐ KỸ THUẬT BẢN VẼ CAD ===")
        
        cur_col = None
        for t in sorted_texts:
            txt = t.get("text", "").strip()
            if not txt or len(txt) > 200:
                continue
            x = round(t.get("x", 0), 1)
            y = round(t.get("y", 0), 1)
            col = round(x / 60.0)
            if col != cur_col:
                cur_col = col
                lines.append(f"\n--- [Nhánh / Cột tọa độ X ~ {x}] ---")
            lines.append(f"  • {txt} (layer: {t.get('layer', '0')}, Y={y})")

        if cad_res.blocks:
            lines.append("\n=== CÁC KHỐI THIẾT BỊ ĐIỆN (BLOCKS INSERTION) ===")
            seen_blocks = set()
            for b in cad_res.blocks[:50]:
                bname = b.get("name", "")
                if bname and bname not in seen_blocks:
                    seen_blocks.add(bname)
                    lines.append(f"  • Block: {bname} (layer: {b.get('layer', '')})")

        return "\n".join(lines)

    @staticmethod
    def extract_devices_from_texts(texts: List[dict]) -> List[DeviceMatch]:
        """
        Extract devices từ danh sách text labels trong CAD
        Sử dụng DevicePatterns với regex linh hoạt và ghép dòng lân cận
        """
        if not texts:
            return []
        
        # 1. Ghép các text nằm gần nhau theo cột dọc (cùng lộ nhánh thiết bị)
        sorted_texts = sorted(texts, key=lambda t: (round(t.get("x", 0) / 30.0), -t.get("y", 0)))
        composite_lines = []
        buf = []
        last_x = None
        last_y = None

        for t in sorted_texts:
            val = t.get("text", "").strip()
            if not val:
                continue
            x = t.get("x", 0)
            y = t.get("y", 0)

            # Nếu nằm gần nhau trên cùng 1 cột (chênh lệch X < 30 và chênh lệch Y < 60)
            if last_x is not None and abs(x - last_x) < 30 and abs(y - last_y) < 60:
                buf.append(val)
            else:
                if buf:
                    composite_lines.append(" ".join(buf))
                buf = [val]
            last_x = x
            last_y = y

        if buf:
            composite_lines.append(" ".join(buf))

        # 2. Ghép toàn bộ text đơn lẻ
        raw_lines = [t.get("text", "").strip() for t in texts if t.get("text")]
        combined_text = "\n".join(composite_lines + raw_lines)
        
        if not combined_text.strip():
            return []
        
        # Use advanced patterns
        devices = DevicePatterns.extract_all_devices(combined_text)
        
        logger.info(f"Extracted {len(devices)} devices from {len(texts)} CAD text labels")
        return devices
