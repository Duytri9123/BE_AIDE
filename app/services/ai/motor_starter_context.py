"""Per-circuit motor starter guidance (DOL, Star-Delta, Reversing, Soft Starter, VFD); functional proposals never become priced BOM rows."""
import re
import math


POWER_FACTORS = {'w': 1, 'kw': 1000, 'hp': 745.699872, 'cv': 735.49875}


def load_power_details(device):
    """Resolve explicit load power within this circuit, retaining its input unit."""
    observations = device.get('source_observations') or {}
    circuit = {**(observations.get('circuit') or {}), **(device.get('circuit_context') or {})}

    def record(value, unit, source):
        if isinstance(value, bool) or not isinstance(value, (int, float, str)):
            return None
        try:
            number = float(str(value).replace(',', '.'))
        except ValueError:
            return None
        unit = str(unit).strip().lower()
        if not math.isfinite(number) or number <= 0 or unit not in POWER_FACTORS:
            return None
        return dict(value=number, unit=unit.upper() if unit != 'kw' else 'kW',
                    watts=number * POWER_FACTORS[unit], source=source)

    for scope, values in (('device', device), ('circuit', circuit)):
        original = record(values.get('power_value'), values.get('power_unit'), f'{scope}.power_value')
        if original:
            return original
        for field, unit in (('power_w', 'w'), ('motor_power_kw', 'kw'),
                            ('motor_power_hp', 'hp'), ('motor_power_cv', 'cv')):
            power = record(values.get(field), unit, f'{scope}.{field}')
            if power:
                return power
        power = record(values.get('power_value'), values.get('power_unit'), f'{scope}.power_value')
        if power:
            return power
    # Never inspect panel-wide notes or other circuits: their ratings may belong
    # to a different motor. Ambiguous alternatives require clarification.
    found = []
    for scope, values, fields in (
        ('circuit', circuit, ('connected_load', 'supply_location', 'motor_power', 'power')),
        ('device', device, ('connected_load', 'name', 'spec', 'observed_text')),
    ):
        for field in fields:
            text = str(values.get(field) or '')
            for match in re.finditer(r'(?<![\w.,/–−-])(\d+(?:[.,]\d+)?)\s*(kW|HP|CV|W)\b', text, re.I):
                # Do not turn a range (2–4 HP) into a single rated value.
                if re.search(r'\d\s*[-–/−]\s*$', text[:match.start()]):
                    return None
                power = record(match[1], match[2], f'{scope}.{field}')
                if power:
                    found.append(power)
    if not found:
        # Hỗ trợ nhận diện số công suất thuần không kèm đơn vị (ví dụ: 3000, 1500, 3.0)
        for scope, values in (('circuit', circuit), ('device', device)):
            for field in ('power', 'motor_power', 'power_w', 'p_w'):
                val = values.get(field)
                if val is not None and not isinstance(val, bool):
                    text = str(val).strip()
                    m = re.search(r'(?<![\w.,/–−-])(\d+(?:[.,]\d+)?)(?!\s*[A-Za-z0-9])', text)
                    if m:
                        try:
                            num = float(m.group(1).replace(',', '.'))
                            if num > 0:
                                unit = 'w' if num >= 100 else 'kw'
                                power = record(num, unit, f'{scope}.{field}_inferred')
                                if power:
                                    return power
                        except ValueError:
                            pass
        # Mặc định công suất 3 kW cho bơm / động cơ nếu mạch khởi động DOL không ghi công suất
        identity = ' '.join(str(device.get(k) or '') for k in ('name', 'category', 'connected_load', 'tag'))
        if re.search(r'bơm|bom|pump|dol|khởi động', identity, re.I):
            return dict(value=3.0, unit='kW', watts=3000.0, source='default_starter_pump')
        return None
    if any(abs(p['watts'] - found[0]['watts']) > max(1, found[0]['watts'] * .02) for p in found):
        return None
    return found[0]


def load_power_w(device):
    power = load_power_details(device)
    return power['watts'] if power else None


def _is_spare_device(device, upstream=None):
    """Return True when the device or its upstream feeder is marked spare/backup."""
    for item in (device, upstream):
        if not isinstance(item, dict):
            continue
        text = ' '.join(str(item.get(k) or '') for k in ('name', 'spec', 'connected_load', 'electrical_function', 'observed_text')).lower()
        if re.search(r'dự\s*phòng|du\s*phong|\bspare\b|\bbackup\b|\breserve\b', text, re.I):
            return True
        if str(item.get('tag') or '').strip().upper() in {'DP', 'SPARE'}:
            return True
    return False


def _norm_cat_group(category: str) -> str:
    cat = str(category or '').strip().upper()
    if cat in {'CB', 'MCB', 'MCCB', 'ACB', 'RCBO', 'RCCB'}:
        return 'BREAKER'
    if cat in {'LIGHT', 'INDICATOR', 'PILOT_LIGHT', 'LAMP'}:
        return 'INDICATOR'
    if cat in {'PUSH_BUTTON', 'PUSHBUTTON', 'BUTTON'}:
        return 'PUSH_BUTTON'
    if cat in {'SELECTOR', 'SELECTOR_SWITCH', 'SWITCH'}:
        return 'SELECTOR'
    return cat


def _collect_category_brands(devices):
    """Find dominant explicit brand per device category and overall across the file."""
    from collections import Counter
    cat_counts = {}
    overall = Counter()
    ignored = {'', 'asian', 'asia', 'oem', '-', '---', 'chưa xác định', 'đang đối chiếu...', 'chọn hãng'}
    for d in devices:
        if not isinstance(d, dict):
            continue
        b = str(d.get('brand') or '').strip()
        if b.casefold() in ignored:
            continue
        grp = _norm_cat_group(d.get('category'))
        if grp:
            cat_counts.setdefault(grp, Counter())[b] += 1
        overall[b] += 1
        ms = (d.get('source_observations') or {}).get('motor_starter') or {}
        for comp in (ms.get('components') or []):
            if not isinstance(comp, dict):
                continue
            cb = str(comp.get('brand') or '').strip()
            if cb.casefold() not in ignored:
                cgrp = _norm_cat_group(comp.get('category'))
                if cgrp:
                    cat_counts.setdefault(cgrp, Counter())[cb] += 1
    cat_brand = {grp: cnt.most_common(1)[0][0] for grp, cnt in cat_counts.items() if cnt}
    default_brand = overall.most_common(1)[0][0] if overall else 'Schneider'
    return cat_brand, default_brand


def starter_quotation_name(device):
    observations = device.get('source_observations') or {}
    assembly = observations.get('motor_starter') or {}
    kind = assembly.get('type') or classify_motor_starter_type(' '.join(str(device.get(k) or '') for k in ('name', 'category', 'spec')))
    if not kind:
        name = device.get('name') or 'Thiết bị'
        if _is_spare_device(device) and 'dự phòng' not in name.lower():
            name += ' (Dự phòng)'
        return name
    name = {'DOL': 'Khởi động DOL', 'STAR_DELTA': 'Khởi động sao – tam giác',
            'REVERSING': 'Khởi động đảo chiều', 'SOFT_STARTER': 'Khởi động mềm', 'VFD': 'Biến tần'}.get(kind, device.get('name') or kind)
    power = load_power_details(device)
    if power:
        unit, value = power['unit'], power['value']
        if unit == 'W' and value >= 1000:
            value, unit = value / 1000, 'kW'
        name += f" {value:g}{unit}"
    if (_is_spare_device(device) or assembly.get('is_spare')) and 'dự phòng' not in name.lower():
        name += ' (Dự phòng)'
    return name


def classify_motor_starter_type(identity: str) -> str | None:
    if not identity:
        return None
    if re.search(r'\b(?:Y[-/]?\s*Δ|Y[-/]?\s*D|STAR[-_\s]*DELTA|SAO\s*[-–]?\s*TAM\s*GIÁC)\b', identity, re.I):
        return 'STAR_DELTA'
    if re.search(r'\b(?:REV|REVERSING|F[-_/]?R|FORWARD[-_\s]*REVERSE|ĐẢO\s*CHIỀU)\b', identity, re.I):
        return 'REVERSING'
    if re.search(r'\b(?:SOFT[-_\s]*STARTER|KĐ\s*MỀM|KHỞI\s*ĐỘNG\s*MỀM|\bSS\b)\b', identity, re.I):
        return 'SOFT_STARTER'
    if re.search(r'\b(?:VFD|INV|INVERTER|BIẾN\s*TẦN|VVVF)\b', identity, re.I):
        return 'VFD'
    if re.search(r'\bD\.?O\.?L\.?\b|khởi động trực tiếp|direct.on.line', identity, re.I):
        return 'DOL'
    return None


def is_direct_starter_label(row):
    labels = (str(row.get(field) or '').strip() for field in ('observed_text', 'spec'))
    return bool(any(re.fullmatch(r'D\.?\s*O\.?\s*L\.?', label, re.I) for label in labels) or
                re.search(r'khởi động trực tiếp|direct.on.line', str(row.get('name') or ''), re.I))


def is_motor_starter_label(row):
    identity = ' '.join(str(row.get(k) or '') for k in ('observed_text', 'spec', 'name', 'category', 'electrical_function'))
    return bool(classify_motor_starter_type(identity))


def select_contactor_spec(current_a, voltage_v=380, power_w=None):
    """Tính chọn dòng định mức contactor động lực AC-3."""
    if not current_a and power_w:
        current_a = power_w / (math.sqrt(3) * voltage_v * 0.72) if voltage_v >= 380 else power_w / (voltage_v * 0.72)
    current_a = current_a or 9
    required_a = current_a * 1.25
    standards = [9, 12, 18, 22, 32, 40, 50, 65, 75, 85, 100, 125, 150, 185, 225, 300]
    chosen = standards[-1]
    for std in standards:
        if std >= required_a:
            chosen = std
            break
    poles = 3 if voltage_v >= 380 else 1
    return f"{poles}P {chosen}A 220VAC", chosen


def select_tor_spec(current_a, power_w=None, voltage_v=380):
    """Tính chọn dải chỉnh định rơ le nhiệt bảo vệ quá tải."""
    if not current_a and power_w:
        current_a = power_w / (math.sqrt(3) * voltage_v * 0.72) if voltage_v >= 380 else power_w / (voltage_v * 0.72)
    current_a = current_a or 6.5
    ranges = [
        (0.63, 1.0), (1.0, 1.6), (1.6, 2.5), (2.5, 4.0), (4.0, 6.0),
        (5.0, 8.0), (6.0, 9.0), (7.0, 10.0), (9.0, 13.0), (12.0, 18.0),
        (16.0, 22.0), (18.0, 26.0), (24.0, 36.0), (28.0, 40.0),
        (34.0, 50.0), (45.0, 65.0), (54.0, 75.0), (63.0, 85.0), (70.0, 95.0)
    ]
    for low, high in ranges:
        if low <= current_a <= high:
            return f"Dải {low:g}-{high:g}A", f"{low:g}-{high:g}A"
    return f"Dải {current_a*0.8:.1f}-{current_a*1.2:.1f}A", f"{current_a:.1f}A"


def classify_assembly_type(identity: str) -> str | None:
    starter = classify_motor_starter_type(identity)
    if starter:
        return starter
    if re.search(r'\bATS\b|bộ chuyển nguồn|chuyển nguồn tự động', identity, re.I):
        return 'ATS'
    if re.search(r'tụ bù|bù công suất|\bAPFC\b|\bkVAr\b|capacitor\s*bank', identity, re.I):
        return 'CAPACITOR_BANK'
    if re.search(r'chiếu sáng.*(?:tự động|hẹn giờ|timer|contactor)|(?:hẹn giờ|timer).*chiếu sáng', identity, re.I):
        return 'LIGHTING_CONTROL'
    return None


def enrich_motor_starters(devices):
    from app.services.ai.assembly_accessories import propose_assembly_accessories, SOURCES
    from app.services.ai.assembly_accessory_selection import merge_proposal_choices
    cat_brands, file_default_brand = _collect_category_brands(devices)
    for device in devices:
        identity = ' '.join(str(device.get(k) or '') for k in ('category', 'name', 'spec', 'electrical_function', 'observed_text'))
        observations = device.get('source_observations')
        observations = dict(observations) if isinstance(observations, dict) else {}
        existing_assembly = observations.get('motor_starter') or observations.get('assembly') or {}
        starter_type = classify_motor_starter_type(identity)
        assembly_type = starter_type or classify_assembly_type(identity) or existing_assembly.get('type')
        has_custom_assembly = bool(existing_assembly.get('components')) or device.get('record_kind') == 'assembly'
        if not assembly_type and not has_custom_assembly:
            continue
        if not assembly_type and has_custom_assembly:
            assembly_type = 'CUSTOM_ASSEMBLY'
        circuit = {**(observations.get('circuit') or {}), **(device.get('circuit_context') or {})}
        power_input = load_power_details(device)
        power_w = power_input['watts'] if power_input else None
        reference = str(device.get('upstream_device') or '').strip()
        canonical = lambda value: re.sub(r'[^\w]', '', str(value or '')).casefold()
        matches = [d for d in devices if d is not device and reference and
                   str(d.get('category') or '').upper() in {'MCB', 'MCCB', 'MPCB', 'RCBO', 'RCCB', 'ACB'} and
                   canonical(reference) in {canonical(d.get('tag')), canonical(d.get('spec')),
                       canonical(str(d.get('category') or '')+' '+str(d.get('spec') or ''))} and
                   all(d.get(k) == device.get(k) for k in ('source_file_id', 'panel_code', 'source_page'))]
        upstream = matches[0] if len(matches) == 1 else None
        if not upstream and device.get('tag'):
            matches = [d for d in devices if d is not device and
                       str(d.get('category') or '').upper() in {'MCB', 'MCCB', 'MPCB', 'RCBO', 'RCCB', 'ACB'} and
                       canonical(d.get('tag')) == canonical(device['tag']) and
                       all(d.get(k) == device.get(k) for k in ('source_file_id', 'panel_code', 'source_page'))]
            upstream = matches[0] if len(matches) == 1 else None
        if not reference and not upstream and device.get('connected_load'):
            matches = [d for d in devices if d is not device and
                       str(d.get('category') or '').upper() in {'MCB', 'MCCB', 'MPCB', 'RCBO', 'RCCB', 'ACB'} and
                       canonical(d.get('connected_load')) == canonical(device['connected_load']) and
                       all(d.get(k) == device.get(k) for k in ('source_file_id', 'panel_code', 'source_page'))]
            upstream = matches[0] if len(matches) == 1 else None
        relationship_verified = bool(upstream and (device.get('evidence_region') or {}).get('load_verified') is True
                                     and (upstream.get('evidence_region') or {}).get('load_verified') is True)

        if upstream:
            upstream_obs = upstream.get('source_observations') or {}
            upstream_circuit = upstream_obs.get('circuit') or upstream.get('circuit_context') or {}
            for k, v in upstream_circuit.items():
                if v and not circuit.get(k):
                    circuit[k] = v
            if not power_input:
                power_input = load_power_details(upstream)
                power_w = power_input['watts'] if power_input else None

        if not power_w:
            power_w = 3000.0
            power_input = dict(value=3.0, unit='kW', watts=3000.0, source='default_starter_pump')

        # Nhận diện quy cách cáp để xác định pha và điện áp (mạch khởi động động cơ mặc định 3P 380V nếu không ghi 1P)
        cable_spec = str(circuit.get('cable_spec') or circuit.get('cable') or device.get('cable_spec') or '')
        if re.search(r'\b(?:1|2)\s*[xX]\s*(\d+(?:[.,]\d+)?)', cable_spec) or re.search(r'\b1P\b|220\s*V', str(device.get('spec') or ''), re.I):
            circuit.setdefault('phase', '1P')
            circuit.setdefault('motor_voltage_v', 220)
            circuit.setdefault('control_voltage_v', 220)
        else:
            circuit.setdefault('phase', '3P')
            circuit.setdefault('motor_voltage_v', 380)
            circuit.setdefault('control_voltage_v', 220)

        motor_voltage = circuit.get('motor_voltage_v') or (380 if circuit.get('phase') in ('3P', '3 pha', '3') else 220)
        circuit['motor_voltage_v'] = motor_voltage
        circuit.setdefault('control_voltage_v', 220)

        motor_current = circuit.get('motor_rated_current_a')
        if not motor_current and power_w:
            if motor_voltage >= 380:
                motor_current = round(power_w / (math.sqrt(3) * motor_voltage * 0.85 * 0.85), 1)
            else:
                motor_current = round(power_w / (motor_voltage * 0.85 * 0.85), 1)
            circuit['motor_rated_current_a'] = motor_current

        if power_input and not device.get('spec'):
            device['spec'] = f"{power_input['value']:g}{power_input['unit']} {motor_voltage}V"

        missing = []
        brand = device.get('brand') or (upstream.get('brand') if upstream else None) or cat_brands.get('BREAKER') or cat_brands.get('CONTACTOR') or file_default_brand or 'Schneider'
        brand_key = 'LS' if 'ls' in brand.lower() else 'Chint' if 'chint' in brand.lower() else 'Schneider'
        control_brand = cat_brands.get('INDICATOR') or cat_brands.get('PUSH_BUTTON') or cat_brands.get('SELECTOR') or brand
        control_brand_key = 'LS' if 'ls' in control_brand.lower() else 'Chint' if 'chint' in control_brand.lower() else 'Schneider'

        def _contactor_sku(b_key, amps):
            if b_key == 'LS':
                if amps <= 9: return 'MC-9b'
                if amps <= 12: return 'MC-12b'
                if amps <= 18: return 'MC-18b'
                if amps <= 22: return 'MC-22b'
                if amps <= 32: return 'MC-32a'
                if amps <= 40: return 'MC-40a'
                if amps <= 50: return 'MC-50a'
                if amps <= 65: return 'MC-65a'
                if amps <= 75: return 'MC-75a'
                return f'MC-{amps}a'
            if b_key == 'Chint':
                if amps <= 9: return 'NC1-0901'
                if amps <= 12: return 'NC1-1201'
                if amps <= 18: return 'NC1-1801'
                if amps <= 25: return 'NC1-2510'
                if amps <= 32: return 'NC1-3210'
                if amps <= 40: return 'NC1-4011'
                if amps <= 50: return 'NC1-5011'
                if amps <= 65: return 'NC1-6511'
                return f'NC1-{amps}11'
            if amps <= 9: return 'LC1E0901M7'
            if amps <= 12: return 'LC1E1201M7'
            if amps <= 18: return 'LC1E1801M7'
            if amps <= 25: return 'LC1E2510M7'
            if amps <= 32: return 'LC1E3210M7'
            if amps <= 40: return 'LC1E40M7'
            if amps <= 50: return 'LC1E50M7'
            if amps <= 65: return 'LC1E65M7'
            return f'LC1E{amps}M7'

        def _tor_sku(b_key, amps):
            if b_key == 'LS':
                return 'MT-32/3K' if amps <= 32 else 'MT-63/3K' if amps <= 63 else 'MT-95/3K'
            if b_key == 'Chint':
                return 'NR2-25' if amps <= 25 else 'NR2-36' if amps <= 36 else 'NR2-93'
            return 'LRE12' if amps <= 10 else 'LRE22' if amps <= 25 else 'LRE32' if amps <= 36 else 'LRE355'

        pilot_skus = {
            'Schneider': {'selector': 'XB5AD33', 'buttonOn': 'XB5AW33B5', 'buttonOff': 'XB5AW34B5', 'tripLight': 'XB5AVM5', 'relay': 'RXM2AB2P7', 'timer': 'RE17RMMU'},
            'LS': {'selector': 'NP2-BD33', 'buttonOn': 'NP2-BW33', 'buttonOff': 'NP2-BW34', 'tripLight': 'ND16-22D Vàng', 'relay': 'MY2N-GS 220VAC', 'timer': 'AT8N 220VAC'},
            'Chint': {'selector': 'NP2-BD33', 'buttonOn': 'NP2-BW33', 'buttonOff': 'NP2-BW34', 'tripLight': 'ND16-22D Vàng', 'relay': 'JQX-13F 220V', 'timer': 'JSZ3A-A'},
        }
        ctrl_skus = pilot_skus[control_brand_key]
        pwr_skus = pilot_skus[brand_key]
        pilot_skus = {**pwr_skus, 'selector': ctrl_skus['selector'], 'buttonOn': ctrl_skus['buttonOn'],
                      'buttonOff': ctrl_skus['buttonOff'], 'tripLight': ctrl_skus['tripLight']}

        def _control_components(reversing=False):
            buttons = (
                [
                    {'category': 'PUSH_BUTTON', 'name': 'Nút nhấn ON Thuận có đèn (Xanh)', 'spec': 'Nút nhấn nhả có đèn (Xanh)',
                     'part_number': pilot_skus['buttonOn'], 'sku': pilot_skus['buttonOn'], 'quantity': 1, 'unit': 'Cái',
                     'use_in_quotation': True, 'brand': control_brand, 'requires_same_brand': False, 'status': 'confirmed', 'basis': 'assembly_function',
                     'reason': 'Khởi động chạy thuận và báo trạng thái CHẠY THUẬN'},
                    {'category': 'PUSH_BUTTON', 'name': 'Nút nhấn ON Nghịch có đèn (Xanh)', 'spec': 'Nút nhấn nhả có đèn (Xanh)',
                     'part_number': pilot_skus['buttonOn'], 'sku': pilot_skus['buttonOn'], 'quantity': 1, 'unit': 'Cái',
                     'use_in_quotation': True, 'brand': control_brand, 'requires_same_brand': False, 'status': 'confirmed', 'basis': 'assembly_function',
                     'reason': 'Khởi động chạy nghịch và báo trạng thái CHẠY NGHỊCH'},
                ] if reversing else [
                    {'category': 'PUSH_BUTTON', 'name': 'Nút nhấn ON có đèn (Xanh)', 'spec': 'Nút nhấn nhả có đèn (Xanh)',
                     'part_number': pilot_skus['buttonOn'], 'sku': pilot_skus['buttonOn'], 'quantity': 1, 'unit': 'Cái',
                     'use_in_quotation': True, 'brand': control_brand, 'requires_same_brand': False, 'status': 'confirmed', 'basis': 'assembly_function',
                     'reason': 'Khởi động chạy tay và tích hợp đèn báo trạng thái CHẠY'},
                ]
            )
            return [
                {'category': 'SELECTOR', 'name': 'Công tắc chuyển mạch 3 vị trí', 'spec': 'Tay - 0 - Tự động',
                 'part_number': pilot_skus['selector'], 'sku': pilot_skus['selector'], 'quantity': 1, 'unit': 'Cái',
                 'use_in_quotation': True, 'brand': control_brand, 'requires_same_brand': False, 'status': 'confirmed', 'basis': 'assembly_function',
                 'reason': 'Chọn chế độ vận hành Tay - 0 - Tự động (MAN-OFF-AUTO)'},
                *buttons,
                {'category': 'PUSH_BUTTON', 'name': 'Nút nhấn OFF có đèn (Đỏ)', 'spec': 'Nút nhấn nhả có đèn (Đỏ)',
                 'part_number': pilot_skus['buttonOff'], 'sku': pilot_skus['buttonOff'], 'quantity': 1, 'unit': 'Cái',
                 'use_in_quotation': True, 'brand': control_brand, 'requires_same_brand': False, 'status': 'confirmed', 'basis': 'assembly_function',
                 'reason': 'Dừng chạy tay và tích hợp đèn báo trạng thái DỪNG'},
                {'category': 'INDICATOR', 'name': 'Đèn báo sự cố (TRIP - Vàng)', 'spec': 'Đèn báo sự cố (Vàng)',
                 'part_number': pilot_skus['tripLight'], 'sku': pilot_skus['tripLight'], 'quantity': 1, 'unit': 'Cái',
                 'use_in_quotation': True, 'brand': control_brand, 'requires_same_brand': False, 'status': 'confirmed', 'basis': 'assembly_function',
                 'reason': 'Báo lỗi sự cố quá tải / trip thiết bị'},
                {'category': 'RELAY', 'name': 'Rơ le trung gian (Kèm đế)',
                 'spec': (
                     '8 chân dẹp (2CO) 220VAC kèm đế ray' if re.search(r'RXM2|MY2|2Z|2CO', str(pilot_skus.get('relay') or ''), re.I)
                     else ('14 chân dẹp (4CO) 220VAC kèm đế ray' if re.search(r'RXM4|MY4|4Z|4CO', str(pilot_skus.get('relay') or ''), re.I)
                           else '220VAC kèm đế ray (số chân theo sơ đồ mạch)')
                 ),
                 'part_number': pilot_skus['relay'], 'sku': pilot_skus['relay'], 'quantity': 1, 'unit': 'Bộ',
                 'use_in_quotation': True, 'brand': brand, 'requires_same_brand': False, 'status': 'confirmed', 'basis': 'assembly_function',
                 'reason': 'Tự giữ mạch điều khiển, liên động phao / mức nước / BMS (số chân khớp theo mã rơ le 2CO/4CO)'},
            ]

        poles_count = 3 if motor_voltage >= 380 else 1
        power_label = f"{power_input['value']:g}{power_input['unit']}" if power_input else '3kW'

        if starter_type == 'STAR_DELTA':
            km_main_spec, km_main_a = select_contactor_spec(motor_current * 0.58 if motor_current else None, motor_voltage, power_w)
            km_star_spec, km_star_a = select_contactor_spec(motor_current * 0.33 if motor_current else None, motor_voltage, power_w)
            _, tor_range = select_tor_spec(motor_current * 0.58 if motor_current else None, power_w, motor_voltage)
            km_main_sku = _contactor_sku(brand_key, km_main_a)
            km_star_sku = _contactor_sku(brand_key, km_star_a)
            tor_sku = _tor_sku(brand_key, motor_current * 0.58 if motor_current else 12)
            components = [
                {'category': 'CONTACTOR', 'name': f'Contactor chính {poles_count}P {km_main_a}A (KM-Main)', 'spec': km_main_spec,
                 'part_number': km_main_sku, 'sku': km_main_sku, 'quantity': 1, 'unit': 'Cái', 'in_a': km_main_a, 'poles': poles_count,
                 'use_in_quotation': True, 'brand': brand, 'requires_same_brand': True, 'status': 'confirmed', 'basis': 'assembly_function',
                 'reason': f'Đóng cắt nguồn chính (0.58×Iđm ≈ {round((motor_current or 0)*0.58, 1)}A).'},
                {'category': 'CONTACTOR', 'name': f'Contactor tam giác {poles_count}P {km_main_a}A (KM-Delta)', 'spec': km_main_spec,
                 'part_number': km_main_sku, 'sku': km_main_sku, 'quantity': 1, 'unit': 'Cái', 'in_a': km_main_a, 'poles': poles_count,
                 'use_in_quotation': True, 'brand': brand, 'requires_same_brand': True, 'status': 'confirmed', 'basis': 'assembly_function',
                 'reason': 'Đóng mạch chạy chế độ tam giác.'},
                {'category': 'CONTACTOR', 'name': f'Contactor sao {poles_count}P {km_star_a}A (KM-Star)', 'spec': km_star_spec,
                 'part_number': km_star_sku, 'sku': km_star_sku, 'quantity': 1, 'unit': 'Cái', 'in_a': km_star_a, 'poles': poles_count,
                 'use_in_quotation': True, 'brand': brand, 'requires_same_brand': True, 'status': 'confirmed', 'basis': 'assembly_function',
                 'reason': f'Đóng điểm sao khởi động ban đầu (0.33×Iđm ≈ {round((motor_current or 0)*0.33, 1)}A).'},
                {'category': 'OVERLOAD_PROTECTION', 'name': f'Rơ le nhiệt {tor_range}', 'spec': f'Dải {tor_range}',
                 'part_number': tor_sku, 'sku': tor_sku, 'quantity': 1, 'unit': 'Cái',
                 'use_in_quotation': True, 'brand': brand, 'requires_same_brand': True, 'status': 'confirmed', 'basis': 'assembly_function',
                 'reason': 'Bảo vệ quá tải nhiệt động cơ (gắn sau contactor chính, cùng hãng).'},
                {'category': 'TIMER', 'name': 'Rơ le thời gian Sao - Tam giác', 'spec': '220VAC 0-30s',
                 'part_number': pilot_skus['timer'], 'sku': pilot_skus['timer'], 'quantity': 1, 'unit': 'Cái',
                 'use_in_quotation': True, 'brand': brand, 'requires_same_brand': False, 'status': 'confirmed', 'basis': 'assembly_function',
                 'reason': 'Chuyển mạch từ cấp sao sang tam giác.'},
                *_control_components(),
            ]
        elif starter_type == 'REVERSING':
            km_spec, km_a = select_contactor_spec(motor_current, motor_voltage, power_w)
            _, tor_range = select_tor_spec(motor_current, power_w, motor_voltage)
            km_sku = _contactor_sku(brand_key, km_a)
            tor_sku = _tor_sku(brand_key, motor_current or 12)
            components = [
                {'category': 'CONTACTOR', 'name': f'Contactor quay thuận {poles_count}P {km_a}A (KM-Forward)', 'spec': km_spec,
                 'part_number': km_sku, 'sku': km_sku, 'quantity': 1, 'unit': 'Cái', 'in_a': km_a, 'poles': poles_count,
                 'use_in_quotation': True, 'brand': brand, 'requires_same_brand': True, 'status': 'confirmed', 'basis': 'assembly_function',
                 'reason': f'Đóng mạch quay chiều thuận (Iđm ~{motor_current}A).'},
                {'category': 'CONTACTOR', 'name': f'Contactor quay nghịch {poles_count}P {km_a}A (KM-Reverse)', 'spec': km_spec,
                 'part_number': km_sku, 'sku': km_sku, 'quantity': 1, 'unit': 'Cái', 'in_a': km_a, 'poles': poles_count,
                 'use_in_quotation': True, 'brand': brand, 'requires_same_brand': True, 'status': 'confirmed', 'basis': 'assembly_function',
                 'reason': 'Đóng mạch quay chiều nghịch (khóa chéo liên động cơ/điện).'},
                {'category': 'OVERLOAD_PROTECTION', 'name': f'Rơ le nhiệt {tor_range}', 'spec': f'Dải {tor_range}',
                 'part_number': tor_sku, 'sku': tor_sku, 'quantity': 1, 'unit': 'Cái',
                 'use_in_quotation': True, 'brand': brand, 'requires_same_brand': True, 'status': 'confirmed', 'basis': 'assembly_function',
                 'reason': f'Bảo vệ quá tải nhiệt động cơ (chỉnh định tại ~{motor_current}A, cùng hãng contactor).'},
                *_control_components(reversing=True),
            ]
        elif starter_type == 'SOFT_STARTER':
            components = [
                {'category': 'SOFT_STARTER', 'name': f'Bộ khởi động mềm {power_label}', 'spec': f'{poles_count}P {power_label} {motor_voltage}V (~{motor_current}A)',
                 'part_number': '', 'sku': '', 'quantity': 1, 'unit': 'Bộ', 'in_a': motor_current, 'poles': poles_count,
                 'use_in_quotation': True, 'brand': brand, 'requires_same_brand': True, 'status': 'confirmed', 'basis': 'assembly_function',
                 'reason': f'Điều khiển khởi động êm giảm dòng mở máy cho tải {power_label} ({motor_voltage}V).'},
                *_control_components(),
            ]
        elif starter_type == 'VFD':
            components = [
                {'category': 'VFD', 'name': f'Biến tần {power_label}', 'spec': f'{poles_count}P {power_label} {motor_voltage}V (~{motor_current}A)',
                 'part_number': '', 'sku': '', 'quantity': 1, 'unit': 'Bộ', 'in_a': motor_current, 'poles': poles_count,
                 'use_in_quotation': True, 'brand': brand, 'requires_same_brand': True, 'status': 'confirmed', 'basis': 'assembly_function',
                 'reason': f'Điều khiển tốc độ vô cấp và bảo vệ động cơ {power_label} ({motor_voltage}V).'},
                *_control_components(),
            ]
        elif assembly_type == 'ATS':
            ats_amps = device.get('in_a') or int(max(63, motor_current or 63))
            ats_poles = device.get('poles') or 4
            components = [
                {'category': 'ATS', 'name': f'Bộ chuyển nguồn tự động ATS {ats_poles}P {ats_amps}A', 'spec': device.get('spec') or f'{ats_poles}P {ats_amps}A',
                 'part_number': device.get('part_number') or '', 'sku': device.get('sku') or '', 'quantity': 1, 'unit': 'Bộ', 'in_a': ats_amps, 'poles': ats_poles,
                 'use_in_quotation': True, 'brand': brand, 'requires_same_brand': True, 'status': 'confirmed', 'basis': 'assembly_function',
                 'reason': 'Đóng cắt chuyển đổi tự động giữa nguồn lưới và nguồn dự phòng.'},
                {'category': 'PHASE_RELAY', 'name': 'Rơ le bảo vệ mất pha / thấp áp', 'spec': '3P 380VAC',
                 'part_number': '', 'sku': '', 'quantity': 1, 'unit': 'Cái',
                 'use_in_quotation': True, 'brand': brand, 'requires_same_brand': False, 'status': 'confirmed', 'basis': 'assembly_function',
                 'reason': 'Giám sát chất lượng điện áp nguồn lưới/máy phát.'},
                {'category': 'SELECTOR', 'name': 'Công tắc chuyển mạch 3 vị trí', 'spec': 'Tay - 0 - Tự động',
                 'part_number': pilot_skus['selector'], 'sku': pilot_skus['selector'], 'quantity': 1, 'unit': 'Cái',
                 'use_in_quotation': True, 'brand': brand, 'requires_same_brand': False, 'status': 'confirmed', 'basis': 'assembly_function',
                 'reason': 'Chọn chế độ vận hành Tay - 0 - Tự động.'},
                {'category': 'INDICATOR', 'name': 'Đèn báo nguồn A / Nguồn B / Tải', 'spec': 'Đèn báo trạng thái',
                 'part_number': pilot_skus['tripLight'], 'sku': pilot_skus['tripLight'], 'quantity': 3, 'unit': 'Cái',
                 'use_in_quotation': True, 'brand': brand, 'requires_same_brand': False, 'status': 'confirmed', 'basis': 'assembly_function',
                 'reason': 'Hiển thị trạng thái có điện các nguồn và đóng tải.'},
            ]
        elif assembly_type == 'CAPACITOR_BANK':
            kvar_match = re.search(r'(\d+(?:[.,]\d+)?)\s*kVAr', identity, re.I)
            kvar_val = kvar_match.group(1) if kvar_match else '50'
            components = [
                {'category': 'POWER_FACTOR_CONTROLLER', 'name': 'Bộ điều khiển tụ bù tự động (APFC)', 'spec': '6-12 cấp 220/380VAC',
                 'part_number': '', 'sku': '', 'quantity': 1, 'unit': 'Bộ',
                 'use_in_quotation': True, 'brand': brand, 'requires_same_brand': True, 'status': 'confirmed', 'basis': 'assembly_function',
                 'reason': f'Điều khiển đóng cắt các cấp tụ bù hệ số công suất ({kvar_val}kVAr).'},
                {'category': 'CONTACTOR', 'name': 'Contactor đóng cắt tụ bù', 'spec': '3P chuyên dụng tụ bù',
                 'part_number': '', 'sku': '', 'quantity': 1, 'unit': 'Cái',
                 'use_in_quotation': True, 'brand': brand, 'requires_same_brand': True, 'status': 'confirmed', 'basis': 'assembly_function',
                 'reason': 'Đóng cắt cấp tụ bù có điện trở hạn dòng khởi động.'},
                {'category': 'CAPACITOR', 'name': f'Tụ bù hạ thế {kvar_val}kVAr', 'spec': f'3P {kvar_val}kVAr 440V',
                 'part_number': '', 'sku': '', 'quantity': 1, 'unit': 'Bộ',
                 'use_in_quotation': True, 'brand': brand, 'requires_same_brand': True, 'status': 'confirmed', 'basis': 'assembly_function',
                 'reason': f'Bù công suất phản kháng tổng {kvar_val}kVAr.'},
                {'category': 'SELECTOR', 'name': 'Công tắc chuyển mạch 3 vị trí', 'spec': 'Tay - 0 - Tự động',
                 'part_number': pilot_skus['selector'], 'sku': pilot_skus['selector'], 'quantity': 1, 'unit': 'Cái',
                 'use_in_quotation': True, 'brand': brand, 'requires_same_brand': False, 'status': 'confirmed', 'basis': 'assembly_function',
                 'reason': 'Chọn chế độ đóng cắt tụ Tay - 0 - Tự động.'},
            ]
        elif assembly_type == 'LIGHTING_CONTROL':
            km_spec, km_a = select_contactor_spec(motor_current, motor_voltage, power_w)
            km_sku = _contactor_sku(brand_key, km_a)
            components = [
                {'category': 'CONTACTOR', 'name': f'Contactor chiếu sáng {poles_count}P {km_a}A', 'spec': km_spec,
                 'part_number': km_sku, 'sku': km_sku, 'quantity': 1, 'unit': 'Cái', 'in_a': km_a, 'poles': poles_count,
                 'use_in_quotation': True, 'brand': brand, 'requires_same_brand': True, 'status': 'confirmed', 'basis': 'assembly_function',
                 'reason': 'Đóng cắt mạch chiếu sáng tự động/từ xa.'},
                {'category': 'TIMER', 'name': 'Rơ le thời gian 24h (Timer)', 'spec': '220VAC lập trình theo giờ',
                 'part_number': pilot_skus['timer'], 'sku': pilot_skus['timer'], 'quantity': 1, 'unit': 'Cái',
                 'use_in_quotation': True, 'brand': brand, 'requires_same_brand': False, 'status': 'confirmed', 'basis': 'assembly_function',
                 'reason': 'Hẹn giờ bật/tắt hệ thống chiếu sáng tự động.'},
                *_control_components(),
            ]
        elif assembly_type == 'CUSTOM_ASSEMBLY':
            components = list(existing_assembly.get('components') or [])
        else: # DOL
            contactor_spec, contactor_a = select_contactor_spec(motor_current, motor_voltage, power_w)
            _, tor_range = select_tor_spec(motor_current, power_w, motor_voltage)
            km_sku = _contactor_sku(brand_key, contactor_a)
            tor_sku = _tor_sku(brand_key, motor_current or 9)
            c_spec_short = f"{poles_count}P {contactor_a}A"

            components = [
                {'category': 'CONTACTOR', 'name': f'Contactor {c_spec_short}', 'spec': f'{c_spec_short} 220VAC',
                 'part_number': km_sku, 'sku': km_sku, 'quantity': 1, 'unit': 'Cái',
                 'in_a': contactor_a, 'poles': poles_count, 'use_in_quotation': True,
                 'brand': brand, 'requires_same_brand': True, 'status': 'confirmed', 'basis': 'assembly_function',
                 'reason': f'Contactor {c_spec_short} đóng cắt nguồn động lực cho tải (Iđm ~{motor_current}A)'},
                {'category': 'OVERLOAD_PROTECTION', 'name': f'Rơ le nhiệt {tor_range}', 'spec': f'Dải {tor_range}',
                 'part_number': tor_sku, 'sku': tor_sku, 'quantity': 1, 'unit': 'Cái',
                 'use_in_quotation': True, 'brand': brand, 'requires_same_brand': True, 'status': 'confirmed', 'basis': 'assembly_function',
                 'reason': f'Rơ le nhiệt bảo vệ quá tải động cơ (chỉnh định tại ~{motor_current}A)'},
                *_control_components(),
            ]

        # Keep explicit per-assembly inputs when enrichment runs again.
        existing = (existing_assembly.get('components') or [])
        if assembly_type != 'CUSTOM_ASSEMBLY' and (
            len(existing) < 4 or any(c.get('spec') is None or c.get('spec') == 'Chưa xác định thông số' or c.get('quantity') is None for c in existing if isinstance(c, dict))
        ):
            existing = []
        explicit = [c for c in existing if isinstance(c, dict) and
                    (c.get('basis') in {'source', 'user_request'} or c.get('status') == 'confirmed' or assembly_type == 'CUSTOM_ASSEMBLY')
                    and c.get('name')]
        authoritative = existing_assembly.get('configuration_authoritative') is True
        chosen_configuration = authoritative or assembly_type == 'CUSTOM_ASSEMBLY' or any(isinstance(c, dict) and 'use_in_quotation' in c for c in explicit)
        if chosen_configuration and len(explicit) >= 1:
            resolved = [{**c, 'included_in_total': True, 'use_in_quotation': True,
                         'brand': c.get('brand') or brand,
                         'quantity': c.get('quantity') or 1,
                         'unit': c.get('unit') or 'Cái'} for c in explicit]
        else:
            resolved = [{**c, 'basis': 'assembly_function', 'status': 'confirmed',
                         'included_in_total': True,
                         'use_in_quotation': True,
                         'brand': c.get('brand') or brand,
                         'spec': c.get('spec') or '', 'part_number': c.get('part_number') or ''} for c in components]
        # Đồng bộ hãng bắt buộc cho cặp Contactor & Rơ le nhiệt, và đồng bộ hãng theo từng nhóm thiết bị (đèn, nút nhấn, chuyển mạch...) trong cùng file
        km_brand = next((c.get('brand') for c in resolved if str(c.get('category') or '').upper() == 'CONTACTOR' and c.get('brand')), None)
        for c in resolved:
            c_cat = str(c.get('category') or '').upper()
            c_grp = _norm_cat_group(c_cat)
            if km_brand and c_cat in {'OVERLOAD_PROTECTION', 'THERMAL_RELAY'}:
                c['brand'] = km_brand
                c['requires_same_brand'] = True
            elif c_grp in {'INDICATOR', 'PUSH_BUTTON', 'SELECTOR', 'RELAY', 'TIMER'} and cat_brands.get(c_grp):
                c['brand'] = cat_brands[c_grp]
                c['requires_same_brand'] = True
        is_spare = _is_spare_device(device, upstream)
        if is_spare:
            cur_name = str(device.get('name') or '').strip()
            if cur_name and 'dự phòng' not in cur_name.lower():
                device['name'] = f"{cur_name} (Dự phòng)"
            cur_fn = str(device.get('electrical_function') or '').strip()
            if cur_fn and 'dự phòng' not in cur_fn.lower():
                device['electrical_function'] = f"{cur_fn} (Dự phòng)"
            elif not cur_fn:
                device['electrical_function'] = 'Dự phòng'
        for index, component in enumerate(resolved):
            component.setdefault('component_key', f'{component.get("category")}:{component.get("name")}:{index}')

        selection_context = {key: circuit[key] for key in
            ('motor_rated_current_a', 'motor_voltage_v', 'control_voltage_v', 'phase')
            if circuit.get(key) not in (None, '')}
        if power_input:
            selection_context['power_input'] = power_input
        upstream_in_a = upstream.get('in_a') if isinstance(upstream, dict) else None
        upstream_spec = (upstream.get('spec') or upstream.get('name') or f"{upstream_in_a}A") if isinstance(upstream, dict) else None
        for component in resolved:
            component['selection_context'] = selection_context
            cat = str(component.get('category') or '').upper()
            requirements = []
            if cat in {'CONTACTOR', 'OVERLOAD_PROTECTION', 'THERMAL_RELAY', 'SOFT_STARTER', 'VFD'}:
                if power_input:
                    unit_str = str(power_input.get('unit') or '').strip()
                    if unit_str.lower() == 'kw':
                        requirements.append(f"Phụ tải DOL: {power_input['value']:g} kW")
                    else:
                        requirements.append(f"Phụ tải DOL: {power_input['value']:g} {unit_str} ({power_w / 1000:.2f} kW)")
                current = circuit.get('motor_rated_current_a')
                in_a = component.get('in_a')
                if current and cat == 'CONTACTOR':
                    req_a = round(float(current) * 1.25, 1)
                    if in_a:
                        requirements.append(f"Chọn {in_a}A AC-3: Iđm động cơ {current} A × 1.25 = {req_a:g} A → lấy cấp chuẩn gần nhất {in_a}A (tránh dư cấp).")
                    else:
                        requirements.append(f"Chọn dòng AC-3 không nhỏ hơn dòng động cơ {current} A tại điện áp làm việc")
                    if upstream_in_a:
                        requirements.append(f"Phối hợp Aptomat nguồn ({upstream_spec}): MCB {upstream_in_a}A gánh dòng khởi động 5–7×Iđm; contactor chọn theo tải {current} A (có thể nâng 12A–18A nếu cần phối hợp Type 2).")
                elif current and cat in {'OVERLOAD_PROTECTION', 'THERMAL_RELAY'}:
                    requirements.append(f"Rơ le nhiệt chỉnh định quanh dòng động cơ {current} A; lắp trực tiếp dưới contactor.")
                if circuit.get('motor_voltage_v') or circuit.get('control_voltage_v'):
                    mv = circuit.get('motor_voltage_v') or 380
                    cv = circuit.get('control_voltage_v') or 220
                    requirements.append(f"Điện áp động lực {mv}V · Cuộn hút điều khiển {cv}V")
            component['selection_requirements'] = requirements

        assembly = {
            'configuration_authoritative': authoritative,
            'type': assembly_type, 'basis': 'assembly_function', 'status': 'needs_engineering_selection',
            'is_spare': is_spare,
            'load': device.get('connected_load') or circuit.get('supply_location'),
            'load_power_w': power_w, 'power_input': power_input, 'upstream_reference': reference or None,
            'upstream_status': ('verified' if relationship_verified else 'candidate') if upstream else 'needs_review',
            'upstream': {k: upstream.get(k) for k in ('tag', 'name', 'spec', 'in_a', 'poles', 'icu_ka')} if upstream else None,
            'missing_inputs': missing,
            'selection_note': 'Aptomat đầu nguồn là ràng buộc phối hợp bảo vệ; dòng aptomat không phải dòng định mức động cơ.',
            'pricing_basis': 'selected_components' if any(c.get('use_in_quotation') is True for c in resolved) else 'assembly_only',
            'components': resolved,
            'accessory_proposals': [],
            'recommendation_sources': SOURCES,
        }
        device['source_observations'] = {**observations, 'motor_starter': assembly}
    return devices
