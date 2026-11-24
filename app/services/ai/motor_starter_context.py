"""Per-circuit motor starter guidance (DOL, Star-Delta, Reversing, Soft Starter, VFD); functional proposals never become priced BOM rows."""
import re
import math


def load_power_w(device):
    observations = device.get('source_observations') or {}
    circuit = {**(observations.get('circuit') or {}), **(device.get('circuit_context') or {})}

    def number(value):
        if isinstance(value, bool) or not isinstance(value, (int, float, str)):
            return None
        try:
            result = float(str(value).replace(',', '.'))
            return result if math.isfinite(result) and result >= 0 else None
        except ValueError:
            return None

    for candidate in (device.get('power_w'), circuit.get('power_w')):
        value = number(candidate)
        if value is not None:
            return value
    value = number(device.get('motor_power_kw', circuit.get('motor_power_kw')))
    if value is not None:
        return value * 1000
    value = number(circuit.get('power_value'))
    unit = str(circuit.get('power_unit') or '').strip().lower()
    if value is not None and unit in {'w', 'kw'}:
        return value * (1000 if unit == 'kw' else 1)
    return None


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
        power_w = load_power_w(device)
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
        required = {
            'motor_rated_current_a': 'Dòng định mức động cơ (A)',
            'motor_power_kw': 'Công suất động cơ (kW)',
            'motor_voltage_v': 'Điện áp động cơ (V)',
            'control_voltage_v': 'Điện áp điều khiển/cuộn hút (V)',
        }
        missing = [label for key, label in required.items() if circuit.get(key) in (None, '')]
        if power_w is not None:
            missing = [label for label in missing if label != required['motor_power_kw']]

        if starter_type == 'STAR_DELTA':
            components = [
                {'category': 'CONTACTOR', 'name': 'Contactor chính KM-Main', 'quantity': 1, 'reason': 'Đóng cắt cấp nguồn chính cho động cơ.'},
                {'category': 'CONTACTOR', 'name': 'Contactor tam giác KM-Delta', 'quantity': 1, 'reason': 'Đóng mạch chạy chế độ tam giác.'},
                {'category': 'CONTACTOR', 'name': 'Contactor sao KM-Star', 'quantity': 1, 'reason': 'Đóng điểm sao khởi động ban đầu.'},
                {'category': 'OVERLOAD_PROTECTION', 'name': 'Rơ le nhiệt (TOR) bảo vệ quá tải', 'quantity': 1, 'reason': 'Bảo vệ quá tải nhiệt động cơ.'},
                {'category': 'TIMER', 'name': 'Rơ le thời gian Sao - Tam giác', 'quantity': 1, 'reason': 'Chuyển mạch từ cấp sao sang tam giác sau thời gian cài đặt.'},
                {'category': 'PUSH_BUTTON_ON', 'name': 'Nút nhấn ON', 'quantity': None, 'reason': 'Số lượng theo mạch điều khiển thực tế.'},
                {'category': 'PUSH_BUTTON_OFF', 'name': 'Nút nhấn OFF', 'quantity': None, 'reason': 'Số lượng theo mạch điều khiển thực tế.'},
            ]
        elif starter_type == 'REVERSING':
            components = [
                {'category': 'CONTACTOR', 'name': 'Contactor quay thuận KM-Forward', 'quantity': 1, 'reason': 'Đóng mạch quay chiều thuận.'},
                {'category': 'CONTACTOR', 'name': 'Contactor quay nghịch KM-Reverse', 'quantity': 1, 'reason': 'Đóng mạch quay chiều nghịch (liên động cơ - điện).'},
                {'category': 'OVERLOAD_PROTECTION', 'name': 'Rơ le nhiệt (TOR) bảo vệ quá tải', 'quantity': 1, 'reason': 'Bảo vệ quá tải nhiệt động cơ.'},
                {'category': 'PUSH_BUTTON_FORWARD', 'name': 'Nút nhấn chạy thuận', 'quantity': None, 'reason': 'Theo phương thức điều khiển chiều thuận.'},
                {'category': 'PUSH_BUTTON_REVERSE', 'name': 'Nút nhấn chạy nghịch', 'quantity': None, 'reason': 'Theo phương thức điều khiển chiều nghịch.'},
                {'category': 'PUSH_BUTTON_OFF', 'name': 'Nút nhấn OFF', 'quantity': None, 'reason': 'Theo mạch dừng thực tế.'},
            ]
        elif starter_type == 'SOFT_STARTER':
            components = [
                {'category': 'SOFT_STARTER', 'name': 'Bộ khởi động mềm (Soft Starter)', 'quantity': 1, 'reason': 'Điều khiển khởi động êm giảm dòng mở máy.'},
                {'category': 'PUSH_BUTTON_ON', 'name': 'Nút nhấn RUN', 'quantity': None, 'reason': 'Chọn theo chế độ điều khiển của bộ khởi động mềm.'},
                {'category': 'PUSH_BUTTON_OFF', 'name': 'Nút nhấn STOP', 'quantity': None, 'reason': 'Chọn theo chế độ điều khiển của bộ khởi động mềm.'},
            ]
        elif starter_type == 'VFD':
            components = [
                {'category': 'VFD', 'name': 'Biến tần (Inverter/VFD)', 'quantity': 1, 'reason': 'Điều khiển tốc độ vô cấp và khởi động động cơ.'},
                {'category': 'CONTACTOR', 'name': 'Contactor cấp nguồn đầu vào', 'quantity': 1, 'reason': 'Đóng cắt cấp nguồn cho biến tần.'},
                {'category': 'PUSH_BUTTON_ON', 'name': 'Nút nhấn RUN', 'quantity': None, 'reason': 'Nếu mạch dùng nút rời thay vì bàn phím hoặc điều khiển ngoài.'},
                {'category': 'PUSH_BUTTON_OFF', 'name': 'Nút nhấn STOP', 'quantity': None, 'reason': 'Nếu mạch dùng nút rời; theo cấu hình ngõ vào điều khiển.'},
            ]
        else: # DOL
            components = [
                {'category': 'CONTACTOR', 'name': 'Contactor động lực', 'quantity': 1,
                 'reason': 'Chọn theo dòng/công suất động cơ, điện áp, chế độ sử dụng và phối hợp bảo vệ.'},
                {'category': 'OVERLOAD_PROTECTION', 'name': 'Rơ le nhiệt / bảo vệ quá tải động cơ', 'quantity': 1,
                 'reason': 'Xác định rơ le quá tải hoặc chức năng bảo vệ đã tích hợp; không lấy dòng aptomat làm dải chỉnh định.'},
                {'category': 'PUSH_BUTTON_ON', 'name': 'Nút nhấn ON', 'quantity': None,
                 'reason': 'Số lượng theo đầu vào và phương thức điều khiển của từng bộ.'},
                {'category': 'PUSH_BUTTON_OFF', 'name': 'Nút nhấn OFF', 'quantity': None,
                 'reason': 'Số lượng theo đầu vào và phương thức điều khiển của từng bộ.'},
                {'category': 'SELECTOR_SWITCH_3_POSITION', 'name': 'Công tắc chuyển mạch 3 vị trí', 'quantity': None,
                 'reason': 'Xác định số lượng và chế độ chuyển mạch theo yêu cầu đầu vào.'},
            ]

        # Keep explicit per-assembly inputs when enrichment runs again. These
        # describe the assembly; they are not additional priced BOM lines.
        existing = (observations.get('motor_starter') or {}).get('components') or []
        explicit = [c for c in existing if isinstance(c, dict) and
                    (c.get('basis') in {'source', 'user_request'} or c.get('status') == 'confirmed')]
        # An explicit configuration is authoritative. Do not fill it with a
        # fixed checklist (e.g. add ON/OFF operators to a remote-controlled set).
        authoritative = (observations.get('motor_starter') or {}).get('configuration_authoritative') is True
        chosen_configuration = authoritative or any(isinstance(c, dict) and 'use_in_quotation' in c for c in existing)
        if chosen_configuration:
            explicit = [c for c in existing if isinstance(c, dict)]
        resolved = ([{**c, 'included_in_total': True} for c in explicit] if explicit or authoritative else
                    [{**c, 'basis': 'assembly_function', 'status': 'proposal',
                      'included_in_total': False, 'spec': None, 'part_number': None} for c in components])
        for index, component in enumerate(resolved):
            component.setdefault('component_key', f'{component.get("category")}:{component.get("name")}:{index}')

        assembly = {
            'configuration_authoritative': authoritative,
            'type': starter_type, 'basis': 'assembly_function', 'status': 'needs_engineering_selection',
            'load': device.get('connected_load') or circuit.get('supply_location'),
            'load_power_w': power_w, 'upstream_reference': reference or None,
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
