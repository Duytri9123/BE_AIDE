"""Remove paired busbar routes and support dimensions while retaining source shell."""
import ast,json,logging,re,math,os
from collections import defaultdict
import ezdxf
from ezdxf import dynblkhelper
from ezdxf.addons import Importer
from extract_project_helpers import ROOT,OUT,save,inside,bounds
from project_form_rejections import norm
logging.getLogger('ezdxf').setLevel(logging.ERROR)
tree=ast.parse((ROOT/'BE_AIDE/scripts/restore_complete_e_side_geometry.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom,ast.FunctionDef))],type_ignores=[]),'helpers','exec'))
data=json.loads((OUT/'catalog.json').read_text(encoding='utf-8'));groups=defaultdict(list);report=[]
for r in data['shells']:groups[r['original_dxf']].append(r)
for path,rows in groups.items():
 src=ezdxf.readfile(ROOT/path);prims=[] if os.environ.get('FORM_DIMENSIONS_ONLY') else [(e,bounds(e)) for e in src.modelspace().query('LINE LWPOLYLINE POLYLINE ARC CIRCLE ELLIPSE SPLINE')];dims=list(src.modelspace().query('DIMENSION'))
 for r in rows:
  folder=OUT/'Mau'/r['id'];vertical=[f['source_bounds'] for f in r['faces'] if f.get('source_bounds') and f.get('kind') in ('outer_door','inner_door','mounting_plate','side')];depth=r.get('dimensions_mm',{}).get('depth');regions=[];remove=[];dimparts=[]
  if vertical and depth:
   top=max(b[3] for b in vertical);bottom=min(b[1] for b in vertical)
   for f in r['faces']:
    if 'E-SIDE' in f['source_label'].upper():
     x=f['label_position_clean'][0];regions.append((x-depth/2,bottom,x+depth/2,top))
  for region in regions:
   # Busbar routes occur as parallel open paths, with 3/4 bends and a 5/8 mm offset.
   candidates=[]
   for e,b in prims:
    if e.dxftype()!='LWPOLYLINE' or not b or not inside(b,(region[0]+35,region[1]+75,region[2]-35,region[3]-75)):continue
    pts=list(e.get_points('xy'));closed=e.closed or math.dist(pts[0],pts[-1])<.01
    if not closed and 3<=len(pts)<=5:candidates.append((e,b,pts))
    if e.dxf.color==1 and len(pts)>=6 and b[2]-b[0]>depth*.65 and b[3]-b[1]<80:remove.append(e)
   for e,b,pts in candidates:
    for q,c,qpts in candidates:
     if q is e or len(pts)!=len(qpts) or e.dxf.color!=q.dxf.color:continue
     gaps=[abs(b[i]-c[i]) for i in range(4)]
     if max(gaps)<=12 and max(gaps)>=3 and b[3]-b[1]>25:remove.append(e);break
   for e in dims:
    a=e.dxf.get('defpoint2');b=e.dxf.get('defpoint3')
    if a is None or b is None:continue
    # Internal horizontal offsets of equipment/supports; overall enclosure sizes stay.
    if (abs(a.y-b.y)<.1 or (e.dxf.dimtype & 7)==0 and abs(e.dxf.get('angle',0)%180)<.1) and 1<abs(a.x-b.x)<depth*.8 and region[0]-1<=min(a.x,b.x) and max(a.x,b.x)<=region[2]+35 and region[1]+75<a.y<region[3]-75:
     try:dimparts.extend(e.virtual_entities())
     except Exception:pass
  restore=[]
  old_audit=r.get('internal_route_cleanup',{})
  if os.environ.get('FORM_DIMENSIONS_ONLY') and vertical and depth:
   for handle in old_audit.get('paired_route_source_handles',[]):
    e=src.entitydb.get(handle);b=bounds(e) if e else None
    if b and b[2]-b[0]>depth*.7 and b[3]-b[1]<80 and (abs(b[1]-bottom)<75 or abs(b[3]-top)<75):restore.append(e)
  keys={signature(e) for e in remove+dimparts if signature(e)};textkeys={(e.dxf.text,round(e.dxf.insert.x,4),round(e.dxf.insert.y,4)) for e in dimparts if e.dxftype()=='TEXT'};changes={}
  for filename in ('ban_ve.dxf','ban_ve_co_khung_goc.dxf'):
   doc=ezdxf.readfile(folder/filename);deleted=0
   sheet=json.loads((folder/'bo_tri_goc.json').read_text(encoding='utf-8'))['source_sheet_bounds']
   positions={(round(e.dxf.insert.x,4),round(e.dxf.insert.y,4)) for e in doc.modelspace().query('INSERT')}
   lift=[]
   for e in src.modelspace().query('INSERT'):
    definition=dynblkhelper.get_dynamic_block_definition(e);name=norm(definition.name if definition else e.dxf.name)
    if 'LIFTING' in name and sheet[0]<=e.dxf.insert.x<=sheet[2] and sheet[1]<=e.dxf.insert.y<=sheet[3] and (round(e.dxf.insert.x,4),round(e.dxf.insert.y,4)) not in positions:lift.append(e)
   existing={signature(e) for e in doc.modelspace() if signature(e)}
   restorations=[e for e in restore if signature(e) not in existing]
   if lift or restorations:
    imp=Importer(src,doc);imp.import_entities(lift+restorations);imp.finalize()
   for e in list(doc.modelspace()):
    drop=signature(e) in keys if signature(e) else False
    if e.dxftype()=='INSERT' and e.dxf.name.startswith('_Open'):
     drop=drop or any(a+30<e.dxf.insert.x<c-30 and b+75<e.dxf.insert.y<z-75 for a,b,c,z in regions)
    if e.dxftype()=='TEXT':drop=drop or (e.dxf.text,round(e.dxf.insert.x,4),round(e.dxf.insert.y,4)) in textkeys
    if e.dxftype()=='INSERT':
     definition=dynblkhelper.get_dynamic_block_definition(e);name=norm(definition.name if definition else e.dxf.name)
     drop=drop or bool(re.search(r'THANH U|THANH DOC|XA SAU|SU KEP|SU PHIP|CAU TIEP DIA|MCCB|MCB|ACB|RCBO|RCCB|CONTACTOR|ATS |ABN|EZC|CAU CHI|PNE.BAR|VTPK|COS [0-9]|DAU.DOC',name))
    if drop:doc.modelspace().delete_entity(e);deleted+=1
   doc.saveas(folder/filename)
   if filename=='ban_ve_co_khung_goc.dxf' and (deleted or lift or restorations):render(doc,folder/'xem_truoc.svg')
   changes[filename]=deleted
  audit={'id':r['id'],'paired_route_source_handles':old_audit.get('paired_route_source_handles',[]) if os.environ.get('FORM_DIMENSIONS_ONLY') else sorted({e.dxf.handle for e in remove}),'removed':changes,'requires_visual_review':True};r['internal_route_cleanup']=audit;save(folder/'thong_tin.json',r);report.append(audit)
 save(OUT/'catalog.json',data);save(OUT/'kiem_tra_dong_va_duong_do_do.json',report);print('Route cleanup',len(report),flush=True)
