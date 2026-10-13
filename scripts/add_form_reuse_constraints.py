import json
from extract_project_helpers import OUT,save
d=json.loads((OUT/'catalog.json').read_text(encoding='utf-8'))
checks=['working_view_and_coordinate_system','usable_mounting_area','device_dimensions_and_rotation','mounting_holes_and_supports','terminal_orientation','busbar_route_and_supports','cable_route_and_bend_space','door_swing_and_depth','maintenance_and_thermal_clearance','required_internal_separation']
for row in d['shells']:
 p=OUT/row['layout_analysis_json'];a=json.loads(p.read_text(encoding='utf-8'))
 a['reuse_compatibility']={
  'baseline_id':row['id'],'baseline_name':row['name'],'baseline_material':row.get('material_from_source'),'nominal_dimensions_mm':row.get('dimensions_mm'),
  'coordinate_scope':'source_sheet_multiple_views_not_single_cabinet_face',
  'baseline_reusable_without_changes':None,'auto_accept':False,
  'working_view_id':None,'usable_mounting_bounds_mm':None,
  'required_checks':{c:{'status':'not_verified','evidence':None} for c in checks},
  'matching_rules':['Tách và xác nhận đúng mặt trước khi dùng tọa độ; không so các mặt khác nhau chung một mặt phẳng.','Ghép cùng thiết bị giữa các mặt theo mã/thuộc tính và bằng chứng; không ghép chỉ vì tên gần giống.','Đổi dòng/model phải kiểm tra lại kích thước, đầu nối, khoan/gá, đồng và nhiệt; cùng hãng không có nghĩa lắp thay được.','Dùng bố trí cũ làm mốc tham khảo; chỉ giữ vị trí khi CAD mới và khoảng hở phù hợp.','Không giữ đường đồng cũ nếu vị trí, số cực hoặc cọc đấu mới thay đổi.','Tên tủ/loại tôn/kích thước cùng nhau vẫn chưa chứng minh bố trí mới phù hợp.'],
  'decision_states':{'compatible':'Đủ bằng chứng cho tất cả kiểm tra bắt buộc.','requires_relayout':'Có xung đột đã xác định, cần bố trí lại.','needs_review':'Thiếu mặt/kích thước/đường đi/khoảng hở hoặc bằng chứng phân khoang.'},
  'current_decision':'needs_review',
  'proposal_contract':{'cabinet_id':row['id'],'working_view_id':'required','coordinate_system':'local_mm_of_verified_working_view','devices':[{'instance_id':'required','baseline_source_handles':[],'catalog_device_id':'required','cad_view_id':'required','position_mm':None,'rotation_deg':None,'occupied_bounds_mm':None,'mounting_holes_mm':None,'terminal_positions_mm':None,'required_clearances_mm':None}],'busbar_routes':[],'wire_routes':[],'required_form':None,'material_and_thickness':None},
  'comparison_output_contract':{'decision':'compatible|requires_relayout|needs_review','kept_positions':[],'moved_devices':[],'collisions':[],'route_changes':[],'missing_evidence':[],'form_conflicts':[]}}
 save(p,a);row['reuse_decision']='needs_review';save(OUT/'Mau'/row['id']/'thong_tin.json',row)
save(OUT/'catalog.json',d)
p=OUT/'phan_tich_bo_tri_va_form.json';all_data=json.loads(p.read_text(encoding='utf-8'));all_data['items']=[json.loads((OUT/r['layout_analysis_json']).read_text(encoding='utf-8')) for r in d['shells']];save(p,all_data)
print('Reuse contracts added:',len(d['shells']))
