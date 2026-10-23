"""Generate review candidates; orientation is approved separately before publication."""
import sys,time
from pathlib import Path
from project_ls_step_views import read_shape,project,RCCB_AXES
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.BRepBndLib import BRepBndLib
from OCP.Bnd import Bnd_Box
from ezdxf.addons.drawing import matplotlib
ROOT=Path(__file__).resolve().parents[1]
def main():
 brand,*families=sys.argv[1:]
 for ident in families:
  p=ROOT/'data/CatalogTB'/brand/'NguonBenNgoai'/ident;s=read_shape(p/'source.step')
  b=Bnd_Box();BRepBndLib.Add_s(s,b);a=b.CornerMin();z=b.CornerMax();print(ident,'bounds',[(getattr(a,c)(),getattr(z,c)()) for c in ['X','Y','Z']],flush=True)
  mesh=BRepMesh_IncrementalMesh(s,.05,False,.5,False);assert mesh.IsDone()
  for code,label,n,x in RCCB_AXES:
   dest=p/('hlr-poly-all-'+code+'.dxf')
   if dest.exists():continue
   start=time.monotonic();d=project(s,n,x,polygonal=True,all_visible=True);d.saveas(dest);matplotlib.qsave(d.modelspace(),p/(code+'.png'),dpi=65);print(ident,code,len(d.modelspace()),round(time.monotonic()-start,1),flush=True)
if __name__=='__main__':main()
