"""Recover orthogonal casing axes from the tilted original NXR-100 STEP."""
import json,hashlib,math,shutil
from pathlib import Path
from project_ls_step_views import read_shape,project
from OCP.TopAbs import TopAbs_FACE,TopAbs_VERTEX
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Plane
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.BRep import BRep_Tool
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from ezdxf.addons.drawing import matplotlib
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'data/CatalogTB/Chint/NguonBenNgoai'
dot=lambda a,b:sum(x*y for x,y in zip(a,b))
cross=lambda a,b:(a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def unit(a):
 n=math.sqrt(dot(a,a));return tuple(v/n for v in a)

def main():
 original=BASE/'PRIMARY-RECHECK-20261023/NXR-100-Thermal-Over-load-Relay-Drawing';target=BASE/'NXR-100-INSTALLED-20261023';target.mkdir(exist_ok=True);shutil.copyfile(original/'source.step',target/'source.step');shape=read_shape(target/'source.step');clusters=[]
 e=TopExp_Explorer(shape,TopAbs_FACE)
 while e.More():
  face=TopoDS.Face(e.Current());s=BRepAdaptor_Surface(face)
  if s.GetType()==GeomAbs_Plane:
   d=s.Plane().Axis().Direction();n=(d.X(),d.Y(),d.Z());g=GProp_GProps();BRepGProp.SurfaceProperties_s(face,g);a=g.Mass()
   found=next((c for c in clusters if abs(dot(c['normal'],n))>1-1e-10),None)
   if found:found['area']+=a
   else:clusters.append({'normal':n,'area':a})
  e.Next()
 clusters.sort(key=lambda c:c['area'],reverse=True);a=clusters[0]['normal'];b=next(c['normal'] for c in clusters[1:] if abs(dot(a,c['normal']))<1e-7);axes=[a,b,unit(cross(a,b))]
 vertices=[];e=TopExp_Explorer(shape,TopAbs_VERTEX)
 while e.More():
  p=BRep_Tool.Pnt_s(TopoDS.Vertex(e.Current()));vertices.append((p.X(),p.Y(),p.Z()));e.Next()
 ranges=sorted([(max(dot(v,n) for v in vertices)-min(dot(v,n) for v in vertices),n) for n in axes])
 print('Original casing-axis extents',ranges,flush=True)
 # Known identity comes from the manufacturer file. Extents only establish a
 # candidate pose; six views and the actual control face still require review.
 assert all(abs(actual-nominal)<4 for (actual,n),nominal in zip(ranges,[72,87,117])),ranges
 r=ranges[0][1];u=ranges[1][1];f=unit(cross(r,u));u=unit(cross(f,r));neg=lambda a:tuple(-v for v in a)
 views=[('FRONT',f,r),('REAR',neg(f),neg(r)),('SIDE-L',neg(r),f),('SIDE',r,neg(f)),('TOP',u,r),('BOTTOM',neg(u),r)]
 mesh=BRepMesh_IncrementalMesh(shape,.05,False,.5,False);assert mesh.IsDone()
 for code,n,x in views:
  p=target/f'hlr-poly-all-{code}.dxf'
  if not p.exists():
   d=project(shape,n,x,polygonal=True,all_visible=True);d.saveas(p);matplotlib.qsave(d.modelspace(),target/(code+'.png'),dpi=80)
  print(code,flush=True)
 source=json.loads((original/'source.json').read_text(encoding='utf8'));source.update(step_sha256=hashlib.sha256((target/'source.step').read_bytes()).hexdigest(),candidate_installed_axes=views,pose_evidence='Orthogonal dominant original planar casing normals, checked against NXR-100 manufacturer dimensions; source geometry retained without scaling or trimming',review_status='six_candidate_installed_views_pending_visual_review')
 (target/'source.json').write_text(json.dumps(source,ensure_ascii=False,indent=2),encoding='utf8')

if __name__=='__main__':main()
