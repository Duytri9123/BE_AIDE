"""Do not publish an inventory from an unreadable model response."""
from app.services.ai.response_parser import ResponseParserService
from collections import Counter
import re
import unicodedata
import math


def require_panel_regions(payload):
    regions = payload.get('panels') if isinstance(payload, dict) else None
    if not isinstance(regions, list) or not regions or payload.get('uncertain_regions'):
        raise ValueError('Chưa xác định đầy đủ khung sơ đồ của các tủ')
    result = []
    for region in regions:
        if not isinstance(region, dict) or not str(region.get('panel_code') or '').strip():
            raise ValueError('Khung sơ đồ thiếu mã tủ')
        box = region.get('box_2d')
        if not isinstance(box, list) or len(box) != 4 or any(isinstance(v, bool) or not isinstance(v, (float, int)) or not math.isfinite(v) for v in box):
            raise ValueError('Tọa độ khung sơ đồ không hợp lệ')
        x0,y0,x1,y1=box
        if not (0 <= x0 < x1 <= 1000 and 0 <= y0 < y1 <= 1000):
            raise ValueError('Khung sơ đồ vượt trang hoặc đảo tọa độ')
        for previous in result:
            a,b,c,d=previous['box_2d']
            overlap=max(0,min(c,x1)-max(a,x0))*max(0,min(d,y1)-max(b,y0))
            if overlap > 0.05 * min((c-a)*(d-b),(x1-x0)*(y1-y0)):
                raise ValueError('Các khung sơ đồ chồng lấn; chưa thể đếm độc lập')
        result.append({'panel_code':str(region['panel_code']).strip(),'box_2d':box})
    return result


async def panel_regions_with_retry(call):
    prompt = '''Định vị TOÀN BỘ các khung sơ đồ nguyên lý tủ trên trang; không đếm thiết bị.
Chỉ JSON {"panels":[{"panel_code":"mã tủ trên tiêu đề","box_2d":[x0,y0,x1,y1]}],"uncertain_regions":[]}.
Tọa độ 0–1000 theo toàn ảnh. Mỗi khung bao trọn tiêu đề, nhãn tủ và TẤT CẢ ký hiệu/nhánh, gồm dự phòng, đo lường, nguồn và điều khiển. Không cắt rời đầu vào khỏi các lộ.
Tên tủ trong cột phụ tải là tải được cấp, không phải khung tủ riêng. Không gộp hai khung khác tủ. Nếu không phân vùng đủ, nêu uncertain_regions. Không tự sinh khung từ tên tải.'''
    last_error = None
    for attempt in range(2):
        response = await call(prompt + ('\nSửa tọa độ/mã khung, không chồng lấn và không bỏ sót khung.' if attempt else ''))
        payload = next((b for b in ResponseParserService.extract_json_blocks(response) if isinstance(b, dict) and 'panels' in b), None)
        try:
            return require_panel_regions(payload)
        except ValueError as error:
            last_error = error
    raise ValueError(str(last_error))


COUNT_PROMPT = '''Kiểm đếm độc lập TOÀN BỘ sơ đồ trên ảnh, không dùng danh sách bóc tách trước.
Trả một JSON {"counts":[{"panel_code":"nhãn tủ","category":"CB|MCB|MCCB|CONTACTOR|TIMER|RELAY|POWER_SUPPLY|FUSE|CT|AMMETER|VOLTMETER|INDICATOR|SELECTOR|OTHER","quantity":1,"evidence":"ký hiệu, nhãn và các nhánh đã đếm"}],"uncertain_regions":[]}.
Nguồn chỉ ghi CB thì dùng CB, không suy thành MCB/MCCB từ số cực. Giữ mã tủ đầy đủ, không tự rút gọn TĐ thành TD hoặc đổi tên tủ.
Không đếm một cụm đo lường thành một OTHER: đếm riêng từng đèn, đồng hồ, cầu chì, biến dòng và chuyển mạch. OTHER chỉ là thân thiết bị chưa phân loại, không phải nhóm gom nhiều loại.
Đếm cả nhánh dự phòng có ký hiệu đóng cắt dù không ghi tag, dòng điện hoặc số cực; không tự điền thông số thiếu. Không suy ký hiệu tiếp địa thành cầu đấu hoặc thiết bị mới.
Một ký hiệu cầu chì có hai đầu nối vẫn là một thân cầu chì: không đếm các đầu nối/cực thành quantity. Chỉ tăng số lượng nếu có các thân riêng hoặc nhãn số lượng rõ ràng. Không suy số cầu chì theo số đèn pha.
Đếm từng thân thiết bị vật lý; gộp số lượng theo loại và tủ. Hộp chữ C cùng nhãn 2P sau CB phải kiểm tra riêng là contactor, không đếm vào CB.
Đếm từng TIMER24H riêng. MDK thường là nhãn mạch, không suy thành relay/module khi không có ký hiệu thân xác định.
Giữ thiết bị ngoài tủ riêng, không gộp bơm/van/tải vào thiết bị trong tủ. Không tự sinh phụ kiện.
Với mỗi tủ, trả cả nhóm RELAY và CONTACTOR có quantity=0 nếu không có thân xác định, để phát hiện thiết bị bị suy diễn. Chỉ JSON hợp lệ, không bỏ qua nhóm điều khiển, dự phòng, nguồn và đo lường.'''


def independent_count_prompt(devices):
    """Share panel spellings, never extracted quantities, with the independent count."""
    import json
    panels = sorted({str(d.panel_code).strip() for d in devices if d.panel_code})
    return COUNT_PROMPT + '\nMã tủ đã đọc (chỉ chuẩn hóa cách ghi; vẫn tự đếm trên ảnh): ' + json.dumps(panels, ensure_ascii=False) + '\nNếu cùng tủ, dùng đúng mã trên; nếu ảnh có tủ khác, giữ nhãn nguồn và báo vùng cần xác minh.'


async def count_with_retry(call, prompt, allow_empty=False):
    last_error = None
    for attempt in range(2):
        response = await call(prompt + ('\nBảng kiểm đếm trước chưa đọc được. Trả JSON counts đầy đủ, mã tủ, category và quantity là số nguyên; không markdown hoặc dấu ...' if attempt else ''))
        blocks = ResponseParserService.extract_json_blocks(response)
        payload = next((b for b in blocks if isinstance(b, dict) and 'counts' in b), None)
        try:
            if allow_empty and isinstance(payload, dict) and payload.get('counts') == []:
                return payload
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


def panel_key(value):
    value = unicodedata.normalize('NFD', str(value or '').upper().replace('Đ', 'D'))
    return re.sub('[^A-Z0-9]', '', ''.join(c for c in value if not unicodedata.combining(c)))


def merge_panel_observations(original, observations, devices):
    result = []
    for observed in [*original, *observations]:
        key = panel_key(observed.get('panel_code'))
        code = next((d.panel_code for d in devices if panel_key(d.panel_code) == key), observed.get('panel_code'))
        values = {**observed, 'panel_code': code}
        existing = next((p for p in result if panel_key(p.get('panel_code')) == key), None)
        if existing is not None:
            existing.update({field:value for field,value in values.items() if value})
        else:
            result.append(values)
    return result


def count_mismatches(devices, payload):
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
    for device in devices:
        # Restore an explicitly written branch label, never assign sequential IDs.
        if panel_key(device.tag) in {'', 'CB', 'MCB', 'MCCB'}:
            branch = re.match(r'^\s*(L\d+(?:/[RYB])?)\b', str(device.name or ''), re.I)
            if branch:
                device.tag = branch.group(1)
        if inventory_kind(device.category, device.name, device.spec) in {'CB','MCB','MCCB','RCBO','RCCB'}:
            # Model repairs sometimes retain the written spec but omit numeric
            # fields. Read explicit units; never infer a rating from frame/model.
            specification = str(device.spec or '')
            for field, pattern, converter in (
                ('poles', r'\b([1-4])\s*P\b', int),
                ('in_a', r'(?<![\w.\d])(\d+(?:[.,]\d+)?)\s*A\b', lambda v: float(v.replace(',', '.'))),
                ('icu_ka', r'(?<![\w.\d])(\d+(?:[.,]\d+)?)\s*kA\b', lambda v: float(v.replace(',', '.'))),
            ):
                if getattr(device, field, None) is None:
                    matches = [m.group(1) for m in re.finditer(pattern, specification, re.I)
                               if not re.search(r'\d\s*[-–]\s*$', specification[:m.start()])]
                    if len(matches) == 1:
                        setattr(device, field, converter(matches[0]))
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
