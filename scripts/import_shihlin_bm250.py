"""Review original BM250-SN bodies in their installed axes; never substitute 2P."""
import hashlib,json,sys,shutil,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from project_ls_step_views import read_shape,project
from import_ls_step_family import entities,LABELS
from ls_native_writer import CAT,write_profile,price_option
from ezdxf import bbox
import ezdxf
BASE=CAT/'Shihlin/NguonBenNgoai'

def installed_axes(shape):
 from OCP.TopExp import TopExp_Explorer
 from OCP.TopAbs import TopAbs_FACE
 from OCP.TopoDS import TopoDS
 from OCP.BRepAdaptor import BRepAdaptor_Surface
 from OCP.GeomAbs import GeomAbs_Plane
 from OCP.BRepGProp import BRepGProp
 from OCP.GProp import GProp_GProps
 faces=[];e=TopExp_Explorer(shape,TopAbs_FACE)
 while e.More():
  f=TopoDS.Face(e.Current());s=BRepAdaptor_Surface(f)
  if s.GetType()==GeomAbs_Plane:
   p=GProp_GProps();BRepGProp.SurfaceProperties_s(f,p);n=s.Plane().Axis().Direction();faces.append((p.Mass(),(n.X(),n.Y(),n.Z())))
  e.Next()
 def axis(component):
  area,n=max((a,n) for a,n in faces if abs(n[component])>.99)
  assert area>500
  return tuple(v if n[component]>0 else -v for v in n)
 f=axis(2);r=axis(0);assert abs(sum(x*y for x,y in zip(f,r)))<1e-8
 u=(f[1]*r[2]-f[2]*r[1],f[2]*r[0]-f[0]*r[2],f[0]*r[1]-f[1]*r[0]);assert u[1]>.99
 return r,u,f

def prepare():
 from OCP.BRepMesh import BRepMesh_IncrementalMesh
 from ezdxf.addons.drawing import matplotlib
 original=BASE/'BM250-PRIMARY-20261023';source=json.loads((original/'source.json').read_text(encoding='utf8'))
 for pole in [3,4]:
  folder=BASE/f'BM250-SN-{pole}P-INSTALLED-20261023';folder.mkdir(exist_ok=True)
  native=original/f'BM250-SN {pole}P.STEP';shutil.copyfile(native,folder/'source.step')
  shape=read_shape(folder/'source.step');r,u,f=installed_axes(shape);neg=lambda a:tuple(-x for x in a)
  print('Installed axes',pole,r,u,f,flush=True)
  axes=[('FRONT',f,r),('REAR',neg(f),neg(r)),('SIDE-L',neg(r),f),('SIDE',r,neg(f)),('TOP',u,r),('BOTTOM',neg(u),r)]
  mesh=BRepMesh_IncrementalMesh(shape,.05,False,.5,False);assert mesh.IsDone()
  for code,n,x in axes:
   target=folder/f'hlr-poly-all-{code}.dxf'
   if not target.exists():
    d=project(shape,n,x,polygonal=True,all_visible=True);d.saveas(target);matplotlib.qsave(d.modelspace(),folder/(code+'.png'),dpi=85)
   print(pole,code,flush=True)
  (folder/'source.json').write_text(json.dumps({**source,'native_member':native.name,'step_sha256':hashlib.sha256(native.read_bytes()).hexdigest(),'axes':axes,'installed_axes_evidence':'Largest planar back/cover faces define front normal; largest perpendicular casing side faces define right; cross product defines up. Original STEP geometry retained, no scaling or trimming. Native 4P assembly has a small rigid pose tilt; project along physical casing normals.'},ensure_ascii=False,indent=2),encoding='utf8')

def publish():
 from app.services.catalog_family_matching import row_poles
 from publish_abb_ct_index import main as publish_index
 rows=json.loads((ROOT/'app/data/supplier_pricebooks.json').read_text(encoding='utf8'))['items'];paths=[];report=[]
 for pole in [3,4]:
  ident=f'BM250-SN-{pole}P-INSTALLED-20261023';folder=BASE/ident
  source=json.loads((folder/'source.json').read_text(encoding='utf8'))
  views,_=entities(ident,[(c,c,0) for c in LABELS],'Shihlin');assert len(views)==6
  sizes={c:bbox.extents(es).size for c,l,es in views}
  width,height,depth=sizes['FRONT'].x,sizes['FRONT'].y,sizes['SIDE'].x
  assert abs(width-(105 if pole==3 else 140))<.15 and abs(height-165)<.15 and abs(depth-92)<1
  matched=[r for r in rows if r['brand']=='Shihlin' and r['sku']=='BM250-SN' and row_poles(r)==str(pole)+'P'];assert len(matched)==1
  options=[{**price_option(r,brand='Shihlin'),'price':'---','basis':'exact_named_manufacturer_step_family','exact_cad_match':False} for r in matched]
  source.update(six_views_verified=True,complete_manufacturer_step_projection=True,projection_method='Open CASCADE complete original STEP visible edges; installed physical casing axes, 0.05 mm mesh, 0.025 mm curve chord; no geometry removed or rescaled',unit_evidence='Manufacturer STEP in mm, STEP import MM, DXF INSUNITS=4',review='All six native projections visually checked against LINE/LOAD terminals, neutral pole and mounting back. Full envelope measured from final DXF; physical casing axes avoid the original 4P assembly pose tilt.',technical_source_url='https://en.seec.com.tw/UpFiles/30/GoodsDownload_Files707031024777540171/VIEW_BSE-MCCB-221101.pdf')
  dimensions=' × '.join(format(round(x,2),'g') for x in (width,height,depth))
  spec={'Kiểu lắp':'Cố định, gá vít trên tấm lắp','Kiểu đầu nối':'Đấu nối phía trước','Vị trí thường lắp':'Ngăn đóng cắt nguồn hoặc xuất tuyến','Kích thước CAD W×H×D (mm)':dimensions}
  path=write_profile(f'BM250-SN-{pole}P',f'Shihlin · MCCB · BM250-SN · {pole}P','MCCB',['BM250-SN'],str(pole)+'P',options,views,source,spec,brand='Shihlin');paths.append(path)
  report.append({'profile':path.relative_to(CAT).as_posix(),'poles':str(pole)+'P','dimensions_mm':dimensions,'price_rows':[r['id'] for r in matched]})
 ledger=ROOT/'app/data/catalog_verified_view_health.json';health=json.loads(ledger.read_text(encoding='utf8'))
 for path in paths:
  for f in path.parent.glob('CadDon/*/ban_ve.dxf'):
   d=ezdxf.readfile(f);a=d.audit();assert d.units==4 and not a.errors and not a.fixes
   health['files'][f.relative_to(CAT).as_posix()]={'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'preview_sha256':hashlib.sha256(f.with_name('xem_truoc.svg').read_bytes()).hexdigest()}
 ledger.write_text(json.dumps(health,ensure_ascii=False,indent=2),encoding='utf8')
 (ROOT/'docs/catalog-completion-2026-10-23/shihlin-bm250-import.json').write_text(json.dumps({'items':report,'held':'Supplier BM250-SN 2P row has no 2P source in the original manufacturer archive; never use the 3P or 4P body.'},ensure_ascii=False,indent=2),encoding='utf8')
 publish_index([p.parent.name for p in paths],report_name='shihlin-full-faces-2026-10-23',brand='Shihlin',category='MCCB',profile_root='Shihlin/ThietBi',refresh=False)

if __name__=='__main__':prepare() if sys.argv[1]=='project' else publish()
