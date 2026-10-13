import json,re,logging
from collections import defaultdict
import ezdxf
from ezdxf import bbox,dynblkhelper
from extract_project_helpers import ROOT,OUT,save,render,inside
from project_form_rejections import norm
logging.getLogger('ezdxf').setLevel(logging.ERROR)
d=json.loads((OUT/'catalog.json').read_text(encoding='utf-8'));groups=defaultdict(list)
for row in d['shells']:groups[row['original_dxf']].append(row)
def rectangles(model,region=None):
 result=[]
 for e in model.query('LWPOLYLINE'):
  pts=list(e.get_points('xy'));xs={round(p[0],3) for p in pts};ys={round(p[1],3) for p in pts}
  if not e.closed or len(pts)!=4 or len(xs)!=2 or len(ys)!=2:continue
  r=(min(xs),min(ys),max(xs),max(ys));w=r[2]-r[0];h=r[3]-r[1]
  if 200<=w<=3000 and 300<=h<=3000 and (region is None or inside(r,region)):result.append((r,round(w,1),round(h,1)))
 return sorted(result,key=lambda v:(v[0][0],v[0][1]))
def box(e):
 b=bbox.extents([e],fast=True)
 return (b.extmin.x,b.extmin.y,b.extmax.x,b.extmax.y) if b.has_data else None
for path,rows in groups.items():
 original=ezdxf.readfile(ROOT/path);source_regions=rectangles(original.modelspace());targets=[];locks=[]
 for e in original.modelspace().query('INSERT'):
  parent=dynblkhelper.get_dynamic_block_definition(e);n=norm(parent.name if parent else e.dxf.name)
  if re.search(r'ISOLATE BKD|SU KEP|SU DO|CAU TIEP DIA|END BRAKET',n):
   b=box(e)
   if b:targets.append((b,e.dxf.handle,n))
  elif re.search(r'KHOA|LOCK|MS406|AB301|^HL\d',n):
   b=box(e)
   if b:locks.append(b)
 for row in rows:
  a=json.loads((OUT/row['layout_analysis_json']).read_text(encoding='utf-8'));sheet=a['source_sheet_bounds'];src=[v for v in source_regions if inside(v[0],sheet)]
  folder=OUT/'Mau'/row['id'];doc=ezdxf.readfile(folder/'ban_ve.dxf');dst=rectangles(doc.modelspace());matches=[(s,t) for s in src for t in dst if s[1:]==t[1:]]
  if not matches:row['cleaning']['electrical_accessory_review']='no_reliable_alignment';continue
  # Same source rectangular contour provides an exact translation anchor.
  s,t=min(matches,key=lambda v:(v[0][0][0],v[1][0][0]));dx=t[0][0]-s[0][0];dy=t[0][1]-s[0][1]
  shift=lambda r:(r[0]+dx,r[1]+dy,r[2]+dx,r[3]+dy)
  areas=[(shift(r),handle,n) for r,handle,n in targets if inside(r,sheet)];protected=[shift(r) for r in locks if inside(r,sheet)];removed=0
  # Equipment support assemblies include exploded conductors between the supports.
  # Combine only supports belonging to the same source face, keeping its border intact.
  extra=[]
  for face,_,_ in dst:
   members=[r for r,_,_ in areas if inside(r,face)]
   if not members:continue
   hull=(max(face[0]+30,min(r[0] for r in members)-80),max(face[1]+30,min(r[1] for r in members)-80),min(face[2]-30,max(r[2] for r in members)+80),min(face[3]-30,max(r[3] for r in members)+80))
   extra.append((hull,'source_face_accessory_region','assembly_region'))
  areas.extend(extra)
  for e in list(doc.modelspace()):
   b=box(e)
   if b is None and e.dxftype()=='INSERT':p=e.dxf.insert;b=(p.x,p.y,p.x,p.y)
   if not b or any(inside(b,r) for r in protected):continue
   if any(inside(b,r) for r,_,_ in areas):doc.modelspace().delete_entity(e);removed+=1
  if removed:doc.saveas(folder/'ban_ve.dxf');render(doc,folder/'xem_truoc.svg')
  row['cleaning']['electrical_accessory_geometry_removed']=removed;row['cleaning']['source_accessory_handles_removed']=[h for _,h,_ in areas];row['cleaning']['accessory_alignment_translation']=[dx,dy]
  save(folder/'thong_tin.json',row)
 save(OUT/'catalog.json',d);print(path,'accessories checked',flush=True)
print('Electrical accessories checked for',len(d['shells']),'sheets')
