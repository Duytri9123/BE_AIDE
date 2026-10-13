"""Remove internal dimension debris and matching horizontal support crosspieces."""
import ast,json,logging,shutil
import ezdxf
from extract_project_helpers import ROOT,OUT,save,inside,bounds
tree=ast.parse((ROOT/'BE_AIDE/scripts/restore_complete_e_side_geometry.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom,ast.FunctionDef))],type_ignores=[]),'helpers','exec'))
logging.getLogger('ezdxf').setLevel(logging.ERROR)
data=json.loads((OUT/'catalog.json').read_text(encoding='utf-8'));report=[]
backup=ROOT/'BE_AIDE/tmp/e_side_annotation_cleanup_backup'
for r in data['shells']:
 folder=OUT/'Mau'/r['id'];depth=r.get('dimensions_mm',{}).get('depth');v=[f['source_bounds'] for f in r['faces'] if f.get('source_bounds') and f.get('kind') in ('outer_door','inner_door','mounting_plate','side','front','inner_side')]
 if not depth or not v:continue
 top=max(b[3] for b in v);bottom=min(b[1] for b in v);regions=[]
 for f in r['faces']:
  if 'E-SIDE' not in f['source_label'].upper():continue
  b=f.get('source_bounds');x=f['label_position_clean'][0]
  regions.append((b[0]+30,b[1]+100,b[2]-30,b[3]-100) if b else (x-depth/2+30,bottom+100,x+depth/2-30,top-100))
 if not regions:continue
 changes={}
 for fn in ('ban_ve.dxf','ban_ve_co_khung_goc.dxf'):
  doc=ezdxf.readfile(folder/fn);lines=[(e,bounds(e)) for e in doc.modelspace().query('LINE')];paired=set()
  for e,b in lines:
   if not b or not any(inside(b,q) for q in regions) or b[3]-b[1]>.01 or b[2]-b[0]<depth*.6:continue
   for q,c in lines:
    if c and q is not e and e.dxf.color==q.dxf.color and abs(c[3]-c[1])<.01 and abs(c[0]-b[0])<.01 and abs(c[2]-b[2])<.01 and .9<abs(c[1]-b[1])<2.1:paired.update((e.dxf.handle,q.dxf.handle))
  removed=[]
  for e in list(doc.modelspace()):
   b=bounds(e);reason=None
   if not b or not any(inside(b,q) for q in regions):continue
   if e.dxftype()=='POINT':reason='orphan_reference_point_inside_clean_E_SIDE'
   elif e.dxftype()=='INSERT' and e.dxf.name.startswith('_Open'):reason='internal_dimension_arrow_of_removed_layout'
   elif e.dxf.handle in paired:reason='paired_thin_horizontal_support_crosspiece'
   elif e.dxftype()=='LWPOLYLINE' and b[2]-b[0]>depth*.65 and 10<b[3]-b[1]<60:
    pts=list(e.get_points('xy'));ys=sorted({round(p[1],3) for p in pts})
    if len(pts)>=6 and any(.9<ys[i+1]-ys[i]<2.1 for i in range(len(ys)-1)):reason='thin_folded_horizontal_support_crosspiece'
   if reason:
    removed.append({'handle':e.dxf.handle,'type':e.dxftype(),'bounds':b,'reason':reason});doc.modelspace().delete_entity(e)
  if removed:
   dest=backup/r['id']/fn;dest.parent.mkdir(parents=True,exist_ok=True)
   if not dest.exists():shutil.copy2(folder/fn,dest)
   doc.saveas(folder/fn)
   if fn=='ban_ve_co_khung_goc.dxf':render(doc,folder/'xem_truoc.svg')
  changes[fn]=removed
 report.append({'id':r['id'],'view_count':len(regions),'removed':changes,'vertical_shell_and_hardware_unchanged':True,'remaining_semantic_review_required':True})
save(OUT/'kiem_tra_net_do_va_do_E_SIDE_toan_bo.json',report)
print('Checked',len(report),'forms;',sum(r['view_count'] for r in report),'views; removed',sum(len(r['removed']['ban_ve.dxf']) for r in report))
