"""Restore source E-SIDE primitives using actual geometry signatures, not bbox dedup."""
import json,re,logging
from collections import defaultdict
import ezdxf
from ezdxf.addons import Importer
from ezdxf.addons.drawing import Frontend,RenderContext
from ezdxf.addons.drawing.config import Configuration
from ezdxf.addons.drawing.svg import SVGBackend
from ezdxf.addons.drawing.layout import Page,Margins
from ezdxf.addons.drawing.properties import LayoutProperties
from extract_project_helpers import ROOT,OUT,save,inside,bounds
logging.getLogger('ezdxf').setLevel(logging.ERROR)
def xy(p):return (round(p[0],5),round(p[1],5))
def signature(e):
 t=e.dxftype();style=(e.dxf.layer,e.dxf.color,e.dxf.get('true_color',None),e.dxf.linetype)
 if t=='LINE':g=tuple(sorted([xy(e.dxf.start),xy(e.dxf.end)]))
 elif t=='LWPOLYLINE':g=(e.closed,tuple(tuple(round(v,5) for v in p) for p in e.get_points('xyseb')))
 elif t=='POLYLINE':g=(e.is_closed,tuple(xy(v.dxf.location) for v in e.vertices))
 elif t in ('CIRCLE','ARC'):g=(xy(e.dxf.center),round(e.dxf.radius,5),e.dxf.get('start_angle',0) if t=='ARC' else 0,e.dxf.get('end_angle',0) if t=='ARC' else 0)
 elif t=='ELLIPSE':g=(xy(e.dxf.center),xy(e.dxf.major_axis),e.dxf.ratio,e.dxf.start_param,e.dxf.end_param)
 elif t=='SPLINE':g=(e.dxf.degree,tuple(xy(p) for p in e.control_points),tuple(xy(p) for p in e.fit_points))
 elif t in ('SOLID','TRACE'):g=tuple(xy(e.dxf.get('vtx'+str(i))) for i in range(4))
 elif t in ('TEXT','MTEXT'):g=(e.dxf.text if t=='TEXT' else e.plain_text(),xy(e.dxf.insert))
 else:return None
 return (t,style,g)
def render(doc,p):
 b=SVGBackend();Frontend(RenderContext(doc),b,config=Configuration()).draw_layout(doc.modelspace(),layout_properties=LayoutProperties('Model','#212830','#ffffff',units=4,dark_background=True));svg=b.get_string(Page(0,0,margins=Margins(10,10,10,10)));svg=re.sub(r'stroke-width: ([0-9.]+)',lambda m:'stroke-width: '+str(max(1000,float(m[1]))),svg);p.write_text(svg,encoding='utf-8')
d=json.loads((OUT/'catalog.json').read_text(encoding='utf-8'));groups=defaultdict(list);report=[]
for r in d['shells']:groups[r['original_dxf']].append(r)
for path,rows in groups.items():
 src=ezdxf.readfile(ROOT/path);primitives=[(e,bounds(e)) for e in src.modelspace().query('LINE LWPOLYLINE POLYLINE ARC CIRCLE ELLIPSE SPLINE')]
 for r in rows:
  vertical=[f['source_bounds'] for f in r.get('faces',[]) if f.get('source_bounds') and f.get('kind') in ('inner_door','outer_door','mounting_plate','side')];faces=[f for f in r.get('faces',[]) if f['source_label'].upper().replace('-',' ').strip()=='E SIDE VIEW'];selected=[]
  depth=r.get('dimensions_mm',{}).get('depth')
  if vertical and depth:
   top=max(b[3] for b in vertical);bottom=min(b[1] for b in vertical)
   for f in faces:
    label=src.entitydb.get(f.get('source_label_handle'))
    if label is None:continue
    x=label.dxf.insert.x;region=(x-depth/2-60,bottom-50,x+depth/2+60,top+50)
    selected.extend(e for e,b in primitives if b and inside(b,region) and e.dxf.layer.lower()!='defpoints')
  changes={};folder=OUT/'Mau'/r['id']
  for filename in ('ban_ve.dxf','ban_ve_co_khung_goc.dxf'):
   doc=ezdxf.readfile(folder/filename);existing={signature(e):e for e in doc.modelspace() if signature(e) is not None};missing=[];visibility=0
   for e in selected:
    k=signature(e)
    if k not in existing:missing.append(e);existing[k]=e
    else:
     old=existing[k]
     if old.dxf.invisible and not e.dxf.invisible:old.dxf.invisible=0;visibility+=1
   if missing:imp=Importer(src,doc);imp.import_entities(missing);imp.finalize()
   after={signature(e) for e in doc.modelspace() if signature(e) is not None};assert all(signature(e) in after for e in selected)
   if missing or visibility:
    doc.saveas(folder/filename)
    if filename=='ban_ve_co_khung_goc.dxf':render(doc,folder/'xem_truoc.svg')
   changes[filename]={'restored_entities':len(missing),'visibility_corrected':visibility,'source_primitive_coverage_verified':True}
  r['e_side_geometry_review']={'view_count':len(faces),'source_primitives':len(selected),'source_handles':[e.dxf.handle for e in selected],'changes':changes,'method':'Complete source primitive geometry inside E-SIDE window; preserve inner folds and short segments. Actual coordinate signatures; no bbox-based dedup. Electrical INSERT blocks not imported.','requires_semantic_review':True}
  save(folder/'thong_tin.json',r);report.append({'id':r['id'],**r['e_side_geometry_review']})
 save(OUT/'catalog.json',d);save(OUT/'kiem_tra_day_du_net_e_side.json',report);print('Complete E-SIDE geometry',len(report),flush=True)
print('Verified',len(report),'forms;',sum(r['view_count'] for r in report),'E-SIDE views')
