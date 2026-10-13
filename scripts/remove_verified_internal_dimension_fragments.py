"""Remove remaining fragments only when matching original internal DIMENSION geometry."""
import ast,json,logging
from collections import defaultdict
import ezdxf
from extract_project_helpers import ROOT,OUT,save,inside,bounds
tree=ast.parse((ROOT/'BE_AIDE/scripts/restore_complete_e_side_geometry.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom,ast.FunctionDef))],type_ignores=[]),'helpers','exec'))
logging.getLogger('ezdxf').setLevel(logging.ERROR)
data=json.loads((OUT/'catalog.json').read_text(encoding='utf-8'));groups=defaultdict(list);report=[]
for r in data['shells']:groups[r['original_dxf']].append(r)
for path,rows in groups.items():
 src=ezdxf.readfile(ROOT/path);dimensions=list(src.modelspace().query('DIMENSION'))
 for r in rows:
  depth=r.get('dimensions_mm',{}).get('depth');v=[f['source_bounds'] for f in r['faces'] if f.get('source_bounds') and f.get('kind') in ('outer_door','inner_door','mounting_plate','side','front','inner_side')];regions=[]
  if depth and v:
   for f in r['faces']:
    if 'E-SIDE' not in f['source_label'].upper():continue
    b=f.get('source_bounds');x=f['label_position_clean'][0]
    regions.append((b[0]+25,b[1]+80,b[2]-25,b[3]-80) if b else (x-depth/2+25,min(b[1] for b in v)+80,x+depth/2-25,max(b[3] for b in v)-80))
  keys=set();source_handles=[]
  for e in dimensions:
   a=e.dxf.get('defpoint2');b=e.dxf.get('defpoint3')
   if a is None or b is None or not any(q[0]<=a.x<=q[2] and q[1]<=a.y<=q[3] and q[0]<=b.x<=q[2] and q[1]<=b.y<=q[3] for q in regions):continue
   source_handles.append(e.dxf.handle)
   try:
    for part in e.virtual_entities():
     ext=bounds(part)
     if ext and any(inside(ext,q) for q in regions) and signature(part):keys.add(signature(part))
   except Exception:pass
  changes={};folder=OUT/'Mau'/r['id']
  for fn in ('ban_ve.dxf','ban_ve_co_khung_goc.dxf'):
   doc=ezdxf.readfile(folder/fn);removed=[]
   for e in list(doc.modelspace()):
    if signature(e) in keys:removed.append(e.dxf.handle);doc.modelspace().delete_entity(e)
   if removed:
    doc.saveas(folder/fn)
    if fn=='ban_ve_co_khung_goc.dxf':render(doc,folder/'xem_truoc.svg')
   changes[fn]=removed
  report.append({'id':r['id'],'source_internal_dimension_handles':source_handles,'removed_exact_geometry_matches':changes})
 save(OUT/'kiem_tra_net_do_noi_bo_theo_nguon.json',report);print('Source dimension audit',len(report),flush=True)
print('Removed verified dimension fragments',sum(len(r['removed_exact_geometry_matches']['ban_ve.dxf']) for r in report))
