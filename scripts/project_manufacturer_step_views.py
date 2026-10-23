"""Project genuine manufacturer STEP into audited mm DXF views."""
import sys,time
from pathlib import Path
import ezdxf
from project_ls_step_views import read_shape,project,RCCB_AXES,ROOT
from ls_projection_compaction import source_segment_count
from OCP.BRepMesh import BRepMesh_IncrementalMesh
brand,ident=sys.argv[1:3];assert brand in ['LS','Chint']
base=ROOT/'data/CatalogTB'/brand/'NguonBenNgoai';p=(base/ident).resolve();assert p.is_relative_to(base.resolve())
s=read_shape(p/'source.step');mesh=BRepMesh_IncrementalMesh(s,.05,False,.5,False);assert mesh.IsDone()
for code,label,n,x in RCCB_AXES:
 f=p/('hlr-poly-'+code+'.dxf')
 if f.exists():
  d=ezdxf.readfile(f)
  if source_segment_count(d.modelspace())>5 and not d.audit().errors:continue
 t=time.monotonic();d=project(s,n,x,polygonal=True);temp=f.with_suffix('.part.dxf');d.saveas(temp);temp.replace(f);print(ident,code,len(d.modelspace()),round(time.monotonic()-t,1),'s',flush=True)
