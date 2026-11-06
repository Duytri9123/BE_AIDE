"""Publish source-backed AX contacts and MI interlock reference geometry."""
import hashlib
import json
import math
import sys
from pathlib import Path
import ezdxf

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.supplement_chint_catalog_views import BASE,ROWS,metadata,make_job,rectangle
from scripts import supplement_chint_native2d as writer

writer.LABELS.update(REAR='Mặt sau',SIDE_L='Mặt bên trái',BOTTOM='Mặt dưới',ENVELOPE='Bao hình bố trí tham chiếu')


def project_step(path):
 """Visible orthographic STEP edges, in original mm, without rescaling."""
 from OCP.STEPControl import STEPControl_Reader
 from OCP.IFSelect import IFSelect_RetDone
 from OCP.Interface import Interface_Static
 from OCP.BRepMesh import BRepMesh_IncrementalMesh
 from OCP.HLRBRep import HLRBRep_PolyAlgo,HLRBRep_PolyHLRToShape
 from OCP.HLRAlgo import HLRAlgo_Projector
 from OCP.gp import gp_Ax2,gp_Pnt,gp_Dir
 from OCP.TopExp import TopExp_Explorer
 from OCP.TopAbs import TopAbs_EDGE
 from OCP.TopoDS import TopoDS
 from OCP.BRepAdaptor import BRepAdaptor_Curve
 from OCP.GCPnts import GCPnts_QuasiUniformDeflection
 from OCP.GeomAbs import GeomAbs_Line
 assert 'SI_UNIT(.MILLI.,.METRE.)' in path.read_text(encoding='ascii')
 Interface_Static.SetCVal_s('xstep.cascade.unit','MM')
 reader=STEPControl_Reader();assert reader.ReadFile(str(path))==IFSelect_RetDone
 assert reader.TransferRoots()>0;shape=reader.OneShape()
 mesh=BRepMesh_IncrementalMesh(shape,.025,False,.3,False);assert mesh.IsDone()
 axes=[('FRONT',(0,0,1),(1,0,0),0),('REAR',(0,0,-1),(-1,0,0),0),
       ('SIDE',(1,0,0),(0,1,0),90),('SIDE_L',(-1,0,0),(0,-1,0),-90),
       ('TOP',(0,1,0),(1,0,0),0),('BOTTOM',(0,-1,0),(-1,0,0),0)]
 result=[]
 for code,normal,xdir,angle in axes:
  algo=HLRBRep_PolyAlgo();algo.Load(shape)
  algo.Projector(HLRAlgo_Projector(gp_Ax2(gp_Pnt(0,0,0),gp_Dir(*normal),gp_Dir(*xdir))))
  algo.Update();visible=HLRBRep_PolyHLRToShape();visible.Update(algo)
  doc=ezdxf.new('R2010');doc.units=4;model=doc.modelspace();seen=set()
  for method in ('VCompound','OutLineVCompound','Rg1LineVCompound','RgNLineVCompound'):
   part=getattr(visible,method)()
   if part.IsNull():continue
   edges=TopExp_Explorer(part,TopAbs_EDGE)
   while edges.More():
    curve=BRepAdaptor_Curve(TopoDS.Edge(edges.Current()))
    if curve.GetType()==GeomAbs_Line:points=[curve.Value(curve.FirstParameter()),curve.Value(curve.LastParameter())]
    else:
     sample=GCPnts_QuasiUniformDeflection(curve,.025);assert sample.IsDone()
     points=[sample.Value(i) for i in range(1,sample.NbPoints()+1)]
    xy=[(p.X(),p.Y()) for p in points]
    xy=[p for i,p in enumerate(xy) if i==0 or math.dist(p,xy[i-1])>1e-7]
    if len(xy)>1:
     key=tuple((round(x,5),round(y,5)) for x,y in xy);key=min(key,tuple(reversed(key)))
     if key not in seen:seen.add(key);model.add_lwpolyline(xy)
    edges.Next()
  assert len(model)>5 and not doc.audit().errors
  target=path.with_name(path.stem+'-'+code+'.dxf');doc.saveas(target)
  result.append((code,normal,xdir,angle,target))
 return result


def job(key,models,lines,source,views,size,name,review):
 ids=[f'chint-dika-2026-06:5:1:{n}:7' for n in lines]
 assert [ROWS[i]['sku'] for i in ids]==models
 return {'source':key,'source_info':source,'input_dxf':views[0][4] if len(views[0])>4 else BASE/key/'source.dxf',
  'technical_source_url':source['source_url'],'technical_source_pages':[],
  'unit_evidence':'Native manufacturer geometry in millimetres; DXF INSUNITS=4, STEP declares SI_UNIT(.MILLI.,.METRE.) where applicable. No geometry rescaling.',
  'models':models,'kind':ROWS[ids[0]]['category'],'poles':None,'name':name,
  'use':'Mở rộng tiếp điểm hoặc liên động cơ khí cho contactor tương thích.',
  'row_ids':ids,'size':size,'spec':{'Kiểu lắp':'Ghép contactor theo họ tương thích'},'views':views,'restriction':review}


def jobs():
 result=[]
 specs=[
  ('AX3X2',['AX-3X/11'],[2],[26,47.5,39.9],
   [('FRONT',(45,25,98,56),90,[26,47.5]),('SIDE',(45,82,98,125),90,[39.9,47.5]),('TOP',(128,82,159,125),0,[26,39.9])]),
  ('AX3X4',['AX-3X/22'],[3],[44.5,47.5,39.4],
   [('FRONT',(42,18,95,67),90,[44.5,47.5]),('SIDE',(42,87,95,132),90,[39.4,47.5]),('TOP',(129,87,178,132),0,[44.5,39.4])]),
  ('AX3C11',['AX-3C/11'],[4],[17.3,71.8,72.3],
   [('FRONT',(141,57,161,132),0,[17.3,71.8]),('SIDE',(35,57,114,132),0,[72.3,71.8]),('TOP',(35,13,114,42),90,[17.3,72.3])]),
 ]
 for key,models,lines,size,views in specs:
  folder=BASE/key;source=metadata(folder/'source.zip')
  assert hashlib.sha256((folder/'source.dwg').read_bytes()).hexdigest()==source['dwg_sha256']
  source['geometry_representation']='Native manufacturer orthographic CAD'
  source['native_dimension_note']='Actual native envelope retained. AX3X drawings override some nominal dimensions with max values; source geometry is not stretched. AX3C terminal details reach 17.3 mm although the annotated width is 17.2 mm.'
  review='Original CHINT Korea AX accessory DWG, individually separated into complete projections. AX-3X 02–20 drawings have two contact groups, matching /11 housing and four terminals; 04–40 drawings have four groups, matching /22 housing and eight terminals. Manufacturer AX-3X manual explicitly groups these variants by housing. Contact state/nameplate text is not transferred. AX-3C/11 uses its own side-mounted housing and interface, not the front-mounted AX-3X. Exact internal contact mechanism is not approved.'
  result.append(job(key,models,lines,source,views,size,'Tiếp điểm phụ CHINT '+models[0],review))
 folder=BASE/'MI-NATIVE';source=metadata(folder/'source3d.rar')
 for key,models,lines,height,depth in [('MI-SMALL',['MI-5'],[7],74,55),('MI-LARGE',['MI-6','MI-7'],[8,9],125,89)]:
  path=folder/(key+'.step');projections=project_step(path)
  info={**source,'geometry_representation':'Visible edges of simplified native manufacturer STEP',
   'source_step_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
   'archive_member_family':'NC1-09-32' if key=='MI-SMALL' else 'NC1-40-95',
   'projection_axes':[{'view':c,'normal':n,'xdir':x,'rotation_degrees':a} for c,n,x,a,p in projections],
   'mechanical_family_mapping_sources':['https://chintcaucasus.com/en/product/6801549b-f34e-11ea-80d0-0025902f52d3/','https://chintcaucasus.com/en/product/6801549d-f34e-11ea-80d0-0025902f52d3/','https://chintcaucasus.com/en/product/6801549f-f34e-11ea-80d0-0025902f52d3/']}
  dimensions={'FRONT':[11,height],'REAR':[11,height],'SIDE':[depth,height],'SIDE_L':[depth,height],'TOP':[11,depth],'BOTTOM':[11,depth]}
  views=[(c,None,a,dimensions[c],p) for c,n,x,a,p in projections]
  review='CHINT Kazakhstan publishes this accessory archive explicitly for MI-5/6/7. Original STEP members identify NC1-09-32 and NC1-40-95 interlock housings; CHINT regional product pages independently map MI-5 to NC1-09–32/NXC-06–38, MI-6 to NC1-40–65/NXC-40–65 and MI-7 to NC1-80–95/NXC-75–100. Reviewed simplified body geometry is accepted as a cabinet reference. The large source has an actual 89 mm depth (regional nominal 90 mm); keep it without scaling. This simplified source does not model every linkage/pin, so exact moving-linkage interchangeability is not approved.'
  result.append(job(key,models,lines,info,views,[11,height,depth],'Liên động cơ khí CHINT '+' / '.join(models),review))
 # User-authorized family geometry review: reserve the documented larger AC30
 # three-pin footprint without asserting the 124 aperture or exact body size.
 p=BASE/'AC30/source.pdf';info=metadata(p);info['pdf_pages']=[1]
 info['source_variant']='CHINT AC30-108/110, three-pin DIN-rail socket, 36×80 mm front envelope'
 target=rectangle(p.parent/'AC30-124-planning-envelope.dxf',36,80)
 envelope=make_job('AC30-124-ENVELOPE',['AC30-124'],['chint-dika-2026-06:10:0:7:11'],info,
  [('ENVELOPE',None,0,[36,80],target)],[36,80],
  'GPT compatible-family assessment under the user instruction: AC30-124 is a three-pin DIN-rail socket in the published price row. The CHINT AC30 engineering sheet explicitly documents the 36×80 mm front envelope for its three-pin DIN-rail 108/110 housings. This larger family envelope is accepted ONLY as a conservative space-reservation reference for cabinet planning. It is an inference of suitable family footprint, NOT manufacturer-confirmed AC30-124 dimensions or a replica of its universal socket. No aperture, terminal, mounting-hole, latch or exact interchangeable body geometry is published. Electrical ratings remain solely those of the price row.',
  'Ổ cắm CHINT AC30-124 · bao hình dự trù',spec={'Kiểu lắp':'Thanh ray DIN'})
 envelope['source_info']['geometry_representation']='Conservative compatible-family planning envelope; exact SKU geometry not established'
 result.append(envelope)
 return result


if __name__=='__main__':writer.main(jobs(),report_name='chint_accessory_cad_review.json',reviewed_on='2026-11-06')
