"""Assembly data separates observed photo, electrical requirements and CAD placement."""
from pathlib import Path
import json,shutil,hashlib

def build_installation(package,out):
 root=Path(__file__).resolve().parents[2]
 refs=out/'anh_tham_khao';refs.mkdir(exist_ok=True)
 photos=[('ben_trong.jpg','C:/Users/admin/AppData/Local/Temp/codex-clipboard-033a4642-4e7b-47dd-89b2-804f8637aa2a.png'),('canh_ngoai.jpg','C:/Users/admin/AppData/Local/Temp/codex-clipboard-c863bbd3-49a5-49b7-a691-34ed9eef36b9.png')]
 for name,src in photos:
  # Keep original encoding and extension, not a recompressed/synthesized image.
  dst=refs/Path(name).with_suffix('.png')
  if Path(src).is_file():shutil.copy2(src,dst)
 observed={'source':'Ảnh người dùng, không phải ảnh của phương án LS đã chốt',
  'internal':['MCCB phía trên, hệ đồng phân phối ở giữa, hai dãy CB bố trí hai bên','Có một thanh bắt vít đứng bên phải và một thanh nằm ngang phía dưới; chức năng N/PE cần đối chiếu đường dây, không xác nhận chỉ bằng vị trí','Có dây xanh-vàng liên kết cánh với vỏ'],
  'door':['Ba đèn đỏ, vàng, xanh lá','Vôn kế kim có thang đến 500 V, công tắc chọn vôn ở ngay phía dưới'],
  'unknown':['Mã MCCB/CB','Thông số dòng và khả năng cắt','Vật liệu và tiết diện thanh dẫn','Kích thước tủ/thiết bị chính xác','Gối đỡ, khoảng cách giữa các pha và chiều sâu','Hãng/mã đèn, công tắc và sơ đồ cọc']}
 devices=[]
 for v in package['instances']:
  definition=package['definitions'][v['definition']]
  file=out/definition['file']
  devices.append({'id':v['id'],'cad':{'file':definition['file'],'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'view':v['face'],'scale':1,'units':'mm','parametric':definition.get('parametric')},
   'placement':{'area':v['area'],'origin_mm':[v['x_mm'],v['y_mm'],None],'rotation_in_view_deg':v['rotation_deg'],'mounting_surface':'Tấm lắp' if v['area']=='ben_trong' else 'Cánh ngoài',
    'physical_orientation_verified':False,'depth_mm':None,'allowed_physical_orientations_deg':None,'note':'Xoay trong CAD không chứng minh hãng cho phép xoay thiết bị khi lắp.'},
   'terminals':{'manufacturer_pin_map':None,'coordinates_local_xyz_mm':None,'allowed_wire_material':None,'wire_range_mm2':None,'busbar_terminal_adapter':None,'tightening_torque_Nm':None},
   'mounting':{'hole_coordinates_mm':None,'fastener':None,'panel_cutout_mm':None,'minimum_clearances_mm':None,'service_space_mm':None},
   'verification_status':'layout_only','missing':['Sơ đồ/giới hạn cọc đấu','Kích thước gá hoặc khoét theo mã chọn','Chiều sâu và khoảng trống','Tài liệu tư thế lắp nếu xoay thiết bị']})
 connections=[]
 for i,w in enumerate(package['conductors'],1):
  connections.append({'id':f'W{i:03d}','device_group':w['device'],'from':{'equipment_or_net':w['from'],'manufacturer_terminal_id':None},'to':{'equipment_or_net':w['to'],'manufacturer_terminal_id':None},
   'selection':{'type':w['conductor'],'section_description':w['size'],'section_mm2':None,'material_confirmed':False,'status':'proposal','basis':w['status']},
   'route':{'points_xyz_mm':None,'plane_or_depth_mm':None,'length_m':None,'bend_radius_mm':None,'crossing_is_connection':False},'fabrication_ready':False})
 model={'schema_version':'1.0','cabinet':package['cabinet'],'status':'layout_only','fabrication_ready':False,'coordinate_system':{'units':'mm','x':'Sang phải','y':'Lên trên','z':'Từ tấm lắp hướng ra cánh; chưa có tọa độ chiều sâu'},
  'photo_reference':observed,'breaker_arrangement':package.get('layout_order'),'devices':devices,'connections':connections,'label_visibility':{'equipment_tags':False,'tags_retained_in_json':True},
  'layout_options':[{'id':'rows','status':'Phương án cũ, đã thay','description':'MCB chia ba hàng ngang'},
   {'id':'fishbone_two_sides','status':'Bản DXF hiện tại, bố trí sơ bộ chưa xuất bản gia công','description':'MCCB trên, trục R/S/T giữa, MCB hai bên; nhánh đồng cấp vào từng cực đúng pha',
    'required_before_use':['Tư thế lắp ±90° được hãng cho phép theo đúng mã','Số cực, chiều nguồn/tải và cọc đấu xác định','Chọn đầu nối thanh đồng hợp cọc MCB','Mô hình chiều sâu tách các pha, gối đỡ và che chắn','Kiểm tra phát nhiệt và chịu ngắn mạch toàn bộ hệ đồng']}],
  'busbar_system':{'topology':'R/S/T độc lập; nhánh xương cá không nối chéo pha','route_draft':package.get('busbar_route_draft',[]),'phase_assignment_per_branch':'Theo net của tuyến sơ bộ, chưa xác nhận cọc hãng','section_and_material_verified':False,'support_spacing_mm':None,'Icw_kA':None,'Ipk_kA':None,'temperature_rise_verified':False,'phase_clearance_mm':None,'insulating_covers':None},
  'requirements_to_resolve':['PDF dùng R/Y/B; ảnh dùng đỏ/vàng/xanh lá. Màu xanh của đầu đèn không tự xác định pha B hay dây N/PE. Chọn màu hiển thị riêng với net điện; chưa đổi BOM từ ảnh.',
   'Ảnh không chứng minh bộ CB và số lượng trong ảnh đáp ứng 19 nhánh của PDF.',
   'MCCB 200 A/Icu 85 kA không xác nhận hệ thanh đồng và tủ chịu 85 kA.',
   'Một N và một PE giữ CAD gốc, không kéo dài hay thêm lỗ. Biến thể 8/13 vị trí phải có thông số cọc thực; tủ 19 nhánh còn cần xác nhận đủ cọc nguồn/nhánh và liên kết vỏ.',
   'L5/L6 30→32 A, điện áp/logic shunt trip và đầu nối nguồn chưa chốt.'],
  'release_gates':['Mã thiết bị + thông số điện đã đối chiếu','Pin map/cọc và đầu cốt xác nhận','Tư thế lắp và kích thước gá xác nhận','Số đầu dây N/PE đáp ứng','Tuyến/tiết diện/độ dài và bảo vệ từng kết nối','Hệ đồng: nhiệt, ngắn mạch, khoảng cách, gối đỡ, che chắn','Cánh: khoét, chiều sâu thân và dây qua bản lề'],
  'documentation':['https://www.ls-electric.com/upload/customer/download/1483/MCB_E_180131.pdf','https://www.electrical-installation.org/enwiki/Distribution_switchboards']}
 assert len(devices)==len(package['instances']) and len(connections)==len(package['conductors'])
 assert {f'L{i}' for i in range(1,20)} <= {d['id'] for d in devices}
 assert sum(d['id']=='PE' for d in devices)==sum(d['id']=='N' for d in devices)==1
 (out/'lap_dat_tu1.json').write_text(json.dumps(model,ensure_ascii=False,indent=2),encoding='utf-8')
 return model
