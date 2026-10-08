"""Compare power connection systems without inventing terminal geometry."""
import json
from pathlib import Path

PATH=Path(__file__).resolve().parents[3]/'data'/'CatalogTB'/'power_distribution_systems.json'
LABELS={
    'terminal_phase_map':'Sơ đồ pha tại từng cọc',
    'terminal_wire_lug_compatibility':'Cọc tương thích dây và đầu cốt',
    'corrected_ampacity':'Khả năng tải sau hiệu chỉnh',
    'short_circuit_verification':'Kiểm tra ngắn mạch',
    'route_bend_radius':'Tuyến dây và bán kính uốn',
    'distribution_block_rating':'Thông số bộ chia nguồn',
    'copper_terminal_interface':'Đầu nối thanh đồng với cọc',
    'busbar_temperature_verification':'Kiểm tra nhiệt thanh đồng',
    'busbar_short_circuit_support':'Chịu ngắn mạch và gối đỡ',
    'clearance_and_cover':'Khoảng cách điện và che chắn',
    'branch_wire_verification':'Kiểm tra dây nhánh',
    'manufacturer_comb_compatibility':'Mã thanh lược tương thích theo hãng',
    'pole_pitch_and_pole_configuration':'Bước cực và cấu hình cực',
    'feed_position_and_current_rating':'Điểm cấp nguồn và dòng thanh lược',
    'end_caps_and_clearance':'Nắp đầu và khoảng cách điện',
    'terminal_allows_fabricated_copper':'Cọc cho phép nối đồng gia công',
    'verified_terminal_coordinates':'Tọa độ cọc được xác nhận',
    'joint_and_torque':'Mối nối và lực siết',
    'mounting_orientation_allowed':'Tư thế gá được phép'}


def review_distribution(devices, evidence=None, requested_method=None):
    data=json.loads(PATH.read_text(encoding='utf-8'));evidence=evidence or {}
    alternatives=[]
    for method in data['methods']:
        failed=[k for k in method['required_evidence'] if evidence.get(k) is False]
        missing=[k for k in method['required_evidence'] if evidence.get(k) is not True and k not in failed]
        alternatives.append(dict(id=method['id'],name=method['name'],topology=method['topology'],
            status='rejected' if failed else 'needs_information' if missing else 'candidate_requires_review',
            missing_information=[LABELS.get(k,k) for k in missing],
            missing_information_keys=missing,
            rejected_conditions=[LABELS.get(k,k) for k in failed]))
    chosen=next((a for a in alternatives if a['id']==requested_method),None)
    if requested_method and not chosen:raise ValueError('Unknown power distribution system')
    return dict(status=chosen['status'] if chosen else 'needs_distribution_selection',
        requested_method=requested_method,selected_method=None,
        alternatives=alternatives,release_ready=False,
        per_circuit=[dict(tag=d.get('tag'),poles=d.get('poles'),spec=d.get('spec'),
            printed_phase=(str(d.get('tag')).split('/')[-1].upper() if '/' in str(d.get('tag')) else None),
            terminal_phase_map=None) for d in devices if str(d.get('category')).upper() in ('MCB','MCCB')],
        rule='Không suy đã đi xương cá từ CB đặt sát. Giữ R/S/T/N/PE riêng; không tự gán cực thứ hai của CB 2P là N. Chọn hệ cấp nguồn khác với dây ra tải và dây đo lường.')
