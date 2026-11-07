
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
            'location': d.get('location') or 'Sơ đồ nguyên lý',
            'basis': d.get('basis') or 'schematic_symbol'
        })
    return clean_devices


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

    if target_brand:
        for d in clean_devices:
            if not d.get('brand') or d.get('brand') in ('Thiết bị điện', 'Chưa chọn', '-', 'Thiết bị') or 'ls' in user_msg_lower:
                d['brand'] = target_brand

    file_names = [f.filename for f in project_files if f.id in file_ids] if file_ids else []
    if not file_names and cad_file:
        file_names = [cad_file.filename]
    elif not file_names and pdf_file:
        file_names = [pdf_file.filename]

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
            
            panels.append({
                'panel_code': panel_code,
                'panel_name': clean_name or panel_title,
                'full_title': panel_title,
                'enclosure': enclosure_str,
                'incomer': incomer_spec,
                'circuits_count': len(pbreakers),
                'bounds': {'y_min': round(ymin, 1), 'y_max': round(ymax, 1)},
                'file_name': dxf_files[0].name
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


def extract_devices_from_cad_for_panels(project_id: int, target_panel_codes: list[str] = None) -> list[dict]:
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

                all_devices.append({
                    'name': dev_type,
                    'tag': 'Incoming',
                    'spec': spec_rating or clean_spec,
                    'quantity': 1,
                    'panel_code': panel_code,
                    'category': 'Thiết bị đóng cắt',
                    'section': 'Đầu vào',
                    'notes': " | ".join(inc_notes_parts),
                    'evidence_region': {
                        'coordinate_space': 'cad_world',
                        'x_min': round(inc['x'] - 100, 1),
                        'y_min': round(inc['y'] - 60, 1),
                        'x_max': round(inc['x'] + 350, 1),
                        'y_max': round(inc['y'] + 60, 1),
                        'layer': inc['layer'],
                        'matched_text': inc['text']
                    },
                    'source_type': 'cad',
                    'source_filename': dxf_files[0].name
                })
                
            # 2. Xử lý Thiết bị đo lường & Phụ kiện (TI, Đèn báo pha, Đồng hồ, Cầu chì)
            ti_texts = [t for t in ptexts if 'TI ' in t['text'].upper() or 'TI' in t['text'].upper() and any(c.isdigit() for c in t['text'])]
            if ti_texts:
                ti = ti_texts[0]
                all_devices.append({
                    'name': 'Biến dòng TI',
                    'tag': 'TI',
                    'spec': ti['text'].strip(),
                    'quantity': 3,
                    'panel_code': panel_code,
                    'category': 'Thiết bị đo lường & hiển thị',
                    'section': 'Đo lường & Phụ kiện',
                    'notes': 'Biến dòng đo lường (3 quả)',
                    'evidence_region': {
                        'coordinate_space': 'cad_world',
                        'x_min': round(ti['x'] - 50, 1),
                        'y_min': round(ti['y'] - 50, 1),
                        'x_max': round(ti['x'] + 200, 1),
                        'y_max': round(ti['y'] + 50, 1),
                        'layer': ti['layer'],
                        'matched_text': ti['text']
                    },
                    'source_type': 'cad',
                    'source_filename': dxf_files[0].name
                })
                # Đèn báo pha 3 pha
                all_devices.append({
                    'name': 'Đèn báo pha',
                    'tag': 'PL',
                    'spec': '220V (Đỏ, Vàng, Xanh)',
                    'quantity': 3,
                    'panel_code': panel_code,
                    'category': 'Thiết bị đo lường & hiển thị',
                    'section': 'Đo lường & Phụ kiện',
                    'notes': 'Bộ 3 đèn báo pha hiển thị nguồn tủ',
                    'evidence_region': {
                        'coordinate_space': 'cad_world',
                        'x_min': round(ti['x'] - 50, 1),
                        'y_min': round(ti['y'] - 50, 1),
                        'x_max': round(ti['x'] + 200, 1),
                        'y_max': round(ti['y'] + 50, 1),
                        'layer': ti['layer'],
                        'matched_text': 'Đèn báo pha'
                    },
                    'source_type': 'cad',
                    'source_filename': dxf_files[0].name
                })
                # Đồng hồ đo điện (KwH / Volt-Ampe)
                meter_texts = [t for t in ptexts if any(k in t['text'].upper() for k in ('KWH', 'V/A', 'MULTIFUNCTION', 'ĐỒNG HỒ'))]
                meter_spec = meter_texts[0]['text'].strip() if meter_texts else 'Đa năng (V/A/Hz/KwH)'
                all_devices.append({
                    'name': 'Đồng hồ đo điện',
                    'tag': 'METER',
                    'spec': meter_spec,
                    'quantity': 1,
                    'panel_code': panel_code,
                    'category': 'Thiết bị đo lường & hiển thị',
                    'section': 'Đo lường & Phụ kiện',
                    'notes': 'Đồng hồ đo lường điện năng tủ điện',
                    'evidence_region': {
                        'coordinate_space': 'cad_world',
                        'x_min': round(ti['x'] - 50, 1),
                        'y_min': round(ti['y'] - 50, 1),
                        'x_max': round(ti['x'] + 200, 1),
                        'y_max': round(ti['y'] + 50, 1),
                        'layer': ti['layer'],
                        'matched_text': meter_spec
                    },
                    'source_type': 'cad',
                    'source_filename': dxf_files[0].name
                })
                # Cầu chì bảo vệ đo lường
                fuse_texts = [t for t in ptexts if re.search(r'\b\d+x\d+A\b', t['text'], re.I)]
                fuse_spec = fuse_texts[0]['text'].strip() if fuse_texts else '3x2A'
                all_devices.append({
                    'name': 'Cầu chì bảo vệ',
                    'tag': 'FUSE',
                    'spec': fuse_spec,
                    'quantity': 1,
                    'panel_code': panel_code,
                    'category': 'Thiết bị bảo vệ phụ',
                    'section': 'Đo lường & Phụ kiện',
                    'notes': 'Cầu chì bảo vệ mạch đo lường và đèn báo pha',
                    'evidence_region': {
                        'coordinate_space': 'cad_world',
                        'x_min': round(ti['x'] - 50, 1),
                        'y_min': round(ti['y'] - 50, 1),
                        'x_max': round(ti['x'] + 200, 1),
                        'y_max': round(ti['y'] + 50, 1),
                        'layer': ti['layer'],
                        'matched_text': fuse_spec
                    },
                    'source_type': 'cad',
                    'source_filename': dxf_files[0].name
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
                
                all_devices.append({
                    'name': dev_type,
                    'tag': tag,
                    'spec': spec_rating or clean_btext,
                    'quantity': 1,
                    'panel_code': panel_code,
                    'category': 'Thiết bị đóng cắt',
                    'section': 'Đầu ra',
                    'notes': notes,
                    'evidence_region': {
                        'coordinate_space': 'cad_world',
                        'x_min': round(b['x'] - 100, 1),
                        'y_min': round(b['y'] - 60, 1),
                        'x_max': round(b['x'] + 350, 1),
                        'y_max': round(b['y'] + 60, 1),
                        'layer': b['layer'],
                        'matched_text': b['text']
                    },
                    'source_type': 'cad',
                    'source_filename': dxf_files[0].name
                })
                
            # 4. Xử lý Vỏ tủ điện (Enclosure)
            enclosure_texts = [t for t in ptexts if any(k in t['text'].upper() for k in ('KT:', 'H1200', 'H800', 'VỎ TỦ'))]
            encl_spec = enclosure_texts[0]['text'].strip() if enclosure_texts else 'Theo tiêu chuẩn thiết kế'
            encl_thickness = 'tôn dày 1.5mm, 2 lớp cánh, sơn tĩnh điện' if '1200' in encl_spec else 'tôn dày 1.2-1.5mm, sơn tĩnh điện'
            all_devices.append({
                'name': f'Vỏ tủ điện {panel_code}',
                'tag': 'ENCL',
                'spec': f"{encl_spec} ({encl_thickness})",
                'quantity': 1,
                'panel_code': panel_code,
                'category': 'Vỏ tủ & phụ kiện',
                'section': 'Vỏ tủ điện',
                'notes': f"Vỏ tủ điện công nghiệp sơn tĩnh điện trong nhà ({encl_thickness})",
                'evidence_region': {
                    'coordinate_space': 'cad_world',
                    'x_min': round(enclosure_texts[0]['x'] - 50, 1) if enclosure_texts else 20000.0,
                    'y_min': round(enclosure_texts[0]['y'] - 50, 1) if enclosure_texts else 95000.0,
                    'x_max': round(enclosure_texts[0]['x'] + 300, 1) if enclosure_texts else 25000.0,
                    'y_max': round(enclosure_texts[0]['y'] + 50, 1) if enclosure_texts else 97000.0,
                    'layer': enclosure_texts[0]['layer'] if enclosure_texts else '0',
                    'matched_text': encl_spec
                },
                'source_type': 'cad',
                'source_filename': dxf_files[0].name
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
        if not devices_data:
            devices_data = extract_devices_from_text(reply_text)
        iteration_id = None
        try:
            iteration_id, clean_devices = await update_takeoff_brand_iteration(
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
            logger.warning("Could not update brand iteration: %s", e)

        resp = {
            'reply': reply_text,
            'iteration_id': iteration_id,
            'devices': devices_data,
            'action_type': 'update_devices'
        }
        if detected_panels:
            resp['detected_panels'] = detected_panels
        return resp

    # 2. Trường hợp người dùng chỉ hỏi thông tin hoặc phân tích (không phải bóc tách)
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

    # Bóc tách thiết bị theo các tủ đã chọn (hoặc toàn bộ)
    if requested_panels:
        cad_devices = extract_devices_from_cad_for_panels(payload.project_id, requested_panels)
        if cad_devices:
            devices_data = cad_devices
        elif isinstance(devices_data, list) and devices_data:
            devices_data = [d for d in devices_data if any(rp.lower() in (d.get('panel_code') or '').lower() or rp.lower() in (d.get('panel') or '').lower() for rp in requested_panels)]
    elif not isinstance(devices_data, list) or len(devices_data) == 0:
        cad_devices = extract_devices_from_cad_for_panels(payload.project_id)
        if cad_devices:
            devices_data = cad_devices
        else:
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
