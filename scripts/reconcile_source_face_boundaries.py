"""Reconcile source face perimeters and unlabelled lower mechanical views."""
import ast,json,logging,re,shutil
from collections import defaultdict
from pathlib import Path
import ezdxf
from ezdxf.addons import Importer
from ezdxf import dynblkhelper
from extract_project_helpers import ROOT,OUT,save,inside,bounds
tree=ast.parse((ROOT/'BE_AIDE/scripts/restore_complete_e_side_geometry.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom,ast.FunctionDef))],type_ignores=[]),'helpers','exec'))
logging.getLogger('ezdxf').setLevel(logging.ERROR)
data=json.loads((OUT/'catalog.json').read_text(encoding='utf-8'));groups=defaultdict(list);report=[]
backup=ROOT/'BE_AIDE/tmp/form_boundary_audit_backup'
for r in data['shells']:groups[r['original_dxf']].append(r)
for path,rows in groups.items():
 src=ezdxf.readfile(ROOT/path);primitives=[(e,bounds(e)) for e in src.modelspace().query('LINE LWPOLYLINE POLYLINE ARC CIRCLE ELLIPSE SPLINE')]
 for r in rows:
  folder=OUT/'Mau'/r['id'];sheet=json.loads((folder/'bo_tri_goc.json').read_text(encoding='utf-8'))['source_sheet_bounds'];selected=[];faces=[]
  vertical=[f['source_bounds'] for f in r['faces'] if f.get('source_bounds') and f.get('kind') in ('outer_door','inner_door','mounting_plate','side')];bottom=min((b[1] for b in vertical),default=sheet[1]);depth=r.get('dimensions_mm',{}).get('depth') or 250
  for f in r['faces']:
   b=f.get('source_bounds');chosen=[];e=src.entitydb.get(f.get('source_perimeter_handle',''))
   if e is not None:chosen.append(e)
   if b:
    width=b[2]-b[0];height=b[3]-b[1]
    for e,q in primitives:
     if not q or not inside(q,(b[0]-3,b[1]-3,b[2]+3,b[3]+3)):continue
     if (q[2]-q[0]>.8*width and q[3]-q[1]>.8*height) or (e.dxftype()=='LINE' and (q[3]-q[1]>.8*height and min(abs(q[0]-b[0]),abs(q[2]-b[2]))<8 or q[2]-q[0]>.8*width and min(abs(q[1]-b[1]),abs(q[3]-b[3]))<8)):chosen.append(e)
   selected.extend(chosen);faces.append({'label':f['source_label'],'source_handles':sorted({e.dxf.handle for e in chosen}),'has_source_boundary':bool(chosen)})
  # Large horizontal shell profiles below the vertical views are sometimes unlabelled.
  lower=[]
  for e,b in primitives:
   if b and inside(b,sheet) and b[3]<bottom-80 and b[1]>sheet[1]+350 and e.dxftype() in ('LWPOLYLINE','POLYLINE') and b[2]-b[0]>250 and 80<b[3]-b[1]<depth+80:
    lower.append((e,b))
  lower_regions=[b for e,b in lower];selected.extend(e for e,b in lower)
  for e,b in primitives:
   if b and any(inside(b,(q[0]-2,q[1]-2,q[2]+2,q[3]+2)) and (b[2]-b[0]>.8*(q[2]-q[0]) or min(abs(b[0]-q[0]),abs(b[2]-q[2]))<8) for q in lower_regions):selected.append(e)
  selected=list({e.dxf.handle:e for e in selected}.values());changes={}
  for fn in ('ban_ve.dxf','ban_ve_co_khung_goc.dxf'):
   dest=backup/r['id']/fn;dest.parent.mkdir(parents=True,exist_ok=True)
   if not dest.exists():shutil.copy2(folder/fn,dest)
   doc=ezdxf.readfile(folder/fn);keys={signature(e) for e in doc.modelspace() if signature(e)};missing=[e for e in selected if signature(e) not in keys]
   if missing:
    imp=Importer(src,doc);imp.import_entities(missing);imp.finalize();doc.saveas(folder/fn)
    if fn=='ban_ve_co_khung_goc.dxf':render(doc,folder/'xem_truoc.svg')
   after={signature(e) for e in doc.modelspace() if signature(e)};assert all(signature(e) in after for e in selected)
   changes[fn]=len(missing)
  audit={'id':r['id'],'faces':faces,'unlabelled_lower_source_handles':[e.dxf.handle for e,b in lower],'restored':changes,'source_boundary_coverage_verified':True,'electrical_residue_review_complete':False}
  r['source_boundary_reconciliation']=audit;r['mechanical_cleaning']['needs_review']=True;r['auto_select']=False;save(folder/'thong_tin.json',r);report.append(audit)
 save(OUT/'catalog.json',data);save(OUT/'kiem_tra_toan_bo_duong_bao_mat.json',report);print('Source boundaries reconciled',len(report),flush=True)
print('Restored',sum(r['restored']['ban_ve.dxf'] for r in report))
