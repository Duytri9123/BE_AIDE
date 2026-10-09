"""Compare proposed ratings to circuit conditions, not to drawing equality."""
import math


def assess(candidate, circuit):
    fields=('load_current_a','cable_derated_ampacity_a','prospective_short_circuit_ka','voltage_v')
    missing=[key for key in fields if not isinstance(circuit.get(key),(int,float)) or isinstance(circuit.get(key),bool) or not math.isfinite(circuit[key]) or circuit[key]<=0]
    required=('rated_current_a','breaking_capacity_ka','voltage_v')
    missing += [key for key in required if not isinstance(candidate.get(key),(int,float)) or isinstance(candidate.get(key),bool) or not math.isfinite(candidate[key]) or candidate[key]<=0]
    if not candidate.get('manufacturer_source'):
        missing.append('manufacturer_source')
    problems=[]
    if not missing:
        if not circuit['load_current_a'] <= candidate['rated_current_a'] <= circuit['cable_derated_ampacity_a']:
            problems.append('Không thỏa Ib ≤ In ≤ Iz sau hiệu chỉnh điều kiện lắp đặt.')
        if candidate['voltage_v'] != circuit['voltage_v']:
            problems.append('Khả năng cắt chưa được xác nhận ở điện áp hệ thống.')
        elif candidate['breaking_capacity_ka'] < circuit['prospective_short_circuit_ka']:
            problems.append('Khả năng cắt thấp hơn dòng ngắn mạch dự kiến.')
    if circuit.get('poles') and candidate.get('poles') != circuit['poles']:
        problems.append('Số cực chưa phù hợp phương án mạch.')
    return dict(candidate=candidate,status='not_suitable' if problems else 'needs_data' if missing else 'eligible_for_coordination_review',
                issues=problems,missing_inputs=missing,release_ready=False,
                remaining_reviews=['trip_curve_and_starting_current','selectivity_and_backup','thermal_derating','cable_fault_withstand'])


def review(devices):
    result=[]
    for device in devices:
        if device.get('category') not in ('MCCB','ACB','MCB','RCBO','RCCB'):
            continue
        proposal=device.get('compatible_proposal') or {}
        options=proposal.get('electrical_candidates') or []
        circuit=dict(device.get('electrical_design_inputs') or proposal.get('circuit_inputs') or {})
        circuit.setdefault('poles',device.get('poles'))
        assessments=[assess(option,circuit) for option in options]
        eligible=[a for a in assessments if a['status']=='eligible_for_coordination_review']
        result.append(dict(tag=device.get('tag'),original_spec=device.get('original_spec') or device.get('spec'),
            drawing_current_a=device.get('in_a'),options=assessments,
            preferred_candidate=min(eligible,key=lambda a:a['candidate']['rated_current_a'])['candidate'] if eligible else None,
            status='eligible_for_coordination_review' if eligible else 'needs_data',
            missing_inputs=[] if options else ['load_current_a','cable_derated_ampacity_a','prospective_short_circuit_ka','voltage_v','exact_model_candidates'],
            basis='Chọn phương án theo tải, cáp và bảo vệ; không bắt buộc dòng đề xuất bằng dòng bản vẽ.',release_ready=False))
    return result
