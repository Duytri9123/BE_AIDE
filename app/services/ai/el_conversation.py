"""Resolve a conversation turn before routing, permissions and tool selection."""
import json
import re
import unicodedata

from fastapi import HTTPException

from app.services.ai.connection_pool import ConnectionPoolService
from app.services.ai.response_parser import ResponseParserService
from app.services.ai.vision_analyzer import VisionAnalyzerService


_BRANDS = ('LS', 'Schneider', 'Mitsubishi', 'ABB', 'Chint', 'Panasonic', 'Hyundai', 'Fuji', 'Legrand')
_BRAND_PATTERN = re.compile(r'\b(?:' + '|'.join(_BRANDS) + r')\b', re.I)


def requested_brand(message):
    replacement = re.search(r'\b(?:sang|thành)\s+(?:hãng\s+)?(' + '|'.join(_BRANDS) + r')\b', message, re.I)
    matches = _BRAND_PATTERN.findall(message)
    target = replacement[1] if replacement else matches[-1] if matches else ''
    return next((brand for brand in _BRANDS if brand.casefold() == target.casefold()), None)


def previous_brand(message):
    match = re.search(r'\btừ\s+(?:hãng\s+)?(' + '|'.join(_BRANDS) + r')\s+(?:sang|thành)\b', message, re.I)
    return match[1].casefold() if match else None


def replace_brand_requested(message):
    normalized = ''.join(c for c in unicodedata.normalize('NFD', message.lower()) if not unicodedata.combining(c))
    return bool(re.search(r'\b(?:doi|thay|chuyen)\b', normalized.replace('đ', 'd')))


def conversation_history(context, message):
    messages = context.get('messages') or []
    history = [dict(role=m['role'], content=str(m.get('content') or '')[:8000])
               for m in messages[-20:] if isinstance(m, dict)
               and m.get('role') in ('user', 'assistant')] if isinstance(messages, list) else []
    # The UI already appended this turn. It must not appear twice in the history.
    if history and history[-1] == {'role': 'user', 'content': message[:8000]}:
        history.pop()
    bounded = []
    remaining = 24000
    for item in reversed(history):
        if remaining <= 0:
            break
        bounded.append({**item, 'content': item['content'][:remaining]})
        remaining -= len(bounded[-1]['content'])
    return list(reversed(bounded))


def resolve_confirmed_takeoff(message, context, panels):
    """A validated confirmation click already identifies the intent and scope."""
    if not panels:
        return None
    codes = ', '.join(panel['panel_code'] for panel in panels)
    confirmation = (f'Bóc tách các tủ đã xác nhận: {codes}. Giữ vị trí/lộ của từng thiết bị '
                    'và chỉ bóc trong các vùng đã chọn.')
    if message != confirmation:
        return None
    history = conversation_history(context, message)
    prior = next((turn['content'] for turn in reversed(history) if turn['role'] == 'user'), '')
    if prior:
        from app.api.v1.endpoints.el_agent import is_explicit_takeoff_request
        if is_explicit_takeoff_request(prior):
            prior = prior.split('\nNguồn của lượt này:', 1)[0]
            if not re.search(r'\b(?:boc\s*moi|lam\s*moi|khong\s*(?:su\s*)?dung\s*(?:lai)?\s*cu)\b', prior, re.I):
                message += '\nGiữ các yêu cầu phù hợp trong phạm vi tủ đã xác nhận từ lượt trước: ' + prior[:3500]
    return {'original': confirmation, 'effective': message, 'intent': 'takeoff'}


async def resolve_request(db, message, context):
    # A complete, simple brand command already identifies the open result.
    # Match the entire turn so questions, negations and extra scope still use
    # contextual resolution rather than accidentally changing every row.
    normalized = ''.join(c for c in unicodedata.normalize('NFD', message.lower().replace('đ', 'd'))
                         if not unicodedata.combining(c)).strip(' .!')

    # Bóc tách mới / bóc tách lại / không sử dụng lại dữ liệu cũ: xóa bỏ iteration_id và observations cũ để bóc tách tươi mới hoàn toàn
    if re.search(r'\b(?:boc\s*tach\s*(?:moi|lai)|boc\s*(?:moi|lai)|lam\s*moi|chay\s*lai|quet\s*lai|doc\s*lai|fresh\s*takeoff|re[-_ ]?takeoff)\b', normalized) or \
       re.search(r'\b(?:khong\s*(?:su\s*)?dung|bo\s*qua|xoa)\s*(?:lai\s*)?(?:du\s*lieu|ket\s*qua|thong\s*tin)?\s*cu\b', normalized):
        context.pop('iteration_id', None)
        context.pop('quotation_iteration_id', None)
        context.pop('observations', None)
        return {
            'original': message,
            'effective': message,
            'intent': 'takeoff',
            'fresh_takeoff': True,
            'new_quotation': True
        }

    brand = requested_brand(message)
    if context.get('iteration_id') and brand and re.fullmatch(
            r'(?:(?:toi muon|toi can|hay|vui long|giup toi)\s+)?'
            r'(?:dung|su dung|chon|doi|thay|chuyen|cap nhat)\s+'
            r'(?:(?:sang|thanh|qua)\s+)?(?:hang\s+)?' + re.escape(brand.lower()) +
            r'(?:\s+(?:cho\s+)?(?:tat ca|toan bo)(?:\s+thiet bi)?)?', normalized):
        return {'original': message, 'effective': message, 'intent': 'catalog_update', 'direct_brand_update': True}
    cached = context.get('resolved_request') or {}
    if isinstance(cached, dict) and cached.get('effective') == message:
        return cached
    history = conversation_history(context, message)
    if not context.get('iteration_id') and not any(m['role'] == 'assistant' for m in history):
        return {'original': message, 'effective': message}
    prompt = '''Bạn là AI phân tích ngữ cảnh hội thoại kỹ thuật điện và điều hướng công cụ (intent router).
Nhiệm vụ: Đọc toàn bộ lịch sử hội thoại (history) và câu yêu cầu hiện tại (current_request) để:
1. Viết lại yêu cầu hiện tại thành câu hoàn chỉnh, tự đủ ngữ cảnh (effective_request).
2. Tự động hiểu ý định người dùng và phân loại chính xác intent tương ứng để hệ thống điều hướng công cụ xử lý.

QUY TẮC HIỂU NGỮ CẢNH VÀ ĐIỀU HƯỚNG Ý ĐỊNH (INTENT):
1. PHẢN HỒI XÁC NHẬN / ĐỒNG Ý / YÊU CẦU LÀM TIẾP:
   - Khi lượt trước của trợ lý có đề xuất, hỏi ý kiến hoặc xác nhận thao tác (ví dụ: "Bạn có muốn cập nhật...", "Tôi có thể bổ sung/sửa/xóa...", "Bạn có muốn lập báo giá...", "Tôi sẽ cập nhật danh sách..."), và người dùng trả lời đồng ý/xác nhận (như: "có", "đồng ý", "ừ", "ok", "tiến hành", "làm đi", "cập nhật đi", "cập nhật nữa", "chuẩn rồi", "thực hiện", "yes", "yep"...):
     BẮT BUỘC viết lại effective_request thành mệnh lệnh hành động đầy đủ nêu rõ thao tác cần thực hiện và chi tiết các mục cần cập nhật/thêm/sửa/xóa theo đề xuất đã trao đổi.
     BẮT BUỘC đặt intent là "takeoff_update" (nếu sửa/cập nhật danh mục bóc tách) hoặc "quotation" (nếu liên quan đến báo giá).

2. YÊU CẦU XUẤT / ĐẨY / HIỂN THỊ KẾT QUẢ BÓC TÁCH HOẶC FILE:
   - Khi người dùng muốn xem kết quả đã tạo, lấy lại file, mở bảng bóc tách hoặc yêu cầu đẩy kết quả ra (ví dụ: "đẩy ra cho tôi phần bóc tách đã bóc", "file chính là các mục đã tạo ấy", "lấy lại file", "mở bảng bóc tách", "đẩy file bóc", "cho tôi xem kết quả đã tạo", "kết quả bóc tách ở đâu"):
     BẮT BUỘC đặt intent là "takeoff_display". Viết lại effective_request yêu cầu hiển thị và trả về danh sách bóc tách và các tệp liên quan.

3. YÊU CẦU THÊM / SỬA / XÓA / TẠO MỚI THIẾT BỊ BÓC TÁCH (CRUD):
   - Khi người dùng yêu cầu chỉnh sửa danh mục bóc tách hiện tại (ví dụ: "thêm vào trong bóc tách", "bổ sung thiết bị...", "sửa thông số...", "xóa lộ...", "cập nhật bóc tách"):
     BẮT BUỘC đặt intent là "takeoff_update". Giữ nguyên các thiết bị khác, chỉ áp dụng thay đổi được chỉ định.

4. CÁC Ý ĐỊNH KHÁC:
   - "takeoff": Khi người dùng yêu cầu bóc tách MỚI hoặc bóc tách lại từ file nguồn bản vẽ.
   - "quotation": Khi người dùng yêu cầu lập bảng báo giá dự toán hoặc chỉnh sửa giá, thuế VAT, chiết khấu.
   - "catalog_update": Khi người dùng yêu cầu đổi hãng/chọn catalog cho thiết bị.
   - "cad": Khi người dùng yêu cầu thao tác trực tiếp trên bản vẽ CAD.
   - "conversation": Khi người dùng chỉ chào hỏi, hỏi giải thích kỹ thuật, hỏi câu hỏi thông tin về bản vẽ/tủ điện mà không yêu cầu thay đổi hay xuất kết quả.

Chỉ trả JSON:
{
  "effective_request": "yêu cầu đầy đủ bằng tiếng Việt, tối đa 10000 ký tự",
  "intent": "conversation|takeoff|takeoff_display|takeoff_update|quotation|catalog_update|cad",
  "new_quotation": false
}
DỮ LIỆU:
''' + json.dumps({'history': history, 'current_request': message,
                  'selected_file_ids': context.get('file_ids') or [],
                  'active_iteration_id': context.get('iteration_id'),
                  'active_quotation_id': context.get('quotation_iteration_id')}, ensure_ascii=False)
    connections = await ConnectionPoolService.get_ordered_connections(db)
    if not connections:
        raise HTTPException(503, 'Chưa có kết nối AI khả dụng cho EL.')
    response, _ = await ConnectionPoolService.call_with_fallback(
        db=db, connections=connections, call_fn=VisionAnalyzerService.analyze_text, prompt=prompt)
    for block in ResponseParserService.extract_json_blocks(response):
        effective = block.get('effective_request') if isinstance(block, dict) else None
        intent = block.get('intent') if isinstance(block, dict) else None
        if (isinstance(effective, str) and 0 < len(effective.strip()) <= 10000
                and intent in ('conversation', 'takeoff', 'takeoff_display', 'takeoff_update', 'quotation', 'catalog_update', 'cad')):
            result = {'original': message, 'effective': effective.strip(), 'intent': intent}
            if intent == 'quotation' and block.get('new_quotation') is True:
                result['new_quotation'] = True
            return result
    # Do not execute a detached request if contextualization failed.
    raise HTTPException(502, 'EL chưa nối được ngữ cảnh hội thoại. Bạn vui lòng thử lại.')
