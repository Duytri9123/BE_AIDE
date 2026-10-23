"""Review candidates from manufacturer IGES MM assemblies, preserving all parts."""
import json,sys
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
 for ident in sys.argv[1:]:
  p=ROOT/'data/CatalogTB/Hyundai/NguonBenNgoai'/ident;meta=json.loads((p/'source.json').read_text());source=(p/meta['source_file']).resolve()
  with source.open() as f:assert '2HMM' in f.read(1000),'IGES unit review required'
  Interface_Static.SetCVal_s('xstep.cascade.unit','MM');r=IGESControl_Reader();r.SetReadVisible(not meta.get('review_all_faces'));assert r.ReadFile(str(source))==IFSelect_RetDone;assert r.TransferRoots()>0;s=r.OneShape()
  if meta.get('review_all_faces'):
   # Review-only candidate: retain every face, with its edges, from all roots.
   # Freestanding construction curves are not device surface geometry.
   from OCP.TopExp import TopExp_Explorer
   from OCP.TopAbs import TopAbs_FACE
   from OCP.BRep import BRep_Builder
   from OCP.TopoDS import TopoDS_Compound
   compound=TopoDS_Compound();builder=BRep_Builder();builder.MakeCompound(compound);ex=TopExp_Explorer(s,TopAbs_FACE)
   while ex.More():builder.Add(compound,ex.Current());ex.Next()
   if meta.get('include_visible_curves'):
    visible=IGESControl_Reader();visible.SetReadVisible(True);assert visible.ReadFile(str(source))==IFSelect_RetDone;assert visible.TransferRoots()>0;builder.Add(compound,visible.OneShape())
   s=compound
  b=Bnd_Box();BRepBndLib.Add_s(s,b);a,z=b.CornerMin(),b.CornerMax();print(ident,'bounds',[(getattr(a,c)(),getattr(z,c)()) for c in ['X','Y','Z']],flush=True)
  mesh=BRepMesh_IncrementalMesh(s,.05,False,.5,False);assert mesh.IsDone()
  for code,label,n,x in RCCB_AXES:
   dest=p/('hlr-poly-all-'+code+'.dxf')
   if dest.exists():continue
   d=project(s,n,x,polygonal=True,all_visible=True);d.saveas(dest);matplotlib.qsave(d.modelspace(),p/(code+'.png'),dpi=65);print(ident,code,len(d.modelspace()),flush=True)
if __name__=='__main__':main()
