"""Import Mitsubishi active CAD states into named product/number-of-poles profiles."""
import json,re,logging
logging.getLogger("ezdxf").setLevel(logging.ERROR)
from pathlib import Path
import ezdxf
from ezdxf import bbox
from ezdxf.addons import Importer
from ezdxf.addons.drawing import Frontend,RenderContext
from ezdxf.addons.drawing.layout import Page
from ezdxf.addons.drawing.properties import LayoutProperties
from ezdxf.addons.drawing.svg import SVGBackend
ROOT=Path(__file__).resolve().parents[1]/'data'/'CatalogTB'
BASE=ROOT.parents[2]/'Tudien/CATALOG_PHU_KIEN_DOC_LAP/MITSUBISHI_D04_DU_LIEU_MOI'
TARGET=ROOT/'Mitsubishi'/'ThietBi'
MC='https://us.mitsubishielectric.com/fa/en/support/technical-support/knowledge-base/getdocument/?docid=3E26SJWH3ZZR-38-3004'
DIN='https://dl.mitsubishielectric.com/dl/fa/document/catalog/lvcb/yn-c-0713/y0713c2303.pdf'
NF='https://dl.mitsubishielectric.com/dl/fa/document/catalog/lvcb/yn-c-0720/y0720f2102.pdf'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def visible(doc,es):
 for e in es:
  if e.dxf.get('invisible',0):continue
  layer=doc.layers.get(e.dxf.layer)
  if layer.is_off() or layer.is_frozen():continue
  if e.dxftype()=='INSERT':yield from visible(doc,e.virtual_entities())
  elif e.dxftype() not in ('TEXT','MTEXT','ATTRIB','ATTDEF','DIMENSION','LEADER','VIEWPORT'):yield e
manifest=read(BASE/'native/manifest.json');variants=read(BASE/'native/views.json')
profiles={}
for item in manifest:
 sid=item['id'];option=item['dynamic_properties'][0]['value'];attrs={a['tag']:a['text'] for a in item['attributes']}
 states=[{'id':sid,'option':option}]+[v for v in variants if v['source_id']==sid]
 if '-C2-' in sid:
  own=option.split(':')[0]
  states=[s for s in states if s['option'].split(':')[0]==own]
 elif '-C3-' in sid and not sid.endswith('I01'):continue
 fronts=[s for s in states if 'Front View' in s['option']]
 for front in fronts:
  op=front['option'];pole=re.search(r'([1-4])P:',op);poles=int(pole[1]) if pole else 3
  if '-C2-' in sid:code=op.split(':')[0].replace(',',' /')
  elif '-C3-' in sid:code='BV-D' if '(BV-D)' in op else 'BH-DN' if '(BH-DN)' in op else 'BH-D6'
  else:code=attrs.get('TYPE0') if front['id']==sid else attrs.get('TYPE'+str(poles),attrs.get('TYPE0'))
  code=code.replace(' (2 Poles)','')
  kind='Khởi động từ' if code.startswith('S-T') else 'RCCB' if code=='BV-D' else 'MCB' if code.startswith('BH') else 'MCCB'
  key=re.sub(r'[^A-Za-z0-9]+','_',code).strip('_')+f'_{poles}P'
  group=profiles.setdefault(key,{'code':code,'poles':poles,'kind':kind,'states':{}})
  group['states'][front['id']]=front
  for state in states:
   so=state['option'];sp=re.search(r'([1-4])P:',so)
   if 'Front View' in so:continue
   if '-C2-' in sid:
    if so.split(':')[0]!=op.split(':')[0]:continue
   elif sp and int(sp[1])!=poles:continue
   if code=='BV-D' and 'Cover' in so and '(BV-D)' not in so:continue
   if code=='BH-DN' and 'Cover' in so and '(BH-DN)' not in so:continue
   if code=='BH-D6' and ('(BV-D)' in so or '(BH-DN)' in so):continue
   group['states'][state['id']]=state
review_path=ROOT.parents[1]/'scripts/catalogtb_face_review.json';review=read(review_path)
report=[]
for key,g in profiles.items():
 folder=TARGET/key;ids=[];code=g['code'];kind=g['kind'];poles=g['poles'];spec={'so_cuc':f'{poles}P'}
 if kind=='Khởi động từ':
  currents={'S-T10':(9,4),'S-T12':(12,5.5),'S-T20':(18,7.5),'S-T21':(23,11),'S-T25':(30,15),'S-T35':(40,18.5),'S-T50':(50,22)}
  spec.update({'cap_su_dung':'AC-3 / AC-1','tan_so_Hz':'50/60','dien_ap_cuon_hut':'Chọn theo biến thể cuộn hút','dong_ac3_cua_bien_the':' / '.join(f'{c}: {currents[c][0]} A, {currents[c][1]} kW tại 380–440 VAC' for c in code.split(' / ') if c in currents)})
  use='Đóng cắt động cơ hoặc tải động lực bằng tín hiệu điều khiển cuộn hút.';source=MC
 elif kind=='RCCB':
  spec.update({'dong_dinh_muc':'25 / 40 / 63 A — chọn biến thể','dien_ap_dinh_muc':'230/400 VAC','chuc_nang_bao_ve':'Dòng rò; không tích hợp bảo vệ quá dòng','dong_ro_tac_dong':'Chọn theo biến thể','tieu_chuan':'IEC 61008'})
  use='Ngắt mạch khi phát hiện dòng rò; phối hợp MCB hoặc MCCB để bảo vệ quá tải và ngắn mạch.';source=DIN
 elif kind=='MCB':
  spec.update({'dong_dinh_muc':'6 / 10 / 16 / 20 A' if code=='BH-DN' else '0,5–63 A — chọn biến thể','dien_ap_dinh_muc':'230 VAC' if code=='BH-DN' else '230/400 VAC','dac_tinh_tac_dong':'C' if code=='BH-DN' else 'B / C / D — chọn biến thể','kha_nang_cat':'Icn 4,5 kA tại 230 VAC' if code=='BH-DN' else 'Icn 6 kA theo IEC 60898-1'})
  if code=='BH-DN':spec['so_cuc']='1P+N'
  use='Bảo vệ mạch nhánh trước quá tải và ngắn mạch.';source=DIN
 else:
  frame=re.search(r'NF(\d+)',code)[1]
  spec.update({'co_khung':frame+' AF','dong_dinh_muc':'Dòng định mức In: chọn theo cấu hình thiết bị','kha_nang_cat':'Chọn Icu/Ics theo mã, điện áp và số cực','tieu_chuan':'IEC 60947-2'})
  if code=='NF30-CS':spec.update({'dong_dinh_muc':'3 / 5 / 10 / 15 / 20 / 30 A','kha_nang_cat':'Icu/Ics 1,5/1,5 kA tại 380/415 VAC'})
  if code=='NF125-CV':spec['dong_dinh_muc']='15–125 A — chọn biến thể'
  if code=='NF250-CV':spec['dong_dinh_muc']='100–250 A — chọn biến thể'
  if code=='NF630-CW':spec['dong_dinh_muc']='500 / 600 / 630 A — chọn biến thể'
  use='Đóng cắt và bảo vệ lộ nguồn hoặc nhánh động lực trước quá tải và ngắn mạch.';source=NF
 for state in g['states'].values():
  src=ezdxf.readfile(BASE/'native'/(state['id']+'.dxf'));es=list(visible(src,src.modelspace()));assert es
  doc=ezdxf.new('R2018');doc.units=4;imp=Importer(src,doc);imp.import_entities(es);imp.finalize();ext=bbox.extents(doc.modelspace(),fast=True);assert ext.has_data
  op=state['option'];face='Mặt bên' if 'Side' in op else 'Mặt trên' if 'Top' in op else 'Mặt dưới' if 'Bottom' in op else 'Mặt trước'
  label='Nắp che mặt trước' if 'Cover' in op else face+(' · có đầu nối' if 'Connector' in op else ' · có vách ngăn' if 'Barrier' in op else '')
  dest=folder/'HinhChieu'/state['id'];dest.mkdir(parents=True,exist_ok=True);doc.saveas(dest/'ban_ve.dxf')
  backend=SVGBackend();Frontend(RenderContext(doc),backend).draw_layout(doc.modelspace(),layout_properties=LayoutProperties('Model','#ffffff','#243b53',units=4,dark_background=False))
  (dest/'xem_truoc.svg').write_text(backend.get_string(Page(max(35,ext.size.x+8),max(35,ext.size.y+8))),encoding='utf-8')
  write(dest/'thong_tin.json',{'id':state['id'],'loai_hinh':'view','ten_hinh':face,'nhan_hien_thi':label,'tep':{'cad_dxf':'ban_ve.dxf','preview':'xem_truoc.svg'},'kich_thuoc_hinh_mm':{'ngang':round(ext.size.x,2),'cao':round(ext.size.y,2)},'trang_thai_block':op})
  review[state['id']]=face;ids.append(state['id'])
 title=f'{kind} Mitsubishi {code}'
 write(folder/'thong_tin_thiet_bi.json',{'nhom':'Mitsubishi','ten_kieu':title,'ten_san_pham':title,'hang_xac_nhan':'Mitsubishi Electric','ma_dong_san_pham':code,'ban_chat':kind,'cong_dung':use,'vi_tri_lap_dat':'Trên ray DIN hoặc tấm lắp bên trong tủ điện; mặt thao tác hướng về phía bảo trì.','thong_so':spec,'quy_cach_hien_thi':spec['so_cuc'],'cac_hinh_cad':ids,'tai_lieu_hang':source,'nguon_tham_khao':[source],'muc_do_xac_nhan':'Đã xác định dòng thiết bị; thông số là các tùy chọn của dòng, chưa chọn mã đặt hàng đầy đủ.','dac_diem':['Mỗi mặt hoặc phương án nắp che, đầu nối, vách ngăn có một DXF riêng.','Chọn dòng định mức và thông số điện của biến thể phù hợp hệ thống.'],'lua_chon_ky_thuat':['Đối chiếu dòng tải, điện áp, khả năng cắt và phối hợp bảo vệ.']})
 report.append({'ma':code,'so_cuc':spec['so_cuc'],'so_cad':len(ids)})
write(review_path,review);write(ROOT/'Mitsubishi/kiem_tra_mitsubishi.json',{'ho_so':report})
print('Mitsubishi profiles:',len(report),'CAD views:',sum(r['so_cad'] for r in report))
