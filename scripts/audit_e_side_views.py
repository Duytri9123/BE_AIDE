"""Preliminary perimeter audit; run restore_complete_e_side_geometry.py afterward."""
import json,re,logging,os
from collections import defaultdict
import ezdxf
from ezdxf import bbox
from ezdxf.addons import Importer
from ezdxf.addons.drawing import Frontend,RenderContext
from ezdxf.addons.drawing.config import Configuration
from ezdxf.addons.drawing.svg import SVGBackend
from ezdxf.addons.drawing.layout import Page,Margins
from ezdxf.addons.drawing.properties import LayoutProperties
from extract_project_helpers import ROOT,OUT,save,inside,bounds
logging.getLogger('ezdxf').setLevel(logging.ERROR)
EXCLUSIONS={'0785608caf266cc1-107DB6E':{'block_names':['Ổ CẮM CN'],'source_handles':['107DB65','107DB66','107DB67'],'reason':'User explicitly selected this form only; remove the three industrial sockets on SIDE VIEW.'}}
save(OUT/'form_source_exclusions.json',EXCLUSIONS)
def render(doc,p):
 backend=SVGBackend();Frontend(RenderContext(doc),backend,config=Configuration()).draw_layout(doc.modelspace(),layout_properties=LayoutProperties('Model','#212830','#ffffff',units=4,dark_background=True));svg=backend.get_string(Page(0,0,margins=Margins(10,10,10,10)));svg=re.sub(r'stroke-width: ([0-9.]+)',lambda m:'stroke-width: '+str(max(1000,float(m[1]))),svg);p.write_text(svg,encoding='utf-8')
def key(e,b):return (e.dxftype(),tuple(round(v,2) for v in b))
d=json.loads((OUT/'catalog.json').read_text(encoding='utf-8'));groups=defaultdict(list);report=[]
for r in d['shells']:groups[r['original_dxf']].append(r)
for path,rows in groups.items():
 if os.environ.get('ESIDE_ZERO_ONLY'):
  rows=[r for r in rows if r.get('e_side_review',{}).get('view_count') and not r['e_side_review'].get('source_perimeter_candidates')]
  if not rows:continue
 src=ezdxf.readfile(ROOT/path);primitives=[(e,bounds(e)) for e in src.modelspace().query('LINE LWPOLYLINE POLYLINE ARC')]
 for r in rows:
  faces=[f for f in r.get('faces',[]) if f['source_label'].upper().replace('-',' ').strip()=='E SIDE VIEW'];vertical=[f['source_bounds'] for f in r.get('faces',[]) if f.get('source_bounds') and f.get('kind') in ('inner_door','outer_door','mounting_plate','side') and f['source_bounds'][3]-f['source_bounds'][1]>=100];candidates=[]
  if faces and vertical:
   top=max(b[3] for b in vertical);bottom=min(b[1] for b in vertical);depth=r.get('dimensions_mm',{}).get('depth')
   if depth:
    for f in faces:
     label=src.entitydb.get(f.get('source_label_handle'))
     if label is None:continue
     x=label.dxf.insert.x;region=(x-depth/2-60,bottom-50,x+depth/2+60,top+50)
     for e,b in primitives:
      if not b or not inside(b,region):continue
      width,height=b[2]-b[0],b[3]-b[1]
      near_edge=min(abs(b[0]-(x-depth/2)),abs(b[2]-(x+depth/2)))<=45
      if (height>.65*(top-bottom) and (near_edge or width>.7*depth)) or (width>.7*depth and min(abs(b[1]-top),abs(b[3]-bottom))<50):candidates.append(e)
  folder=OUT/'Mau'/r['id'];counts={};changed=False
  for filename in ('ban_ve.dxf','ban_ve_co_khung_goc.dxf'):
   doc=ezdxf.readfile(folder/filename);removed=[]
   for e in list(doc.modelspace().query('INSERT')):
    if any(n.lower() in e.dxf.name.lower() for n in EXCLUSIONS.get(r['id'],{}).get('block_names',[])):removed.append(e.dxf.handle);doc.modelspace().delete_entity(e)
   existing={key(e,b) for e in doc.modelspace() if (b:=bounds(e))};missing=[]
   for e in candidates:
    b=bounds(e);k=key(e,b)
    if k not in existing:missing.append(e);existing.add(k)
   if missing:imp=Importer(src,doc);imp.import_entities(missing);imp.finalize()
   if removed or missing:
    doc.saveas(folder/filename);changed=True
    if filename=='ban_ve_co_khung_goc.dxf':render(doc,folder/'xem_truoc.svg')
   counts[filename]={'restored_source_perimeter_entities':len(missing),'removed_confirmed_device_blocks':len(removed)}
  r['e_side_review']={'view_count':len(faces),'source_perimeter_candidates':len(candidates),'changes':counts,'basis':'Original source edge contours; no synthesized lines, mirror or uniform stretch.','requires_visual_review':bool(faces)}
  if r['id'] in EXCLUSIONS:
   r['confirmed_device_exclusions']=EXCLUSIONS[r['id']]
   r['side_view_source_blocks']=[entry for entry in r.get('side_view_source_blocks',[]) if entry.get('source_handle') not in EXCLUSIONS[r['id']]['source_handles']]
  save(folder/'thong_tin.json',r);report.append({'id':r['id'],**r['e_side_review']})
 save(OUT/'catalog.json',d);save(OUT/'kiem_tra_e_side_view.json',report);print('E-SIDE audited',len(report),flush=True)
print('Audited',len(report),'forms;',sum(r['view_count'] for r in report),'E-SIDE views')
save(OUT/'kiem_tra_e_side_view.json',[{'id':r['id'],**r.get('e_side_review',{})} for r in d['shells']])
