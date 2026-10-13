"""Review every Mitsubishi profile; preserve CAD and separate selected ratings."""
import json
from pathlib import Path
import ezdxf
from ezdxf import bbox
ROOT=Path(__file__).resolve().parents[1]/'data/CatalogTB/Mitsubishi'
CATALOG='https://www.mitsubishielectric.com/fa/download/search.page?kisyu=%2Flvcb&mode=manual'
CAD='https://www.mitsubishielectric.com/fa/download/cad/search.page?category1=102&kisyu=%2Flvcb&mode=cad'
CONTACTOR='https://www.mitsubishielectric.com/fa/products/faspec/download.page?category=ex&formNm=CONTACTOR_S-T21_4632&id=spec&kisyu=%2Flvsw&lang=2&popup=1&sub=catalog'
report=[]
for p in sorted(ROOT.rglob('thong_tin_thiet_bi.json')):
 d=json.loads(p.read_text(encoding='utf-8'));spec=d['thong_so'];poles=spec.get('so_cuc','');kind=d.get('ban_chat','')
 code=d.get('ma_dong_san_pham') or p.parent.name
 prefix='Contactor' if p.parent.name.startswith('S_T') else 'RCCB' if code=='BV-D' else 'MCB' if code.startswith('BH-') else 'MCCB'
 dc=code in ['NF800-SDW','NF1250-SDW','NF1600-SDW'] and poles=='2P'
 d['ten_san_pham']=d['ten_kieu']=f'{prefix} Mitsubishi {code} · {poles}'+(' · DC' if dc else '')
 d['cac_ma_cung_than_cad']=[c.strip() for c in code.split('/')]
 if dc:
  spec['loai_nguon']='DC — cấu hình 2P chuẩn theo catalog WS-V'
  spec['dien_ap_tham_khao']='250 V DC; không lấy Ui 690 V làm điện áp làm việc AC'
  d['luu_y_loai_nguon']='Không tự chọn cấu hình SDW 2P này cho nguồn AC.'
  url='https://dl.mitsubishielectric.com/dl/fa/document/catalog/lvcb/yn-c-0720/y0720h2303.pdf'
  d['nguon_tham_khao']=list(dict.fromkeys(d.get('nguon_tham_khao',[])+[url]))
 contactor=p.parent.name.startswith('S_T')
 roles=['Nguồn ba pha vào','Ra tải ba pha','Cuộn hút','Tiếp điểm phụ theo biến thể'] if contactor else ['Nguồn vào','Ra tải']
 d['cau_hinh_chon']={'hang':'Mitsubishi Electric','dong_san_pham':d.get('ma_dong_san_pham'),'so_cuc':poles,
  'dong_dinh_muc_A_da_chon':None,'dien_ap_lam_viec_V_da_chon':None,'Icu_kA_tai_dien_ap_da_chon':None,'Ics_kA_tai_dien_ap_da_chon':None,
  'dien_ap_cuon_hut_V_da_chon':None if contactor else 'Không áp dụng trừ phụ kiện điện',
  'dong_ro_mA_da_chon':None if p.parent.name.startswith('BV_D') else 'Không áp dụng nếu không có bảo vệ rò',
  'quy_tac':'Thông số dải/dòng sản phẩm không phải cấu hình đặt hàng. Không suy dòng định mức từ AF hay kích thước CAD.',
  'can_chon':(['Mã riêng trong nhóm chung cỡ thân','AC-3/AC-1 và dòng tại điện áp tải','Điện áp cuộn hút','Tiếp điểm phụ và rơ le nhiệt tương thích'] if contactor else ['Mã đầy đủ, số cực và dòng/trip unit','Điện áp và khả năng cắt tương ứng','Phụ kiện theo đúng dòng'])}
 d['yeu_cau_chon_day'].update({'vai_tro_ket_noi':roles,'vat_lieu_da_xac_nhan':None,'tiet_dien_mac_dinh_mm2':None,
  'quy_tac':'Tra dải dây, đầu cốt, cọc đồng thanh và lực siết theo đúng mã. Mạch cuộn hút/tiếp điểm phụ chọn riêng với dây tải; không tự coi cọc cho phép Al.'})
 d['yeu_cau_lap_dat'].update({'nguon_hang':[CONTACTOR] if contactor else [CATALOG,CAD],
  'tu_the_lap_duoc_phep':None,'so_do_coc_hang':None,'luc_siet_Nm':None,'co_lo_gia_mm':None,'chieu_sau_than_mm':None,
  'thanh_dong':{'cho_phep':None,'adapter':None,'buoc_cuc_mm':None,'can_kiem_tra':['Cọc nguồn/tải','Đầu nối/đầu cốt tương thích','Vách cách điện đầu cực','Khoảng cách và lực siết']},
  'quy_tac_xoay':'Mặt trước/bên là hướng nhìn CAD, không phải tư thế lắp được hãng cho phép; chưa tự duyệt xoay ±90°.'})
 d['nguon_tham_khao']=list(dict.fromkeys(d.get('nguon_tham_khao',[])+([CONTACTOR] if contactor else [CATALOG,CAD])))
 d['quy_cach_hien_thi']=poles+(' · DC' if dc else '')+' · '+str(spec.get('dong_ac3_cua_bien_the') or spec.get('dong_dinh_muc') or spec.get('co_khung') or 'Chọn cấu hình điện')
 d['luu_y_thong_so']='Dải tham khảo của dòng, chưa chọn mã đặt hàng; CAD không xác nhận thông số điện. BV-D là RCCB cần bảo vệ quá dòng phía trước; AF không bằng dòng tải chọn.'
 views=[];errors=[]
 for v in d['cad_don']:
  f=p.parent/v['duong_dan'];doc=ezdxf.readfile(f);ext=bbox.extents(doc.modelspace())
  if not ext.has_data or doc.units!=4:errors.append(v['id_hinh_goc']+': hình học hoặc đơn vị không đúng')
  if ext.has_data and max(abs(ext.center.x),abs(ext.center.y))>.1:errors.append(v['id_hinh_goc']+': chưa đặt tâm tại gốc')
  cover='COVER' in v['id_hinh_goc'].upper()
  v['vai_tro_cad']='Tấm che đầu cực' if cover else 'Mặt thiết bị'
  v['nhan_hien_thi']=('Tấm che đầu cực · '+poles if cover else v['huong_nhin']+' · '+poles)
  v['kich_thuoc_bao_cad_mm']={'ngang':round(ext.size.x,3),'cao':round(ext.size.y,3)}
  views.append({'id':v['id_hinh_goc'],'face':v['huong_nhin'],'role':v['vai_tro_cad'],'size_mm':v['kich_thuoc_bao_cad_mm']})
 primary=d['cad_chen_tu']['id_hinh_goc']
 if 'COVER' in primary.upper():errors.append('Mặt chính đang là tấm che')
 p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 report.append({'profile':p.relative_to(ROOT).as_posix(),'name':d['ten_san_pham'],'view_count':len(views),'views':views,'errors':errors,
  'electrical_status':'Có dải tham khảo, chưa chọn cấu hình','installation_status':'Cần dữ liệu hãng theo mã; chưa có lực siết/cọc/tư thế xác nhận'})
(ROOT/'kiem_tra_lap_dat.json').write_text(json.dumps({'profiles':len(report),'views':sum(r['view_count'] for r in report),'errors':sum(len(r['errors']) for r in report),'items':report},ensure_ascii=False,indent=2),encoding='utf-8')
print('Reviewed',len(report),'profiles,',sum(r['view_count'] for r in report),'views, errors:',sum(len(r['errors']) for r in report))
