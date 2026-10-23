"""Keep original IGES assemblies intact and generate six review projections."""
import sys,time
from pathlib import Path
from OCP.IGESControl import IGESControl_Reader
from OCP.IFSelect import IFSelect_RetDone
from OCP.Interface import Interface_Static
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.BRepBndLib import BRepBndLib
from OCP.Bnd import Bnd_Box
from project_ls_step_views import project,RCCB_AXES
from ezdxf.addons.drawing import matplotlib
ROOT=Path(__file__).resolve().parents[1]
def main():
 for pole in sys.argv[1:] or ['1P','2P','4P']:
  p=ROOT/'data/CatalogTB/Chint/NguonBenNgoai'/('NB1-63H-'+pole)
  Interface_Static.SetCVal_s('xstep.cascade.unit','MM');r=IGESControl_Reader();assert r.ReadFile(str(p/'source.igs'))==IFSelect_RetDone;assert r.TransferRoots()>0
  shape=r.OneShape();b=Bnd_Box();BRepBndLib.Add_s(shape,b);a=b.CornerMin();z=b.CornerMax();print(pole,'bounds',[(getattr(a,c)(),getattr(z,c)()) for c in ['X','Y','Z']],flush=True)
  mesh=BRepMesh_IncrementalMesh(shape,.05,False,.5,False);assert mesh.IsDone()
  for code,label,n,x in RCCB_AXES:
   dest=p/('hlr-poly-all-'+code+'.dxf')
   if dest.exists():continue
   start=time.monotonic();d=project(shape,n,x,polygonal=True,all_visible=True);d.saveas(dest);matplotlib.qsave(d.modelspace(),p/(code+'.png'),dpi=75);print(pole,code,len(d.modelspace()),round(time.monotonic()-start,1),flush=True)
if __name__=='__main__':main()
