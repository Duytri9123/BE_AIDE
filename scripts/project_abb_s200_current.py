"""Produce review projections from complete original ABB STEP assemblies."""
import sys,time
from pathlib import Path
from project_ls_step_views import read_shape,project,RCCB_AXES
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from ezdxf.addons.drawing import matplotlib
ROOT=Path(__file__).resolve().parents[1]
def main():
 for uid in sys.argv[1:] or ['9AKK106930A4834','9AKK106930A4835','9AKK106930A4836','9AKK106930A4837']:
  p=ROOT/'data/CatalogTB/ABB/NguonBenNgoai'/uid
  s=read_shape(p/'source.step');mesh=BRepMesh_IncrementalMesh(s,.05,False,.5,False);assert mesh.IsDone()
  for code,label,n,x in RCCB_AXES:
   target=p/('hlr-poly-all-'+code+'.dxf')
   if target.exists():continue
   start=time.monotonic();doc=project(s,n,x,polygonal=True,all_visible=True);doc.saveas(target)
   matplotlib.qsave(doc.modelspace(),p/(code+'.png'),dpi=75)
   print(uid,code,len(doc.modelspace()),round(time.monotonic()-start,1),flush=True)
if __name__=='__main__':main()
