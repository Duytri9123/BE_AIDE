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
            for field in ('power', 'motor_power', 'power_w', 'p_w', 'connected_load'):
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
        return None
    if any(abs(p['watts'] - found[0]['watts']) > max(1, found[0]['watts'] * .02) for p in found):
        return None
    return found[0]


def load_power_w(device):
    power = load_power_details(device)
    return power['watts'] if power else None


def starter_quotation_name(device):
    observations = device.get('source_observations') or {}
    assembly = observations.get('motor_starter') or {}
    kind = assembly.get('type') or classify_motor_starter_type(' '.join(str(device.get(k) or '') for k in ('name', 'category', 'spec')))
    if not kind:
        return device.get('name') or 'Thiết bị'
    name = {'DOL': 'Khởi động DOL', 'STAR_DELTA': 'Khởi động sao – tam giác',
            'REVERSING': 'Khởi động đảo chiều', 'SOFT_STARTER': 'Khởi động mềm', 'VFD': 'Biến tần'}.get(kind, device.get('name') or kind)
    power = load_power_details(device)
    if power:
        unit, value = power['unit'], power['value']
        if unit == 'W' and value >= 1000:
            value, unit = value / 1000, 'kW'
        name += f" {value:g}{unit}"
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


def enrich_motor_starters(devices):
    from app.services.ai.assembly_accessories import propose_assembly_accessories, SOURCES
    from app.services.ai.assembly_accessory_selection import merge_proposal_choices
    for device in devices:
        identity = ' '.join(str(device.get(k) or '') for k in ('category', 'name', 'spec', 'electrical_function', 'observed_text'))
        starter_type = classify_motor_starter_type(identity)
        is_ats = bool(re.search(r'\bATS\b|bộ chuyển nguồn', identity, re.I))
        if not starter_type and not is_ats:
            continue
        observations = device.get('source_observations')
        observations = dict(observations) if isinstance(observations, dict) else {}
        circuit = {**(observations.get('circuit') or {}), **(device.get('circuit_context') or {})}
        power_input = load_power_details(device)
        power_w = power_input['watts'] if power_input else None
        if is_ats and not starter_type:
            current = observations.get('assembly') or {}
            components = current.get('components') or []
            device['source_observations'] = {**observations, 'assembly': {
                **current, 'type': 'ATS', 'components': components,
                'load': device.get('connected_load'), 'load_power_w': power_w,
                'accessory_proposals': merge_proposal_choices(
                    propose_assembly_accessories('ATS', circuit, components, power_w, device.get('connected_load')),
                    current.get('accessory_proposals')),
                'recommendation_sources': SOURCES,
            }}
            continue
        reference = str(device.get('upstream_device') or '').strip()
        canonical = lambda value: re.sub(r'[^\w]', '', str(value or '')).casefold()
        matches = [d for d in devices if d is not device and reference and
                   str(d.get('category') or '').upper() in {'MCB', 'MCCB', 'MPCB', 'RCBO', 'RCCB', 'ACB'} and
                   canonical(reference) in {canonical(d.get('tag')), canonical(d.get('spec')),
                       canonical(str(d.get('category') or '')+' '+str(d.get('spec') or ''))} and
                   all(d.get(k) == device.get(k) for k in ('source_file_id', 'panel_code', 'source_page'))]
        upstream = matches[0] if len(matches) == 1 else None
        if not reference and device.get('connected_load'):
            matches = [d for d in devices if d is not device and
                       str(d.get('category') or '').upper() in {'MCB', 'MCCB', 'MPCB', 'RCBO', 'RCCB', 'ACB'} and
                       canonical(d.get('connected_load')) == canonical(device['connected_load']) and
                       all(d.get(k) == device.get(k) for k in ('source_file_id', 'panel_code', 'source_page'))]
            upstream = matches[0] if len(matches) == 1 else None
        relationship_verified = bool(upstream and (device.get('evidence_region') or {}).get('load_verified') is True
                                     and (upstream.get('evidence_region') or {}).get('load_verified') is True)

        # Nhận diện quy cách cáp để xác định pha và điện áp
        cable_spec = str(circuit.get('cable_spec') or circuit.get('cable') or device.get('cable_spec') or '')
        if re.search(r'\b(?:3|4)\s*[xX]\s*(\d+(?:[.,]\d+)?)', cable_spec):
            circuit.setdefault('phase', '3P')
            circuit.setdefault('motor_voltage_v', 380)
            circuit.setdefault('control_voltage_v', 220)
        elif re.search(r'\b(?:1|2)\s*[xX]\s*(\d+(?:[.,]\d+)?)', cable_spec):
            circuit.setdefault('phase', '1P')
            circuit.setdefault('motor_voltage_v', 220)
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

        if starter_type == 'STAR_DELTA':
            km_main_spec, km_main_a = select_contactor_spec(motor_current * 0.58 if motor_current else None, motor_voltage, power_w)
            tor_spec, _ = select_tor_spec(motor_current * 0.58 if motor_current else None, power_w, motor_voltage)
            components = [
                {'category': 'CONTACTOR', 'name': 'Contactor chính KM-Main', 'spec': km_main_spec, 'quantity': 1, 'in_a': km_main_a, 'reason': 'Đóng cắt cấp nguồn chính cho động cơ.'},
                {'category': 'CONTACTOR', 'name': 'Contactor tam giác KM-Delta', 'spec': km_main_spec, 'quantity': 1, 'in_a': km_main_a, 'reason': 'Đóng mạch chạy chế độ tam giác.'},
                {'category': 'CONTACTOR', 'name': 'Contactor sao KM-Star', 'spec': select_contactor_spec(motor_current * 0.33 if motor_current else None, motor_voltage, power_w)[0], 'quantity': 1, 'reason': 'Đóng điểm sao khởi động ban đầu.'},
                {'category': 'OVERLOAD_PROTECTION', 'name': 'Rơ le nhiệt (TOR) bảo vệ quá tải', 'spec': tor_spec, 'quantity': 1, 'reason': 'Bảo vệ quá tải nhiệt động cơ.'},
                {'category': 'TIMER', 'name': 'Rơ le thời gian Sao - Tam giác', 'spec': '220VAC 0-30s', 'quantity': 1, 'reason': 'Chuyển mạch từ cấp sao sang tam giác.'},
            ]
        elif starter_type == 'REVERSING':
            km_spec, km_a = select_contactor_spec(motor_current, motor_voltage, power_w)
            tor_spec, _ = select_tor_spec(motor_current, power_w, motor_voltage)
            components = [
                {'category': 'CONTACTOR', 'name': 'Contactor quay thuận KM-Forward', 'spec': km_spec, 'quantity': 1, 'in_a': km_a, 'reason': 'Đóng mạch quay chiều thuận.'},
                {'category': 'CONTACTOR', 'name': 'Contactor quay nghịch KM-Reverse', 'spec': km_spec, 'quantity': 1, 'in_a': km_a, 'reason': 'Đóng mạch quay chiều nghịch.'},
                {'category': 'OVERLOAD_PROTECTION', 'name': 'Rơ le nhiệt (TOR) bảo vệ quá tải', 'spec': tor_spec, 'quantity': 1, 'reason': 'Bảo vệ quá tải nhiệt động cơ.'},
            ]
        elif starter_type == 'SOFT_STARTER':
            components = [
                {'category': 'SOFT_STARTER', 'name': 'Bộ khởi động mềm (Soft Starter)', 'spec': f"{power_input['value']:g}{power_input['unit']} {motor_voltage}V" if power_input else None, 'quantity': 1, 'reason': 'Điều khiển khởi động êm giảm dòng mở máy.'},
            ]
        elif starter_type == 'VFD':
            components = [
                {'category': 'VFD', 'name': 'Biến tần (Inverter/VFD)', 'spec': f"{power_input['value']:g}{power_input['unit']} {motor_voltage}V" if power_input else None, 'quantity': 1, 'reason': 'Điều khiển tốc độ vô cấp và khởi động động cơ.'},
            ]
        else: # DOL
            contactor_spec, contactor_a = select_contactor_spec(motor_current, motor_voltage, power_w)
            tor_spec, _ = select_tor_spec(motor_current, power_w, motor_voltage)
            power_desc = f"{power_input['value']:g} {power_input['unit']}" if power_input else ""
            components = [
                {'category': 'CONTACTOR', 'name': 'Contactor động lực', 'spec': contactor_spec, 'quantity': 1,
                 'in_a': contactor_a, 'poles': 3 if motor_voltage >= 380 else 1,
                 'reason': f'Contactor {contactor_spec} cho tải {power_desc} (Iđm ~{motor_current}A)' if motor_current else 'Contactor động lực mạch khởi động trực tiếp.'},
                {'category': 'OVERLOAD_PROTECTION', 'name': 'Rơ le nhiệt / bảo vệ quá tải động cơ', 'spec': tor_spec, 'quantity': 1,
                 'reason': f'Rơ le nhiệt {tor_spec} bảo vệ quá tải (chỉnh định tại ~{motor_current}A)' if motor_current else 'Rơ le nhiệt bảo vệ quá tải động cơ.'},
            ]

        # Keep explicit per-assembly inputs when enrichment runs again.
        existing = (observations.get('motor_starter') or {}).get('components') or []
        # Nếu các thành phần cũ là placeholder rỗng (không có spec hoặc thiếu số lượng), loại bỏ để tính lại từ đầu
        if any(c.get('spec') is None or c.get('quantity') is None for c in existing if isinstance(c, dict)):
            existing = []
        explicit = [c for c in existing if isinstance(c, dict) and
                    (c.get('basis') in {'source', 'user_request'} or c.get('status') == 'confirmed')]
        authoritative = (observations.get('motor_starter') or {}).get('configuration_authoritative') is True
        chosen_configuration = authoritative or any(isinstance(c, dict) and 'use_in_quotation' in c for c in existing)
        if chosen_configuration:
            explicit = [c for c in existing if isinstance(c, dict)]
        resolved = ([{**c, 'included_in_total': True} for c in explicit] if explicit or authoritative else
                    [{**c, 'basis': 'assembly_function', 'status': 'proposal',
                      'included_in_total': False, 'spec': c.get('spec'), 'part_number': c.get('part_number')} for c in components])
        for index, component in enumerate(resolved):
            component.setdefault('component_key', f'{component.get("category")}:{component.get("name")}:{index}')

        selection_context = {key: circuit[key] for key in
            ('motor_rated_current_a', 'motor_voltage_v', 'control_voltage_v', 'phase')
            if circuit.get(key) not in (None, '')}
        if power_input:
            selection_context['power_input'] = power_input
        for component in resolved:
            component['selection_context'] = selection_context
            requirements = []
            if power_input:
                requirements.append(f"Phụ tải {power_input['value']:g} {power_input['unit']} = {power_w / 1000:.3f} kW")
            current = circuit.get('motor_rated_current_a')
            if current and component.get('category') == 'CONTACTOR':
                requirements.append(f"Chọn dòng AC-3 không nhỏ hơn dòng động cơ {current} A tại điện áp làm việc")
            elif current and component.get('category') == 'OVERLOAD_PROTECTION':
                requirements.append(f"Dải chỉnh định phải bao phủ dòng động cơ {current} A; đối chiếu vị trí lắp rơ le")
            for key, label in (('motor_voltage_v', 'Điện áp động cơ'), ('control_voltage_v', 'Điện áp điều khiển')):
                if circuit.get(key):
                    requirements.append(f"{label}: {circuit[key]} V")
            component['selection_requirements'] = requirements

        assembly = {
            'configuration_authoritative': authoritative,
            'type': starter_type, 'basis': 'assembly_function', 'status': 'needs_engineering_selection',
            'load': device.get('connected_load') or circuit.get('supply_location'),
            'load_power_w': power_w, 'power_input': power_input, 'upstream_reference': reference or None,
            'upstream_status': ('verified' if relationship_verified else 'candidate') if upstream else 'needs_review',
            'upstream': {k: upstream.get(k) for k in ('tag', 'name', 'spec', 'in_a', 'poles', 'icu_ka')} if upstream else None,
            'missing_inputs': missing,
            'selection_note': 'Aptomat đầu nguồn là ràng buộc phối hợp bảo vệ; dòng aptomat không phải dòng định mức động cơ.',
            'pricing_basis': 'selected_components' if any(c.get('use_in_quotation') is True for c in resolved) else 'assembly_only',
            'components': resolved,
            'accessory_proposals': merge_proposal_choices(
                propose_assembly_accessories(starter_type, circuit, resolved + [a for a in device.get('accompanying_accessories') or []
                    if isinstance(a, dict) and not a.get('assembly_proposal_key')], power_w, device.get('connected_load')),
                (observations.get('motor_starter') or {}).get('accessory_proposals')),
            'recommendation_sources': SOURCES,
        }
        device['source_observations'] = {**observations, 'motor_starter': assembly}
    return devices
