"""Stage all six native orthographic projections for explicit, visual axis review."""
import sys,time,json
from pathlib import Path
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from project_ls_step_views import read_shape,project,RCCB_AXES
from ezdxf.addons.drawing import matplotlib
BASE=Path(__file__).resolve().parents[1]/'data/CatalogTB/Chint/NguonBenNgoai/PRIMARY-RECHECK-20261023'

def prepare(p,exact=False):
  start=time.monotonic();shape=read_shape(p/'source.step')
  if not exact:
   mesh=BRepMesh_IncrementalMesh(shape,.05,False,.5,False);assert mesh.IsDone()
  for code,label,n,x in RCCB_AXES:
   target=p/f'hlr-{ "all" if exact else "poly-all" }-{code}.dxf'
   if not target.exists():
    d=project(shape,n,x,polygonal=not exact,all_visible=True);d.saveas(target);matplotlib.qsave(d.modelspace(),p/(code+'.png'),dpi=75)
   print(p.name,code,round(time.monotonic()-start,1),flush=True)
  s=json.loads((p/'source.json').read_text(encoding='utf8'));s.update(raw_projector_axes=RCCB_AXES,unit_evidence='Manufacturer STEP imported with xstep.cascade.unit=MM; final DXF INSUNITS=4; physical dimensions still require catalog review',projection_method=('Exact original BRep visible edges; 0.025 mm curve chord; no trimming/rescaling' if exact else 'Original visible edges; 0.05 mm mesh, 0.025 mm curve chord; no trimming/rescaling'),review_status='native_six_views_pending_axis_and_dimension_review')
  (p/'source.json').write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding='utf8')

def main():
 names=[a for a in sys.argv[1:] if not a.startswith('--')]
 folders=[p for p in sorted(BASE.iterdir()) if p.is_dir() and (p.name.startswith('NXC-') or p.name in names) and (p/'source.step').is_file() and (p/'source.json').is_file()]
 if names:folders=[p for p in folders if p.name in names]
 for p in folders:
  try:prepare(p,exact='--exact' in sys.argv)
  except Exception as e:
   (p/'projection_error.json').write_text(json.dumps({'status':'held_not_published','error':repr(e),'native_source_preserved':True},indent=2),encoding='utf8');print('HELD',p.name,repr(e),flush=True)

if __name__=='__main__':main()
