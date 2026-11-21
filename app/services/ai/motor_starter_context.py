"""Per-circuit motor starter guidance (DOL, Star-Delta, Reversing, Soft Starter, VFD); functional proposals never become priced BOM rows."""
import re


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
    for device in devices:
        identity = ' '.join(str(device.get(k) or '') for k in ('category', 'name', 'spec', 'electrical_function', 'observed_text'))
        starter_type = classify_motor_starter_type(identity)
        if not starter_type:
            continue
        observations = device.get('source_observations')
        observations = dict(observations) if isinstance(observations, dict) else {}
        circuit = observations.get('circuit')
        circuit = circuit if isinstance(circuit, dict) else {}
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

        if starter_type == 'STAR_DELTA':
            components = [
                {'category': 'CONTACTOR', 'name': 'Contactor chính KM-Main', 'quantity': 1, 'reason': 'Đóng cắt cấp nguồn chính cho động cơ.'},
                {'category': 'CONTACTOR', 'name': 'Contactor tam giác KM-Delta', 'quantity': 1, 'reason': 'Đóng mạch chạy chế độ tam giác.'},
                {'category': 'CONTACTOR', 'name': 'Contactor sao KM-Star', 'quantity': 1, 'reason': 'Đóng điểm sao khởi động ban đầu.'},
                {'category': 'OVERLOAD_PROTECTION', 'name': 'Rơ le nhiệt (TOR) bảo vệ quá tải', 'quantity': 1, 'reason': 'Bảo vệ quá tải nhiệt động cơ.'},
                {'category': 'TIMER', 'name': 'Rơ le thời gian Sao - Tam giác', 'quantity': 1, 'reason': 'Chuyển mạch từ cấp sao sang tam giác sau thời gian cài đặt.'},
                {'category': 'CONTROL_OPERATORS', 'name': 'Nút nhấn Start/Stop và đèn báo', 'quantity': None, 'reason': 'Điều khiển mặt tủ theo sơ đồ.'},
            ]
        elif starter_type == 'REVERSING':
            components = [
                {'category': 'CONTACTOR', 'name': 'Contactor quay thuận KM-Forward', 'quantity': 1, 'reason': 'Đóng mạch quay chiều thuận.'},
                {'category': 'CONTACTOR', 'name': 'Contactor quay nghịch KM-Reverse', 'quantity': 1, 'reason': 'Đóng mạch quay chiều nghịch (liên động cơ - điện).'},
                {'category': 'OVERLOAD_PROTECTION', 'name': 'Rơ le nhiệt (TOR) bảo vệ quá tải', 'quantity': 1, 'reason': 'Bảo vệ quá tải nhiệt động cơ.'},
                {'category': 'CONTROL_OPERATORS', 'name': 'Cụm nút nhấn Thuận - Nghịch - Dừng', 'quantity': None, 'reason': 'Điều khiển chiều quay và dừng.'},
            ]
        elif starter_type == 'SOFT_STARTER':
            components = [
                {'category': 'SOFT_STARTER', 'name': 'Bộ khởi động mềm (Soft Starter)', 'quantity': 1, 'reason': 'Điều khiển khởi động êm giảm dòng mở máy.'},
                {'category': 'CONTACTOR', 'name': 'Contactor Bypass (nếu có)', 'quantity': None, 'reason': 'Bypass bộ khởi động mềm khi đã đạt tốc độ định mức.'},
                {'category': 'CONTROL_OPERATORS', 'name': 'Nút nhấn Run/Stop và đèn báo trạng thái', 'quantity': None, 'reason': 'Điều khiển mặt tủ.'},
            ]
        elif starter_type == 'VFD':
            components = [
                {'category': 'VFD', 'name': 'Biến tần (Inverter/VFD)', 'quantity': 1, 'reason': 'Điều khiển tốc độ vô cấp và khởi động động cơ.'},
                {'category': 'CONTACTOR', 'name': 'Contactor cấp nguồn đầu vào', 'quantity': 1, 'reason': 'Đóng cắt cấp nguồn cho biến tần.'},
                {'category': 'REACTOR', 'name': 'Cuộn kháng Line Choke / Bộ lọc (nếu có)', 'quantity': None, 'reason': 'Lọc sóng hài và bảo vệ biến tần.'},
                {'category': 'CONTROL_OPERATORS', 'name': 'Biến trở chiết áp / Đèn báo / Nút nhấn', 'quantity': None, 'reason': 'Điều khiển tốc độ và trạng thái biến tần.'},
            ]
        else: # DOL
            components = [
                {'category': 'CONTACTOR', 'name': 'Contactor động lực', 'quantity': 1,
                 'reason': 'Chọn theo dòng/công suất động cơ, điện áp, chế độ sử dụng và phối hợp bảo vệ.'},
                {'category': 'OVERLOAD_PROTECTION', 'name': 'Bảo vệ quá tải động cơ', 'quantity': 1,
                 'reason': 'Xác định rơ le quá tải hoặc chức năng bảo vệ đã tích hợp; không lấy dòng aptomat làm dải chỉnh định.'},
                {'category': 'CONTROL_OPERATORS', 'name': 'Điều khiển Start/Stop hoặc tín hiệu ngoài', 'quantity': None,
                 'reason': 'Chốt phương thức điều khiển và số lượng theo mạch thực tế; không mặc định mọi bộ đều có nút nhấn rời.'},
            ]

        assembly = {
            'type': starter_type, 'basis': 'assembly_function', 'status': 'needs_engineering_selection',
            'load': device.get('connected_load'), 'upstream_reference': reference or None,
            'upstream_status': ('verified' if relationship_verified else 'candidate') if upstream else 'needs_review',
            'upstream': {k: upstream.get(k) for k in ('tag', 'name', 'spec', 'in_a', 'poles', 'icu_ka')} if upstream else None,
            'missing_inputs': missing,
            'selection_note': 'Aptomat đầu nguồn là ràng buộc phối hợp bảo vệ; dòng aptomat không phải dòng định mức động cơ.',
            'pricing_basis': 'assembly_only',
            'components': [{**c, 'basis': 'assembly_function', 'status': 'proposal', 'included_in_total': False,
                            'spec': None, 'part_number': None} for c in components],
        }
        device['source_observations'] = {**observations, 'motor_starter': assembly}
    return devices
