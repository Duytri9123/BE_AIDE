"""Add missing source-linked candidates from the verified combined library."""
import ast,json,shutil,hashlib,logging
from pathlib import Path
import ezdxf
from ezdxf import bbox
from ezdxf.addons.drawing import Frontend,RenderContext
from ezdxf.addons.drawing.config import Configuration
from ezdxf.addons.drawing.svg import SVGBackend
from ezdxf.addons.drawing.layout import Page
from ezdxf.addons.drawing.properties import LayoutProperties
BASE=Path(__file__).resolve().parents[1];ROOT=BASE/'data/CatalogTB'
logging.getLogger('ezdxf').setLevel(logging.ERROR)
audit=json.loads((ROOT/'kiem_tra_nguon_tong_hop_1.json').read_text(encoding='utf-8'));added=[]
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
for candidate in audit['candidates']:
 if candidate['existing_matches']:continue
 r=candidate['item'];block=r['source_block'];kind=candidate['source_kind']
 if 'TỔNG HỢP 1.dwg' not in r.get('source_files',[r.get('source_file')]):continue
 if 'INVERTER' in block:category='Biến tần';title='Biến tần · nhãn INVERTER-0.75K';purpose='Điều khiển động cơ theo cấu hình biến tần được xác nhận.'
 elif r.get('category')=='Biến áp':
  category='Nguồn và biến áp';title={'TR':'Biến áp · nhãn TR','VTPK_NGUON 24VAC':'Nguồn · nhãn 24VAC','VTPK_NGUON 24VDC':'Nguồn · nhãn 24VDC'}[block];purpose='Cấp nguồn cho mạch điều khiển; cần xác định loại nguồn và sơ đồ cọc.'
 else:category='Chống sét';title='Chống sét · mẫu CAD '+r['id'][:6];purpose='Mẫu hình trong ô chống sét của nguồn; cần xác định loại SPD và đặc tính trước thiết kế.'
 key='TH1_'+r['id'];folder=ROOT/category/'ThietBi'/key;view=folder/'HinhChieu'/key;view.mkdir(parents=True,exist_ok=True)
 src=BASE/'data/device_layouts'/kind/r['filename'];shutil.copy2(src,view/'ban_ve.dxf');doc=ezdxf.readfile(src);ext=bbox.extents(doc.modelspace(),fast=True)
 assert ext.has_data and doc.units==4
 backend=SVGBackend();Frontend(RenderContext(doc),backend,config=Configuration()).draw_layout(doc.modelspace(),layout_properties=LayoutProperties('Model','#ffffff','#243b53',units=4,dark_background=False));(view/'xem_truoc.svg').write_text(backend.get_string(Page(0,0)),encoding='utf-8')
 source={'file':audit['source_dwg'],'sha256':audit['source_sha256'],'block':block,'asset_id':r['id'],'parent_asset_id':r.get('parent_asset_id'),'geometry_key':candidate['geometry_key']}
 record={'id':key,'thiet_bi':key,'loai_hinh':'block','ten_hinh':title,'kich_thuoc_hinh_mm':{'ngang':round(ext.size.x,3),'cao':round(ext.size.y,3)},'tep':{'cad_dxf':'ban_ve.dxf','preview':'xem_truoc.svg'},'nguon':source,'source_state_verified':False,'nhan_hien_thi':'Hình nguồn · chưa xác nhận mặt'};save(view/'thong_tin.json',record)
 profile={'nhom':category,'ten_kieu':title,'ten_san_pham':title,'ban_chat':category,'cong_dung':purpose,'vi_tri_lap_dat':'Chưa xác nhận kiểu gá và tư thế lắp theo mã thiết bị.','hang_xac_nhan':None,'ma_dong_san_pham':None,'thong_so':{'nhan_block_nguon':block,'dien_ap_xac_nhan_V':None,'cong_suat_xac_nhan':None},'muc_do_xac_nhan':'CAD tham khảo từ thư viện nguồn; chưa xác nhận mã đặt hàng, hãng, hướng nhìn và thông số điện.','nguon_tham_khao':[],'nguon_cad':source,'cac_hinh_cad':[key],'auto_select':False,'needs_review':True,'trang_thai_lua_chon':'Chỉ tham khảo, cần xác nhận mã và trạng thái CAD trước sử dụng.','yeu_cau_chon_day':{'tiet_dien_mac_dinh_mm2':None,'quy_tac':'Xác định từng cọc, dòng, điện áp, bảo vệ và giới hạn dây theo mã thực tế.'},'yeu_cau_lap_dat':{'status':'Chưa xác nhận dữ liệu hãng','unknown_value':None,'cad_rotation_is_mounting_approval':False}}
 save(folder/'thong_tin_thiet_bi.json',profile);added.append({'category':category,'profile':str(folder/'thong_tin_thiet_bi.json'),'id':key,'title':title})
audit['added']=added;save(ROOT/'kiem_tra_nguon_tong_hop_1.json',audit);print('Added',len(added),'source CAD profiles')
