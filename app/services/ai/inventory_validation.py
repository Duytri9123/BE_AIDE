"""Do not publish an inventory from an unreadable model response."""
from app.services.ai.response_parser import ResponseParserService
from collections import Counter
import re
import unicodedata


COUNT_PROMPT = '''Kiểm đếm độc lập TOÀN BỘ sơ đồ trên ảnh, không dùng danh sách bóc tách trước.
Trả một JSON {"counts":[{"panel_code":"nhãn tủ","category":"CB|MCB|MCCB|CONTACTOR|TIMER|RELAY|POWER_SUPPLY|FUSE|CT|AMMETER|VOLTMETER|INDICATOR|SELECTOR|OTHER","quantity":1,"evidence":"ký hiệu, nhãn và các nhánh đã đếm"}],"uncertain_regions":[]}.
Nguồn chỉ ghi CB thì dùng CB, không suy thành MCB/MCCB từ số cực. Giữ mã tủ đầy đủ, không tự rút gọn TĐ thành TD hoặc đổi tên tủ.
Không đếm một cụm đo lường thành một OTHER: đếm riêng từng đèn, đồng hồ, cầu chì, biến dòng và chuyển mạch. OTHER chỉ là thân thiết bị chưa phân loại, không phải nhóm gom nhiều loại.
Đếm cả nhánh dự phòng có ký hiệu đóng cắt dù không ghi tag, dòng điện hoặc số cực; không tự điền thông số thiếu. Không suy ký hiệu tiếp địa thành cầu đấu hoặc thiết bị mới.
Đếm từng thân thiết bị vật lý; gộp số lượng theo loại và tủ. Hộp chữ C cùng nhãn 2P sau CB phải kiểm tra riêng là contactor, không đếm vào CB.
Đếm từng TIMER24H riêng. MDK thường là nhãn mạch, không suy thành relay/module khi không có ký hiệu thân xác định.
Giữ thiết bị ngoài tủ riêng, không gộp bơm/van/tải vào thiết bị trong tủ. Không tự sinh phụ kiện.
Với mỗi tủ, trả cả nhóm RELAY và CONTACTOR có quantity=0 nếu không có thân xác định, để phát hiện thiết bị bị suy diễn. Chỉ JSON hợp lệ, không bỏ qua nhóm điều khiển, dự phòng, nguồn và đo lường.'''


def independent_count_prompt(devices):
    """Share panel spellings, never extracted quantities, with the independent count."""
    import json
    panels = sorted({str(d.panel_code).strip() for d in devices if d.panel_code})
    return COUNT_PROMPT + '\nMã tủ đã đọc (chỉ chuẩn hóa cách ghi; vẫn tự đếm trên ảnh): ' + json.dumps(panels, ensure_ascii=False) + '\nNếu cùng tủ, dùng đúng mã trên; nếu ảnh có tủ khác, giữ nhãn nguồn và báo vùng cần xác minh.'


async def count_with_retry(call, prompt):
    last_error = None
    for attempt in range(2):
        response = await call(prompt + ('\nBảng kiểm đếm trước chưa đọc được. Trả JSON counts đầy đủ, mã tủ, category và quantity là số nguyên; không markdown hoặc dấu ...' if attempt else ''))
        blocks = ResponseParserService.extract_json_blocks(response)
        payload = next((b for b in blocks if isinstance(b, dict) and 'counts' in b), None)
        try:
            count_mismatches([], payload)  # Validate structure; do not borrow extraction counts.
            return payload
        except ValueError as error:
            last_error = error
    raise ValueError(f'Không đọc được kiểm đếm độc lập sau khi thử lại: {last_error}')


def inventory_kind(category, name='', spec=''):
    def key(value):
        value=unicodedata.normalize('NFD',str(value or '').upper().replace('Đ','D'))
        return re.sub('[^A-Z0-9]','', ''.join(c for c in value if not unicodedata.combining(c)))
    kind=key(category)
    label=key(name)
    if kind in {'LIGHT','LAMP','PILOTLAMP','INDICATOR','INDICATORLIGHT','DENBAO'}: return 'LIGHT'
    if kind in {'VOLTMETER','VONKE'}: return 'VOLTMETER'
    if kind in {'AMMETER','AMPEKE'}: return 'AMMETER'
    if kind=='METER':
        voltage=any(term in label for term in ('VON','VOLT','DIENAP'))
        current=any(term in label for term in ('AMPE','AMMETER','DONGDIEN'))
        if voltage and not current: return 'VOLTMETER'
        if current and not voltage: return 'AMMETER'
    if kind in {'SELECTOR','SELECTORSWITCH','CHUYENMACH','CONGTACCHONDIENAP'}: return 'SELECTOR'
    if kind in {'SWITCH','CONGTAC'} and any(term in label for term in ('CHUYENMACH','CHON','SELECTOR')): return 'SELECTOR'
    if kind in {'FUSE','CAUCHI'}: return 'FUSE'
    return kind


def count_mismatches(devices, payload):
    def panel_key(value):
        value = unicodedata.normalize('NFD', str(value or '').upper().replace('Đ', 'D'))
        return re.sub('[^A-Z0-9]', '', ''.join(c for c in value if not unicodedata.combining(c)))
    actual = Counter()
    for device in devices:
        actual[(panel_key(device.panel_code), inventory_kind(device.category,device.name,device.spec))] += device.quantity
    differences = []
    counts = payload.get('counts') if isinstance(payload, dict) else None
    if not isinstance(counts, list) or not counts:
        raise ValueError('Không đọc được bảng kiểm đếm độc lập.')
    source = Counter()
    evidence = {}
    for row in counts:
        if not isinstance(row, dict):
            raise ValueError('Bảng kiểm đếm có dòng không hợp lệ.')
        key = (panel_key(row.get('panel_code')), inventory_kind(row.get('category'),row.get('name') or ''))
        expected = row.get('quantity')
        if not key[0] or not key[1] or not isinstance(expected, int) or isinstance(expected, bool) or expected < 0:
            raise ValueError('Bảng kiểm đếm độc lập thiếu tủ, loại hoặc số lượng hợp lệ.')
        source[key] += expected
        evidence.setdefault(key, []).append(str(row.get('evidence') or ''))
    for key in sorted(source.keys() | actual.keys()):
        expected = source[key]
        if actual[key] != expected:
            differences.append(f'{key[0]} / {key[1]}: bóc tách {actual[key]}, kiểm đếm nguồn {expected}; {"; ".join(evidence.get(key, ["Không có nhóm này trong kiểm đếm độc lập"]))}')
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
