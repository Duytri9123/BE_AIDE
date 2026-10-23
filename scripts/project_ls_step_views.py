"""Generate orthographic visible edges from original LS STEP (Open CASCADE HLR)."""
import json,hashlib,math,time
from pathlib import Path
from OCP.STEPControl import STEPControl_Reader
from OCP.IFSelect import IFSelect_RetDone
from OCP.Interface import Interface_Static
from OCP.HLRBRep import HLRBRep_Algo,HLRBRep_HLRToShape
from OCP.HLRAlgo import HLRAlgo_Projector
from OCP.gp import gp_Ax2,gp_Pnt,gp_Dir
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_EDGE
from OCP.TopoDS import TopoDS
from OCP.BRepAdaptor import BRepAdaptor_Curve
from OCP.GCPnts import GCPnts_QuasiUniformDeflection
from OCP.GeomAbs import GeomAbs_Line
import ezdxf
ROOT=Path(__file__).resolve().parents[1]

def read_shape(path):
 Interface_Static.SetCVal_s('xstep.cascade.unit','MM')
 r=STEPControl_Reader();assert r.ReadFile(str(path))==IFSelect_RetDone;assert r.TransferRoots()>0
 return r.OneShape()

def project(shape,normal,xdir,polygonal=False,all_visible=False):
 projector=HLRAlgo_Projector(gp_Ax2(gp_Pnt(0,0,0),gp_Dir(*normal),gp_Dir(*xdir)))
 if polygonal:
  from OCP.HLRBRep import HLRBRep_PolyAlgo,HLRBRep_PolyHLRToShape
  alg=HLRBRep_PolyAlgo();alg.Load(shape);alg.Projector(projector);alg.Update();out=HLRBRep_PolyHLRToShape();out.Update(alg)
 else:
  alg=HLRBRep_Algo();alg.Add(shape);alg.Projector(projector);alg.Update();alg.Hide();out=HLRBRep_HLRToShape(alg)
 d=ezdxf.new('R2010');d.units=4;m=d.modelspace();seen=set()
 parts=[out.VCompound(),out.OutLineVCompound()]
 if all_visible:
  for method in ['Rg1LineVCompound','RgNLineVCompound']:
   if hasattr(out,method):parts.append(getattr(out,method)())
 for part in parts:
  if part.IsNull():continue
  ex=TopExp_Explorer(part,TopAbs_EDGE)
  while ex.More():
   edge=TopoDS.Edge(ex.Current());curve=BRepAdaptor_Curve(edge)
   try:
    if curve.GetType()==GeomAbs_Line:points=[curve.Value(curve.FirstParameter()),curve.Value(curve.LastParameter())]
    else:
     sampler=GCPnts_QuasiUniformDeflection(curve,.025);assert sampler.IsDone();points=[sampler.Value(i) for i in range(1,sampler.NbPoints()+1)]
    xy=[(p.X(),p.Y()) for p in points];xy=[p for i,p in enumerate(xy) if i==0 or math.dist(p,xy[i-1])>1e-7]
    if len(xy)>1:
     key=tuple((round(x,5),round(y,5)) for x,y in xy);key=min(key,tuple(reversed(key)))
     if key not in seen:
      seen.add(key)
      if len(xy)==2:m.add_line(xy[0],xy[1])
      else:m.add_lwpolyline(xy)
   finally:ex.Next()
 from ls_projection_compaction import compact_lines
 return compact_lines(d)

# Definitions are reviewed per manufacturer's coordinate system, never inferred from dimensions.
RCCB_AXES=[('FRONT','Mặt trước',(0,1,0),(0,0,-1)),('REAR','Mặt sau',(0,-1,0),(0,0,1)),('SIDE-L','Mặt bên trái',(0,0,1),(0,1,0)),('SIDE','Mặt bên phải',(0,0,-1),(0,-1,0)),('TOP','Mặt trên',(-1,0,0),(0,0,-1)),('BOTTOM','Mặt dưới',(1,0,0),(0,0,-1))]
if __name__=='__main__':
 import sys
 ident=sys.argv[1] if len(sys.argv)>1 else '55499';p=ROOT/'data/CatalogTB/LS/NguonBenNgoai'/ident;s=read_shape(p/'source.step');axes=RCCB_AXES
 polygonal='--poly' in sys.argv
 if polygonal:
  from OCP.BRepMesh import BRepMesh_IncrementalMesh
  mesh=BRepMesh_IncrementalMesh(s,.05,False,.5,False);assert mesh.IsDone()
 for code,label,n,x in axes:
  all_visible='--all-visible' in sys.argv
  f=p/(('hlr-poly-all-' if polygonal else 'hlr-all-')+code+'.dxf' if all_visible else ('hlr-poly-' if polygonal else 'hlr-reviewed-')+code+'.dxf')
  if f.exists():
   try:
    check=ezdxf.readfile(f)
    from ls_projection_compaction import source_segment_count
    if source_segment_count(check.modelspace())>5 and not check.audit().errors:continue
   except Exception:pass
  t=time.monotonic();d=project(s,n,x,polygonal=polygonal,all_visible=all_visible);tmp=f.with_suffix('.part.dxf');d.saveas(tmp);tmp.replace(f);print(ident,code,len(d.modelspace()),round(time.monotonic()-t,1),'s',flush=True)

