"""Per-circuit DOL guidance; functional proposals never become priced BOM rows."""
import re


def enrich_motor_starters(devices):
    for device in devices:
        identity = ' '.join(str(device.get(k) or '') for k in ('category', 'name', 'spec', 'electrical_function'))
        if not re.search(r'\bD\.?O\.?L\.?\b|khởi động trực tiếp|direct.on.line', identity, re.I):
            continue
        observations = device.get('source_observations')
        observations = dict(observations) if isinstance(observations, dict) else {}
        circuit = observations.get('circuit')
        circuit = circuit if isinstance(circuit, dict) else {}
        reference = str(device.get('upstream_device') or '').strip()
        # Match a unique explicit reference; a shared load is only a candidate
        # until both source wire relationships have passed the pixel audit.
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
        components = [
            {'category': 'CONTACTOR', 'name': 'Contactor động lực', 'quantity': 1,
             'reason': 'Chọn theo dòng/công suất động cơ, điện áp, chế độ sử dụng và phối hợp bảo vệ.'},
            {'category': 'OVERLOAD_PROTECTION', 'name': 'Bảo vệ quá tải động cơ', 'quantity': 1,
             'reason': 'Xác định rơ le quá tải hoặc chức năng bảo vệ đã tích hợp; không lấy dòng aptomat làm dải chỉnh định.'},
            {'category': 'CONTROL_OPERATORS', 'name': 'Điều khiển Start/Stop hoặc tín hiệu ngoài', 'quantity': None,
             'reason': 'Chốt phương thức điều khiển và số lượng theo mạch thực tế; không mặc định mọi bộ đều có nút nhấn rời.'},
        ]
        assembly = {
            'type': 'DOL', 'basis': 'assembly_function', 'status': 'needs_engineering_selection',
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
