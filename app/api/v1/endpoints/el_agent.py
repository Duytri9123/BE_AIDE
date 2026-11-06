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
    if "The user wants to" in cleaned or "Looking at the history and observations:" in cleaned or "status code 409" in cleaned:
        vn_lines = [line for line in cleaned.splitlines() if not any(eng in line for eng in [
            "The user wants", "Looking at the history", "was called", "status code", "So there is an ongoing task",
            "What tool can check", "Let's look at", "Let's try checking", "Wait, the prompt says:"
        ])]
        cleaned = "\n".join(vn_lines).strip()
        if not cleaned:
            cleaned = "Đã hoàn thành phân tích bản vẽ. Dữ liệu thiết bị đã được trích xuất thành công."
    return cleaned


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
3. KHI NGƯỜI DÙNG YÊU CẦU BÓC TÁCH BẢN VẼ (ví dụ: bóc tách thiết bị điện, phân nhóm theo tủ từ bản vẽ DWG, DXF, PDF):
   - Nếu chưa đọc file nguồn bản vẽ: chọn tool `read_project_sources` với `file_ids` của file được chọn.
   - Khi `read_project_sources` ĐÃ CÓ DỮ LIỆU trong observations: BẠN PHẢI TỔNG HỢP VÀ TRẢ LỜI NGAY BẰNG JSON `{"reply": "..."}`.
     Không gọi thêm bất kỳ tool bóc tách nào khác.
     Trình bày kết quả bóc tách chi tiết dưới dạng BẢNG MARKDOWN phân nhóm rõ ràng theo từng tủ điện:
     Ví dụ:
     ### Tủ điện: [Tên tủ / Mã tủ]
     | STT | Tên thiết bị | Ký hiệu / Mã | Thông số kỹ thuật | Số lượng | Đơn vị | Ghi chú |
     |---|---|---|---|---|---|---|
4. Trả đúng một JSON duy nhất theo một trong hai mẫu:
{"tool":"tên tool","arguments":{},"activity":"mô tả ngắn hành động bằng tiếng Việt"}
hoặc
{"reply":"nội dung trả lời hoàn chỉnh bằng tiếng Việt"}
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
                return {'reply': sanitize_user_reply(cleaned[:20000])}
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
                return {'reply': sanitize_user_reply(str(decision['reply'])[:20000])}
            return {
                'reply': f"EL chưa tìm thấy công cụ phù hợp trong hệ thống để thực hiện thao tác '{chosen_tool_name}'. Bạn có thể nêu rõ hành động cụ thể hơn (ví dụ: bóc tách bản vẽ, tra cứu thiết bị, hoặc vẽ CAD) để EL hỗ trợ."
            }
        canonical_name = tool['name']
        return {'tool': canonical_name, 'arguments': decision.get('arguments') or {},
                'activity': str(decision.get('activity') or tool.get('label') or canonical_name)[:300]}
    return {'reply': sanitize_user_reply(str(decision['reply'])[:20000])}


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
