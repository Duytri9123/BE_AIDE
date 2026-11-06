"""Reviewed compatible geometry for remaining CHINT transformers and controls."""
import hashlib
import json
import sys
from pathlib import Path
import ezdxf
from ezdxf import bbox

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import supplement_chint_native2d as writer
from app.services.cad.catalogtb_assets import normalized_source

CAT=ROOT/'data/CatalogTB'
BASE=CAT/'Chint/NguonBenNgoai'
ROWS={r['id']:r for r in json.loads((ROOT/'app/data/supplier_pricebooks.json').read_text(encoding='utf8'))['items']}
writer.LABELS.update(ISOMETRIC='Hình trục đo',CUTOUT='Lỗ khoét cánh')


def bounds(path,angle=0):
 import math
 from ezdxf.math import Matrix44
 d=ezdxf.readfile(path);assert d.units==4
 if angle:
  for e in d.modelspace():e.transform(Matrix44.z_rotate(math.radians(angle)))
 b=bbox.extents(d.modelspace());return [b.size.x,b.size.y]


def ndk_jobs():
 jobs=[]
 for line,n in [(3,25),(4,50),(5,100),(6,150),(7,200),(8,250),(9,300),(10,500),(11,700),(12,1000),(13,1500),(14,2000),(15,3000),(16,5000)]:
  folder=BASE/f'NDK-{n}';source=json.loads((folder/'source.json').read_text(encoding='utf8'))
  assert hashlib.sha256((folder/'source.step').read_bytes()).hexdigest()==source['sha256']
  if n==100:
   mapping=[('ISOMETRIC','FRONT',0)]
  else:
   primary='SIDE' if n in (250,300,500) else 'SIDE-L'
   mapping=[('FRONT',primary,0),('SIDE','FRONT',0),('TOP','TOP',90)]
  views=[]
  for code,raw,angle in mapping:
   path=folder/f'hlr-poly-all-{raw}.dxf';size=bounds(path,angle);views.append((code,None,angle,size,path))
  size=views[0][3] if n==100 else [*views[0][3],views[1][3][0]]
  if n!=100:
   assert abs(views[0][3][1]-views[1][3][1])<.05
   assert abs(views[0][3][0]-views[2][3][0])<.05
   assert abs(views[1][3][0]-views[2][3][1])<.05
  review=('Original manufacturer NDK STEP for the named VA frame; visible terminal groups, winding body and mounting feet reviewed in all six projections. Different voltage taps and winding conductor are not inferred from CAD. ')
  review+=('Native model is oblique to the exported axes: publish only an axonometric reference, not an orthographic mounting view or physical overall dimensions.' if n==100 else 'Front/side/top axes chosen by the visible terminal face and mounting feet; opposed envelopes cross-checked without scaling or cropping.')
  spec={'Kiểu lắp':'Gá vít trên tấm lắp','Công suất khung tham chiếu (VA)':str(n)}
  if n==100:spec.update({'Kích thước hình chiếu trước W×H (mm)':None})
  jobs.append({'source':f'NDK-{n}-REVIEWED','source_info':source,'input_dxf':views[0][4],
   'technical_source_url':json.loads((BASE/'NDK-CATALOG/source.json').read_text(encoding='utf8'))['source_url'],
   'technical_source_pages':[1,2],'unit_evidence':'Original manufacturer STEP imported in millimetres; Open CASCADE visible-edge projection; DXF INSUNITS=4; scale 1.',
   'models':[f'NDK-{n}'],'kind':'TRANSFORMER','poles':None,'name':f'Biến áp điều khiển CHINT NDK-{n}',
   'use':'Biến đổi điện áp cho mạch điều khiển.','row_ids':[f'chint-dika-2026-06:9:0:{line}:8'],
   'size':size,'spec':spec,'views':views,'restriction':review})
 return jobs


def existing_job(folder,models,row_ids,indices,source_url,review,name,poles=None,spec=None):
 p=CAT/'Chint/ThietBi'/folder/'thong_tin_thiet_bi.json';raw=json.loads(p.read_text(encoding='utf8'))
 views=[];source_paths=[]
 for index,code in indices:
  v=raw['cad_don'][index];f=normalized_source(p.parent/v['duong_dan']);source_paths.append(f.relative_to(CAT).as_posix())
  views.append((code,None,0,bounds(f),f))
 row=ROWS[row_ids[0]]
 return {'source':folder+'-COMPATIBLE','source_info':{'source_url':source_url,'source_page':source_url,
  'source_profile':p.relative_to(CAT).as_posix(),'source_views':source_paths},'input_dxf':views[0][4],
  'technical_source_url':source_url,'technical_source_pages':[],
  'unit_evidence':'Existing source-backed CAD has verified millimetre units; actual full outline retained. Manufacturer dimensional family reviewed.',
  'models':models,'kind':row['category'],'poles':poles,'name':name,'use':'Điều khiển và giám sát mạch điện.',
  'row_ids':row_ids,'size':views[0][3],'spec':spec or {'Kiểu lắp':'Theo bản vẽ tham chiếu'},'views':views,'restriction':review}


def jobs():
 result=ndk_jobs()
 np2='https://www.chintglobal.com/content/dam/chint/global/product-center/low-voltage/iec/industrial-control/push-button/np2/catalog/NP2-PUSH-BUTTON-Catalog.pdf'
 result.append(existing_job('NP2_NO',['NP2-EA*','NP2-EW*'],['chint-dika-2026-06:10:0:10:11','chint-dika-2026-06:10:0:14:11'],[(0,'FRONT')],np2,
  'Round 30 mm NP2 operator face matches the 31 mm maximum EA/EW head family. Publish front geometry only; do not mix side views of different head/contact variants. Illumination and contacts remain price-row choices.',
  'Nút nhấn CHINT NP2-EA / NP2-EW · mặt trước',spec={'Kiểu lắp':'Trên cánh tủ'}))
 result.append(existing_job('NP2_Selector',['NP2-ED/J*'],['chint-dika-2026-06:10:0:22:11','chint-dika-2026-06:10:0:26:11'],[(0,'FRONT')],np2,
  'NP2 rotary selector head reviewed against the manufacturer ED/EJ selector family: same circular panel operator and lever. Two/three detents and contacts are internal electrical/order choices; one static front position does not imply the number of detents.',
  'Công tắc xoay CHINT NP2-ED/J · mặt trước',spec={'Kiểu lắp':'Trên cánh tủ'}))
 result.append(existing_job('NCH8_20_25_2P',['NCH8-20*','NCH8-25*'],['chint-dika-2026-06:11:1:4:9','chint-dika-2026-06:11:1:5:9'],[(0,'FRONT'),(1,'SIDE')],
  'https://www.chintglobal.com/global/en/products/low-voltage/iec/industrial-control/nch8.html',
  'Native 2P modular body has two main terminal positions plus coil terminals. Front width 18.003 mm and height 85 mm, side depth 66.618 mm agree with the manufacturer NCH8-20/25 2P drawing (18 × 85 × 66.5).',
  'Contactor mô-đun CHINT NCH8-20 / NCH8-25 · 2P',poles='2P',spec={'Kiểu lắp':'Ray DIN TH35-7.5'}))
 # The commercial row leaves the control voltage open; it does not describe a
 # different enclosure. The exact named official body is a geometry reference.
 result.append(existing_job('OFFICIAL-TIMER-KG316T',['KG316T'],['chint-dika-2026-06:7:0:7:5'],[(0,'FRONT'),(1,'REAR'),(3,'SIDE'),(4,'TOP')],
  'https://www.chintglobal.com/global/en/products/low-voltage/iec/industrial-control/kg316t.html',
  'Exact named KG316T official enclosure, screw mounting and terminal positions. Price row voltage/contact choices do not require a different label-perfect drawing. Source terminal markings are retained; no 1NO/1CO or voltage equivalence is inferred.',
  'Công tắc thời gian CHINT KG316T',spec={'Kiểu lắp':'Gá vít'}))
 return result


if __name__=='__main__':writer.main(jobs(),report_name='chint_control_cad_review.json',reviewed_on='2026-11-06')
