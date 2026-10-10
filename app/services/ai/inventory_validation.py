"""Do not publish an inventory from an unreadable model response."""
from app.services.ai.response_parser import ResponseParserService
from collections import Counter
import re
import unicodedata


COUNT_PROMPT = '''Kiểm đếm độc lập TOÀN BỘ sơ đồ trên ảnh, không dùng danh sách bóc tách trước.
Trả một JSON {"counts":[{"panel_code":"nhãn tủ","category":"MCB|MCCB|CONTACTOR|TIMER|RELAY|POWER_SUPPLY|OTHER","quantity":1,"evidence":"ký hiệu, nhãn và các nhánh đã đếm"}],"uncertain_regions":[]}.
Đếm từng thân thiết bị vật lý; gộp số lượng theo loại và tủ. Hộp chữ C cùng nhãn 2P sau CB phải kiểm tra riêng là contactor, không đếm vào CB.
Đếm từng TIMER24H riêng. MDK thường là nhãn mạch, không suy thành relay/module khi không có ký hiệu thân xác định.
Giữ thiết bị ngoài tủ riêng, không gộp bơm/van/tải vào thiết bị trong tủ. Không tự sinh phụ kiện.
Với mỗi tủ, trả cả nhóm RELAY và CONTACTOR có quantity=0 nếu không có thân xác định, để phát hiện thiết bị bị suy diễn. Chỉ JSON hợp lệ, không bỏ qua nhóm điều khiển, dự phòng, nguồn và đo lường.'''


def count_mismatches(devices, payload):
    def panel_key(value):
        value = unicodedata.normalize('NFD', str(value or '').upper().replace('Đ', 'D'))
        return re.sub('[^A-Z0-9]', '', ''.join(c for c in value if not unicodedata.combining(c)))
    actual = Counter()
    for device in devices:
        actual[(panel_key(device.panel_code), device.category.upper())] += device.quantity
    differences = []
    counts = payload.get('counts') if isinstance(payload, dict) else None
    if not isinstance(counts, list) or not counts:
        raise ValueError('Không đọc được bảng kiểm đếm độc lập.')
    source = Counter()
    evidence = {}
    for row in counts:
        key = (panel_key(row.get('panel_code')), str(row.get('category') or '').upper())
        expected = row.get('quantity')
        if not key[0] or not key[1] or not isinstance(expected, int) or expected < 0:
            raise ValueError('Bảng kiểm đếm độc lập thiếu tủ, loại hoặc số lượng hợp lệ.')
        source[key] += expected
        evidence.setdefault(key, []).append(str(row.get('evidence') or ''))
    for key, expected in source.items():
        if actual[key] != expected:
            differences.append(f'{key[0]} / {key[1]}: bóc tách {actual[key]}, kiểm đếm nguồn {expected}; {"; ".join(evidence[key])}')
    return differences


def require_inventory(response: str):
    devices = ResponseParserService.parse_device_list(response)
    warnings = ResponseParserService.extract_completeness_warnings(response)
    if not devices:
        raise ValueError("Phản hồi không có danh sách thiết bị đọc được.")
    incomplete = [w for w in warnings if w.startswith("Phản hồi AI chưa đọc đủ:")]
    if incomplete:
        raise ValueError("; ".join(incomplete))
    return devices


async def extract_with_retry(call, prompt: str):
    last_error = None
    for attempt in range(2):
        retry_prompt = prompt
        if attempt:
            retry_prompt += (
                "\nLần trước không đọc đủ danh sách. Trả một JSON hợp lệ duy nhất, "
                "không markdown, không cắt ngắn, không dấu ...; devices là mảng đầy đủ "
                "các thiết bị, mỗi dòng có category, name, quantity. "
                "Quét lại toàn trang, giữ cả contactor, timer và mạch điều khiển."
            )
        response = await call(retry_prompt)
        try:
            return response, require_inventory(response)
        except ValueError as error:
            last_error = error
    raise ValueError(f"Chưa xác nhận được danh sách thiết bị sau khi thử lại: {last_error}")
