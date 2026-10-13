"""Persist selection evidence; do not infer N/PE identity from similar geometry."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/'data/CatalogTB'
def save(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
rules={'version':1,'required_steps':['Đọc toàn bộ chỉ mục thiết bị trước khi chọn hãng hoặc dựng CAD mới.','Bóc yêu cầu sơ đồ thành vai trò, số lượng, thông số và vị trí lắp.','Tra mọi nhóm thư mục theo vai trò; ưu tiên hãng chỉ cho thiết bị chính.','Kiểm tra bản CAD đơn, hướng nhìn, biến thể và nguồn xác định; không dùng hình giống nhau để xác nhận cùng thiết bị.','Nếu có CAD phù hợp trong thư viện phải dùng trước CAD tự dựng.','Xuất bảng đối chiếu yêu cầu → hồ sơ → mặt CAD → số lượng → mức xác định; ghi rõ yêu cầu chưa đáp ứng.'],
 'N_PE':{'default_quantity_per_cabinet':{'PE':1,'N':1},'quantity_policy':'Đây là mặc định bố trí, không phải quy tắc điện cho mọi tủ. Chỉ tăng số lượng khi sơ đồ, phân vùng RCD, số đầu dây hoặc tính toán yêu cầu; phải ghi lý do.',
 'identity_policy':'Thanh PE và thanh N phải có vai trò xác định theo nguồn/nhãn gốc; không lấy một CAD chưa xác định rồi gán cả hai.',
 'capacity_policy':'Số lỗ CAD không tự động bằng số đầu dây hữu dụng; không suy ra dòng, vật liệu hay tiết diện dây từ kích thước mặt.'},
 'shunt_trip':{'parent_role':'MCCB','placement':'Phụ kiện tích hợp, không tạo ô bố trí độc lập trừ khi phụ kiện thực tế lắp ngoài.','quantity_policy':'Chỉ thêm khi sơ đồ cần cắt từ xa; chọn đúng điện áp và dòng MCCB.'},
 'manufacturer_policy':'LS ưu tiên thiết bị đóng cắt chính trong phương án LS; phụ kiện/đo lường chọn hãng phù hợp khác khi cần. Không kết luận hãng không có thiết bị chỉ vì thư viện thiếu CAD.'}
save(ROOT/'ai_selection_rules.json',rules)
rules['conductors']={'selection_unit':'Từng kết nối/cọc, không phải một loại dây cố định cho cả thiết bị',
 'required_fields':['Thiết bị và cọc đầu nối','Từ/đến','Vai trò mạch','Cu/Al/đồng thanh/đồng mềm','Tiết diện','Bảo vệ phía trước','Kiểu đầu cốt và giới hạn cọc','Tuyến/chiều dài','Căn cứ và mức xác định'],
 'distribution_options':['Cáp cách điện','Thanh đồng cứng','Thanh đồng mềm cách điện','Thanh lược hãng','Đồng xương cá gia công có gối đỡ và che chắn'],
 'checks':['Không suy ra tiết diện điện từ CAD','Không đồng nhất mm² cáp và mm² thanh đồng về dòng cho phép','Kiểm tra tải, nhiệt, ngắn mạch, sụt áp, đầu nối và bảo vệ của đoạn trước CB','Đồng xương cá cần đúng pha, bước cực, cọc đấu và khả năng chịu dòng; không nối chung R/S/T','Không tự suy chiều dài đặt hàng từ khoảng cách thẳng 2D'],
 'sources':['https://www.electrical-installation.org/enwiki/Sizing_and_protection_of_conductors','https://www.ls-electric.com/upload/customer/download/1483/MCB_E_180131.pdf']}
rules['manufacturer_reviews']={'Chint':'Chint/kiem_tra_chint.json','Schneider':'Schneider/kiem_tra_schneider.json','Shihlin':'Shihlin/kiem_tra_shihlin.json','ABB':'ABB/kiem_tra_abb.json','O-Sung':'O-Sung/kiem_tra_osung.json','RMU':'RMU/kiem_tra_rmu.json','Đồng':'Đồng/kiem_tra_dong.json'}
rules['layout_review']={'reference':'../form_tu_cong_nghiep/04_kiem_tra_mau_va_bo_tri.json','rules':['Tách mẫu vỏ khỏi Form phân khoang IEC','Không coi chiều dài/diện tích CAD là khả năng chịu dòng','Giữ nguyên thanh N/PE và số lỗ; chọn biến thể 8/13 vị trí khi xác nhận hồ sơ, không tự kéo dài hoặc nhân đôi','Nhãn thiết bị có thể ẩn trên bản bố trí nhưng phải giữ id trong JSON/BOM']}
rules['breaker_arrangement']={'sort_preference':'Dòng định mức lớn trước, nhỏ sau; nhóm theo số cực và đầu nối để thuận đi đồng','status':'Ưu tiên bố trí, không khẳng định là quy tắc bắt buộc IEC','balance':['Số CB hai bên','Chiều cao chiếm chỗ','Tải và nhiệt theo từng nhánh','Pha cấp theo sơ đồ, không đổi pha chỉ để đẹp hình'],'copper_checks':['Cọc và chiều nguồn/tải theo hãng','Tư thế xoay được phép','Bước cực và đầu nối thanh đồng','Tiết diện, nhiệt, Icw/Ipk','Khoảng cách pha, chiều sâu, gối đỡ và che chắn'],'sources':['https://www.electrical-installation.org/enwiki/Distribution_switchboards','https://webinfo.rittal.com/hubfs/Brosch%C3%BCre_Ri4Power_Technical%20System%20Catalogue_EN.pdf','https://www.ls-electric.com/upload/customer/download/1483/MCB_E_180131.pdf']}
save(ROOT/'ai_selection_rules.json',rules)
for key,role,title in [('ThanhE_10x115','PE','Thanh tiếp địa PE'),('ThanhN_10x160','N','Thanh trung tính N'),('CauNPE',None,'Thanh đấu nối có vít · chưa xác định N hay PE')]:
 p=next(ROOT.rglob(key+'/thong_tin_thiet_bi.json'));d=json.loads(p.read_text(encoding='utf-8'))
 d['ten_san_pham']=d['ten_kieu']=title
 d['cad_tham_so']={'cho_phep_keo_dai':False,'giu_nguyen_cad_mac_dinh':True,'truc':'y_local','chieu_rong_mm':10 if role else None,'buoc_lo_mm':7 if role else None,'duong_kinh_lo_giua_mm':3 if role else None,'phuong_phap':'Giữ nguyên CAD. Không tự kéo dài, thêm lỗ hay nhân đôi thanh; chọn biến thể theo số cọc thật, không tổng số lỗ','xac_nhan_dien':False}
 d['nhan_dien_ai']={'vai_tro_dien':role,'tu_dong_chon_theo_vai_tro':bool(role),'so_luong_mac_dinh':1 if role else None,
  'can_cu':'Nhãn E/N của hồ sơ CAD gốc; chưa xác nhận hãng/thông số điện' if role else 'Hai CAD dạng thanh đấu nối khác nhau; không có căn cứ xác nhận CAD nào là N, CAD nào là PE hoặc là hai mặt của cùng sản phẩm.',
  'khong_suy_ra':['Dòng định mức','Vật liệu','Số đầu dây hữu dụng','Tính thay thế điện từ hình học']}
 d['cong_dung']=('Đấu dây bảo vệ PE, liên kết tiếp địa vỏ tủ.' if role=='PE' else 'Đấu dây trung tính N; cấu hình gá và liên kết theo sơ đồ nối đất.' if role=='N' else 'Thanh đấu nối có vít. Chờ xác định chức năng điện và biến thể trước khi AI chọn cho N/PE.')
 d['muc_do_xac_nhan']=d['nhan_dien_ai']['can_cu']
 d['quy_cach_hien_thi']=('PE · mặt lỗ đấu nối · 10 × 115 mm' if role=='PE' else 'N · mặt lỗ đấu nối · 10 × 160 mm' if role=='N' else 'Hai CAD khác kích thước · không tự gán N/PE')
 save(p,d)
index=[]
for p in sorted(ROOT.rglob('thong_tin_thiet_bi.json')):
 d=json.loads(p.read_text(encoding='utf-8'))
 existing_wire=d.get('yeu_cau_chon_day',{})
 existing_install=d.get('yeu_cau_lap_dat',{})
 kind=(str(d.get('ban_chat',''))+' '+str(d.get('ten_san_pham',''))).casefold()
 role=d.get('nhan_dien_ai',{}).get('vai_tro_dien')
 connection_roles=([role] if role else ['Nguồn vào','Ra tải','Phụ kiện điều khiển nếu có'] if any(x in kind for x in ['mccb','mcb','khởi động từ','contactor']) else
  ['Mạch đo / điều khiển, chọn theo đúng cọc thực tế'] if any(x in kind for x in ['đèn','đồng hồ','vôn','đo lường','điều khiển','cầu chì','cầu đấu','quạt','tụ','kháng']) else ['Xác định thiết bị có phần điện hay chỉ cơ khí trước khi chọn dây'])
 d['yeu_cau_chon_day']={'vai_tro_ket_noi':connection_roles,'tiet_dien_mac_dinh_mm2':None,
  'quy_tac':'Chọn theo từng kết nối, thông số điện và bảo vệ phía trước; không suy từ hình CAD. Vật tư thuần cơ khí không yêu cầu dây.',
  'vat_lieu_va_kieu':['Cu cách điện','Al nếu cọc/đầu cốt cho phép','Đồng thanh/đồng mềm/thanh lược/xương cá nếu đúng chức năng và cọc đấu'],
  'can_kiem_tra':['Dòng/điện áp và bảo vệ','Tiết diện/vật liệu cọc cho phép','Kiểu đầu cốt','Điều kiện nhiệt và tuyến','Độ dài thực tế']}
 d['yeu_cau_lap_dat']={'schema':'installation_contract.schema.json','status':'Chưa có dữ liệu gá/cọc theo mã đầy đủ','required_manufacturer_data':['Tư thế lắp được phép','Chiều sâu thân và khoảng trống','Vị trí lỗ gá hoặc khoét','Sơ đồ cọc nguồn/tải/điều khiển','Giới hạn dây và đầu nối thanh đồng','Lực siết','Khoảng cách điện và che chắn'],'unknown_value':None,'cad_rotation_is_mounting_approval':False}
 if d.get('nhom') in ('Mitsubishi','Chint','Schneider','Shihlin','ABB','O-Sung','RMU','Đồng','Đố') or p.parent.name.startswith('SRC_'):
  d['yeu_cau_chon_day'].update(existing_wire)
  d['yeu_cau_lap_dat'].update(existing_install)
 save(p,d)
 index.append({'profile':p.relative_to(ROOT).as_posix(),'name':d.get('ten_san_pham'),'category':d.get('nhom'),'brand':d.get('hang_xac_nhan'),'auto_select':d.get('auto_select'),'needs_review':d.get('needs_review'),
  'search_aliases':d.get('tu_khoa_tim_kiem',[]),'type':d.get('ban_chat'),'use':d.get('cong_dung'),'spec':d.get('thong_so'),'identification':d.get('nhan_dien_ai',{}),'conductor_requirements':d.get('yeu_cau_chon_day'),'installation_requirements':d.get('yeu_cau_lap_dat'),'parametric_cad':d.get('cad_tham_so'),
  'views':[{'id':v['id_hinh_goc'],'face':v.get('huong_nhin'),'dxf':(p.parent/v['duong_dan']).relative_to(ROOT).as_posix(),'placement':v.get('bo_tri_trong_tu',{})} for v in d.get('cad_don',[])]})
save(ROOT/'ai_device_index.json',{'rules':'ai_selection_rules.json','count':len(index),'items':index})
print('Indexed',len(index),'profiles; PE/N identity updated')

