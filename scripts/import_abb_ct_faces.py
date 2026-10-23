"""Publish supplier CT1M projections with dimension-derived mm scale evidence."""
import collections,hashlib,json,sqlite3
from pathlib import Path
import ezdxf
from ezdxf import bbox
from ezdxf.addons import Importer
from ezdxf.addons.drawing import Frontend,RenderContext,svg,layout,matplotlib
from ezdxf.math import Matrix44
from PIL import Image,ImageDraw,ImageOps
from download_abb_ct_sources import SOURCES

ROOT=Path(__file__).resolve().parents[1]/'data/CatalogTB'
TECH='https://new.abb.com/low-voltage/cs/nizke-napeti/produkty/modularni-pristroje/merici-pristroje/proudove-transformatory'
RANGES={'CT1M-2':'50–400','CT1M-3':'300–600','CT1M-4':'300–800','CT1M-5':'1000','CT1M-6':'250–1500','CT1M-7':'2000–2500','CT1M-8':'600–2000','CT1M-10':'600–4000','CT1M-12':'3000–6000','CT1M-S-30':'100–400','CT1M-S-80':'250–1000','CT1M-S-120':'800–1500'}
SIDE={'CT1M-2':(175,325),'CT1M-3':(165,305),'CT1M-4':(170,305),'CT1M-5':(185,300),'CT1M-6':(190,305),'CT1M-7':(215,310),'CT1M-8':(210,300),'CT1M-10':(200,310),'CT1M-12':(220,315),'CT1M-S-30':(185,290),'CT1M-S-80':(215,310),'CT1M-S-120':(210,295)}
ISOLEFT={'CT1M-2':336,'CT1M-3':317,'CT1M-4':319,'CT1M-5':318,'CT1M-6':317,'CT1M-7':328,'CT1M-8':307,'CT1M-10':320,'CT1M-12':326,'CT1M-S-30':321,'CT1M-S-80':323,'CT1M-S-120':313}
TYPES={'LINE','SPLINE','ELLIPSE','ARC','CIRCLE','POLYLINE','LWPOLYLINE','HATCH'}

def main():
 report=[]
 for family,uid in SOURCES.items():
  folder=ROOT/'BienDong/ABB/NguonBenNgoai'/family;source=folder/(family+'.dxf');doc=ezdxf.readfile(source)
  evidence=json.loads((folder/'source.json').read_text(encoding='utf8'))
  scales=[]
  for dimension in doc.modelspace().query('DIMENSION'):
   actual=dimension.dxf.get('actual_measurement');measured=dimension.get_measurement()
   if actual and isinstance(measured,(float,int)) and actual>1:scales.append(round(measured/actual,5))
  counts=collections.Counter(scales);scale,count=counts.most_common(1)[0]
  if count<3 or count/len(scales)<.7:raise ValueError('Conflicting dimension scale: '+family)
  geometry=[]
  for entity in doc.modelspace():
   if entity.dxftype() not in TYPES or entity.dxf.layer not in {'1','2'}:continue
   box=bbox.extents([entity])
   if box.has_data:geometry.append((entity,box))
  intervals=sorted((b.extmin.y,b.extmax.y) for _,b in geometry if 20<b.extmin.x and b.extmax.x<200 and 15<b.extmin.y and b.extmax.y<280)
  groups=[]
  for a,b in intervals:
   if not groups or a>groups[-1][1]+4:groups.append([a,b])
   else:groups[-1][1]=max(groups[-1][1],b)
  if len(groups)!=2:raise ValueError('Unclear projection separation: '+family)
  boundary=(groups[0][1]+groups[1][0])/2
  left,right=SIDE[family]
  windows=[('WIRE','Mặt xuyên dây',(20,boundary,min(200,left-1),280)),('SIDE','Mặt bên',(left-8,70,min(right+8,ISOLEFT[family]-2),280)),('TOP','Mặt trên',(20,15,min(200,left-1),boundary)),('ISO','Hình trục đo',(ISOLEFT[family]-.1,70,405,270))]
  profile_path=ROOT/'BienDong/ABB'/family/'thong_tin_thiet_bi.json';profile_path.parent.mkdir(parents=True,exist_ok=True)
  split='-S-' in family
  name=f"Biến dòng ABB {family} · {'Lõi mở' if split else 'Lõi kín'}"
  profile={'nhom':'BienDong','ten_kieu':name,'ten_san_pham':name,'hang_xac_nhan':'ABB','ma_dong_san_pham':family,'ban_chat':'CT',
   'cong_dung':'Biến đổi dòng tải sang dòng thứ cấp cho đồng hồ đo; chọn tỷ số, cấp chính xác, VA và cửa sổ theo mã đầy đủ.',
   'thong_so':{'Loại lõi':'Lõi mở' if split else 'Lõi kín','Dải dòng sơ cấp (A)':RANGES[family],'Dòng thứ cấp (A)':5,'Tỷ số đã chọn':None,'Cấp chính xác đã chọn':None,'Công suất VA đã chọn':None},
   'nhan_dien_ai':{'loai_thiet_bi_code':'CT','cac_ma_dong_san_pham':[family],'measurement_function':'current','fabrication_ready':False},
   'tu_khoa_tim_kiem':['ABB',family,'Biến dòng','Current transformer',RANGES[family]+'/5A'],
   'nguon_tham_khao':[TECH,evidence['source_url']],'cad_don':[],'cac_hinh_cad':[],
   'muc_do_xac_nhan':'Hình học nguồn ABB; dải dòng là thông tin họ thiết bị, chưa chọn mã điện cụ thể.',
   'auto_select':False,'needs_review':True,
   'quy_tac_dung_chung_cad':{'relationship':'one_geometry_many_electrical_variants','ratio_from_cad':False,'requirements':['Đúng họ, loại lõi và cửa sổ luồn cáp/thanh cái','Đúng tỷ số và đầu vào 1A/5A của đồng hồ','Đối chiếu cấp chính xác, VA và tải dây thứ cấp']}}
  for code,label,window in windows:
   x0,y0,x1,y1=window
   entities=[e for e,b in geometry if b.extmin.x>=x0 and b.extmax.x<=x1 and b.extmin.y>=y0 and b.extmax.y<=y1]
   if len(entities)<30:raise ValueError(f'Incomplete projection {family} {code}')
   if code=='WIRE':
    boxes=[bbox.extents([entity]) for entity in entities]
    parent=list(range(len(boxes)))
    def root(i):
     while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
     return i
    grid=collections.defaultdict(list)
    for i,box in enumerate(boxes):
     cells=[(x,y) for x in range(int(box.extmin.x//10),int(box.extmax.x//10)+1) for y in range(int(box.extmin.y//10),int(box.extmax.y//10)+1)]
     nearby=set(j for cell in cells for j in grid[cell])
     for j in nearby:
      other=boxes[j]
      if box.extmin.x<=other.extmax.x+.05 and box.extmax.x>=other.extmin.x-.05 and box.extmin.y<=other.extmax.y+.05 and box.extmax.y>=other.extmin.y-.05:
       parent[root(i)]=root(j)
     for cell in cells:grid[cell].append(i)
    components=collections.defaultdict(list)
    for i,entity in enumerate(entities):components[root(i)].append(entity)
    hull=max((bbox.extents(group) for group in components.values()),key=lambda b:b.size.x*b.size.y)
    entities=[entity for entity,box in zip(entities,boxes) if box.extmin.x>=hull.extmin.x-.05 and box.extmax.x<=hull.extmax.x+.05]
   bounds=bbox.extents(entities)
   target=ezdxf.new('R2010');target.units=4
   importer=Importer(doc,target);importer.import_entities(entities);importer.finalize()
   transform=Matrix44.chain(Matrix44.translate(-bounds.extmin.x,-bounds.extmin.y,0),Matrix44.scale(1/scale))
   for entity in target.modelspace():entity.transform(transform);entity.dxf.color=7
   identity=f'ABB-OFFICIAL-{family}-{code}'
   destination=profile_path.parent/'CadDon'/identity;destination.mkdir(parents=True,exist_ok=True)
   output=destination/'ban_ve.dxf';target.saveas(output)
   backend=svg.SVGBackend();Frontend(RenderContext(target),backend).draw_layout(target.modelspace(),finalize=True)
   (destination/'xem_truoc.svg').write_text(backend.get_string(layout.Page(0,0,layout.Units.mm)),encoding='utf8')
   matplotlib.qsave(target.modelspace(),str(destination/'preview.png'),dpi=90)
   size=bbox.extents(target.modelspace()).size
   verification={'source_url':evidence['source_url'],'document_id':uid,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
    'source_package_sha256':evidence['sha256'],'coordinate_scale_to_mm':1/scale,'dimension_scale_samples':dict((str(k),v) for k,v in counts.items()),
    'extraction_window':window,'width_mm':size.x,'height_mm':size.y,'entity_count':len(target.modelspace()),
    'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'geometry_status':'supplier_reference','ordering_code_verified':False}
   (destination/'evidence.json').write_text(json.dumps(verification,indent=2),encoding='utf8')
   (destination/'thong_tin_cad_chen.json').write_text(json.dumps({'hinh_hoc_lap_dat':{'don_vi':'mm','bao_hinh_mm':{'min_x':0,'min_y':0,'max_x':size.x,'max_y':size.y}},'evidence':verification},indent=2),encoding='utf8')
   profile['cad_don'].append({'id_hinh_goc':identity,'huong_nhin':label,'nhan_hien_thi':f'ABB · CT · {family} · {label}',
    'duong_dan':output.relative_to(profile_path.parent).as_posix(),'bien_the_cad':'abb_official_ct1m_20261020','unit_verification':verification,
    'bo_tri_trong_tu':{'cho_phep_chen':code!='ISO','huong_dan':'Mặt xuyên dây nhìn dọc cáp/thanh cái; đối chiếu tư thế lắp và kích thước cửa sổ.'}})
   profile['cac_hinh_cad'].append(identity)
   report.append({'family':family,'view':code,'path':destination.relative_to(ROOT).as_posix(),**verification})
  profile['cad_chen_tu']={k:profile['cad_don'][0][k] for k in ['id_hinh_goc','huong_nhin','duong_dan']}
  profile_path.write_text(json.dumps(profile,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
  print(family,len(profile['cad_don']),flush=True)
 (ROOT.parents[1]/'docs/abb-ct-faces-2026-10-20.json').write_text(json.dumps(report,indent=2),encoding='utf8')
 print('Published source profiles; equipment index sync pending')

if __name__=='__main__':main()
