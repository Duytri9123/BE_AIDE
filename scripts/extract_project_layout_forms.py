"""Extract source enclosure contours + exact lamp geometry; retain placement evidence separately."""
raise SystemExit('Không dùng bộ tách chỉ giữ đường bao cũ. Dùng rebuild_tudien_clean_forms.py, giữ cơ khí và làm sạch thiết bị điện.')
import json,re,unicodedata,hashlib,logging,time
from pathlib import Path
import ezdxf
from project_form_rejections import rejection,CACHE
from ezdxf import bbox,dynblkhelper,transform
from ezdxf.addons import Importer
from ezdxf.addons.drawing import Frontend,RenderContext
from ezdxf.addons.drawing.config import Configuration,ColorPolicy
from ezdxf.addons.drawing.svg import SVGBackend
from ezdxf.addons.drawing.layout import Page
from ezdxf.addons.drawing.properties import LayoutProperties
ROOT=Path(__file__).resolve().parents[2];BASE=ROOT/'BE_AIDE/tmp/project_cabinet_sources';OUT=ROOT/'BE_AIDE/data/CatalogTB/Form tủ'
logging.getLogger('ezdxf').setLevel(logging.ERROR)
def norm(s):return ''.join(c for c in unicodedata.normalize('NFD',s.upper().replace('Đ','D')) if not unicodedata.combining(c))
def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
def bounds(e):
 try:
  b=bbox.extents([e],fast=True)
  return (b.extmin.x,b.extmin.y,b.extmax.x,b.extmax.y) if b.has_data else None
 except:return None

def inside(b,r):return b and b[0]>=r[0]-.1 and b[1]>=r[1]-.1 and b[2]<=r[2]+.1 and b[3]<=r[3]+.1
LAMP=re.compile(r'LIGHT|PILOT|DEN BAO|^DEN (DO|VANG|XANH)|^DCHINT')
DEVICE=re.compile(r'MCCB|MCB|ACB|BKN|ABN|ABS|RCBO|RCCB|CONTACTOR|MC[- _]?[0-9]|PLC|S7-|AMPERE|VOLTMET|DONG HO|METER|SELECTOR|BUTTON|ATS|CAU CHI|FUSE|POWER|S8FS')
SUPPORT=re.compile(r'(^|[^A-Z])DO([^A-Z]|$)|THANH (U|DOC|NGANG|GA)|CROSS.?MEMBER|SUPPORT RAIL|^XA ')
rejected=json.loads((OUT/'form_loai_bo.json').read_text(encoding='utf-8')) if (OUT/'form_loai_bo.json').exists() else []
rows=json.loads((OUT/'catalog.json').read_text(encoding='utf-8')).get('shells',[])
review=json.loads((OUT/'kiem_tra_nguon.json').read_text(encoding='utf-8')) if (OUT/'kiem_tra_nguon.json').exists() else []
done={x['source_id'] for x in review}
support_list=json.loads((BASE/'support_candidates.json').read_text(encoding='utf-8')) if (BASE/'support_candidates.json').exists() else []
supports={x['source']['id']+'-'+x['handle']:x for x in support_list}
placements=json.loads((OUT/'bo_tri_thiet_bi_dong.json').read_text(encoding='utf-8')) if (OUT/'bo_tri_thiet_bi_dong.json').exists() else []
while True:
 manifest=json.loads((BASE/'manifest.json').read_text(encoding='utf-8')) if (BASE/'manifest.json').exists() else []
 for source in manifest:
  sid=source['id']
  if sid in done or source['status']!='exported':continue
  done.add(sid);doc=ezdxf.readfile(ROOT/source['dxf']);CACHE.clear();model=doc.modelspace();inserts=[]
  for e in model.query('INSERT'):
   parent=dynblkhelper.get_dynamic_block_definition(e);name=parent.name if parent else e.dxf.name;n=norm(name);typ='lock' if re.search(r'KHOA|LOCK|LATCH|CAM LOCK',n) else 'lamp' if LAMP.search(n) else 'device' if DEVICE.search(n) else 'frame' if 'KHUNG' in n or 'BANG THONG SO' in n else 'support' if ('ĐỐ' in name.upper() or re.search(r'THANH (U|DOC|NGANG|GA)|CROSS.?MEMBER|SUPPORT RAIL|^XA ',n)) else 'unknown'
   if typ=='unknown':continue
   b=bounds(e)
   if b:inserts.append((e,name,typ,b))
   if typ=='support':supports.setdefault(sid+'-'+e.dxf.name,{'source':source,'handle':e.dxf.handle,'name':name,'bounds':b})
  rects=[]
  for e in model.query('LWPOLYLINE'):
   if not e.closed:continue
   pts=list(e.get_points('xy'));xs={round(p[0],3) for p in pts};ys={round(p[1],3) for p in pts}
   if len(xs)!=2 or len(ys)!=2 or len(pts)!=4:continue
   r=(min(xs),min(ys),max(xs),max(ys));w=r[2]-r[0];h=r[3]-r[1]
   if not (200<=w<=3000 and 300<=h<=3000):continue
   contained=[v for v in inserts if inside(v[3],r)]
   devices=[v for v in contained if v[2] in ('device','lamp')]
   if not devices or any(v[2]=='frame' for v in contained):continue
   rects.append((e,r,contained))
  chosen=[x for x in rects if not any(y is not x and inside(x[1],y[1]) and (y[1][2]-y[1][0])*(y[1][3]-y[1][1])>(x[1][2]-x[1][0])*(x[1][3]-x[1][1])+1 for y in rects)]
  for e,r,contained in chosen:
   reason=rejection(doc,r)
   if reason:
    rejected.append({'source_id':sid,'source_file':source['source_file'],'source_handle':e.dxf.handle,'reason':reason});continue
   key=sid+'-'+e.dxf.handle;folder=OUT/'Mau'/key;folder.mkdir(parents=True,exist_ok=True)
   lamps=[v for v in contained if v[2]=='lamp'];original_lamp_handles=[v[0].dxf.handle for v in lamps]
   locks=[v for v in contained if v[2]=='lock']; keep=[e,*[v[0] for v in lamps],*[v[0] for v in locks]]
   for circle in model.query('CIRCLE'):
    if circle.dxf.color in (1,2,3) and 7<=circle.dxf.radius<=18 and inside(bounds(circle),r):keep.append(circle);original_lamp_handles.append(circle.dxf.handle)
   clean=ezdxf.new('R2018');clean.units=4;imp=Importer(doc,clean);imp.import_entities(keep);imp.finalize()
   # Strip annotation recursively; retain lamp geometry and source positions exactly.
   for layout in [clean.modelspace(),*list(clean.blocks)]:
    for entity in list(layout):
     if entity.dxftype() in ('TEXT','MTEXT','ATTRIB','ATTDEF','DIMENSION','LEADER','MULTILEADER'):layout.delete_entity(entity)
   transform.translate(clean.modelspace(),(-(r[0]+r[2])/2,-(r[1]+r[3])/2,0));clean.saveas(folder/'ban_ve.dxf')
   be=SVGBackend();Frontend(RenderContext(clean),be,config=Configuration(color_policy=ColorPolicy.BLACK)).draw_layout(clean.modelspace(),layout_properties=LayoutProperties('Model','#ffffff','#000000',units=4,dark_background=False));svg=be.get_string(Page(0,0));svg=re.sub(r'stroke-width: ([0-9.]+)',lambda m:'stroke-width: '+str(max(1000,float(m[1]))),svg);(folder/'xem_truoc.svg').write_text(svg,encoding='utf-8')
   w=round(r[2]-r[0],3);h=round(r[3]-r[1],3)
   info={'id':key,'name':f'Mẫu bố trí {h:g}×{w:g} mm','source_file':source['source_file'],'source_id':sid,'source_handle':e.dxf.handle,'source_rectangle':list(r),'dimensions_mm':{'height':h,'width':w,'depth':None},'kind':'project','preview':f'Mau/{key}/xem_truoc.svg','source_dxf':f'Mau/{key}/ban_ve.dxf','original_dxf':source['dxf'],'lamp_handles_preserved':original_lamp_handles,'lock_handles_preserved':[v[0].dxf.handle for v in locks],'lamp_count':len(original_lamp_handles),'source_units_code':doc.units,'auto_select':False,'verified_form':None,'cad_scope':'single_layout_contour_with_source_lamps','notes':['Giữ đường bao mặt từ nguồn và đèn, khóa đã nhận diện; đã bỏ thiết bị điện còn lại và chữ.','Chưa xác nhận đây là mặt cánh/tấm lắp nào; chưa có chiều sâu và chi tiết vỏ.','Các chi tiết cơ khí bên trong không tự đưa vào mẫu này.']}
   save(folder/'thong_tin.json',info);rows.append(info)
   placements.append({'form_id':key,'source':source['source_file'],'devices_removed':[{'name':v[1],'source_handle':v[0].dxf.handle,'bounds':list(v[3])} for v in contained if v[2]=='device'],'lamps_kept':original_lamp_handles,'copper_layout_verified':False,'support_layout_verified':False})
  review.append({'source':source['source_file'],'source_id':sid,'rectangles_candidates':len(rects),'forms_selected':len(chosen),'lamp_blocks':sum(v[2]=='lamp' for v in inserts),'device_blocks':sum(v[2]=='device' for v in inserts),'status':'needs_view_identity_review'})
  save(OUT/'form_loai_bo.json',rejected);save(OUT/'catalog.json',{'shells':rows,'separation_forms':[],'source_directory':'Tudien','rules':['Mẫu từ đường bao mặt dự án; giữ đèn và khóa, bỏ thiết bị/chữ; phải xác nhận mặt trước dùng.']});save(OUT/'kiem_tra_nguon.json',review);save(OUT/'bo_tri_thiet_bi_dong.json',placements);save(BASE/'support_candidates.json',list(supports.values()));print(source['source_file'],len(chosen),'forms',flush=True)
 if (BASE/'conversion_complete.json').exists():break
 time.sleep(3)
print('Extracted',len(rows),'forms from',len(done),'unique sources')

