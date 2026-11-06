"""Dimension-verified CAD references recovered from CHINT technical documents.

Catalogue illustrations are not manufacturing CAD. Their printed maximum
dimensions define the calibrated cabinet reference; internal drawn details are
illustrative. Mounting-only outlines contain only independently documented
envelopes/centres, never invented terminals, poles or release mechanisms.
"""
import hashlib
import json
import sys
from pathlib import Path
import ezdxf
from ezdxf import bbox

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.chint_pdf_geometry import vector_view
from scripts import supplement_chint_native2d as writer

BASE=ROOT/'data/CatalogTB/Chint/NguonBenNgoai/REVIEW-20261106'
ROWS={r['id']:r for r in json.loads((ROOT/'app/data/supplier_pricebooks.json').read_text(encoding='utf8'))['items']}
writer.LABELS.update(MOUNTING='Mặt đế gá theo bản vẽ',CUTOUT='Lỗ khoét cánh')


def pdf(folder,name=None):
 candidates=list((BASE/folder).glob('*.pdf'))
 return next(p for p in candidates if name in p.name) if name else candidates[0]


def metadata(path):
 data=json.loads(path.with_suffix('.json').read_text(encoding='utf8'))
 assert hashlib.sha256(path.read_bytes()).hexdigest()==data['sha256']
 return data


def cad_size(path):
 d=ezdxf.readfile(path);b=bbox.extents(d.modelspace());return [b.size.x,b.size.y]


def make_job(key,models,row_ids,source,views,size,review,name,poles=None,spec=None):
 source['geometry_representation']='Dimension-calibrated catalogue reference' if 'vector_calibrations' in source else 'Documented dimension-based outline'
 return {'source':key,'source_info':source,'input_dxf':views[0][4],
  'technical_source_url':source['source_url'],'technical_source_pages':source.get('pdf_pages',[]),
  'unit_evidence':'Printed manufacturer millimetre dimensions are the calibration anchors; DXF INSUNITS=4. Catalogue details are schematic, not manufacturing coordinates.',
  'models':models,'kind':ROWS[row_ids[0]]['category'],'poles':poles,'name':name,
  'use':'Tham chiếu bố trí và hình học thiết bị trong tủ.','row_ids':row_ids,
  'size':size,'spec':{'Kiểu lắp':'Theo bản vẽ tham chiếu',**(spec or {})},'views':views,'restriction':review}


def recovered(key,models,row_ids,path,view_specs,name,poles=None,spec=None):
 source=metadata(path);source['vector_calibrations']=[];views=[]
 for code,page,rect,width,height,angle in view_specs:
  target=path.parent/(key+'-'+code+'.dxf')
  cal=vector_view(path,page,rect,width,target,angle=angle,physical_height_mm=height)
  source['vector_calibrations'].append(cal);views.append((code,None,0,cad_size(target),target))
 source['pdf_pages']=sorted({v[1] for v in view_specs})
 return make_job(key,models,row_ids,source,views,views[0][3],
  'Manufacturer catalogue vector illustration recovered without photos or OCR tracing. Printed width/height calibrate each axis because catalogue artwork is not necessarily plotted at 1:1. Correct family, body and mounting type reviewed; drawn terminals/features remain schematic. No electrical-rating transfer or fabrication approval.',name,poles,spec)


def rectangle(path,width,height,mount_pitch=None):
 d=ezdxf.new('R2010');d.units=4;m=d.modelspace();m.add_lwpolyline([(0,0),(width,0),(width,height),(0,height)],close=True)
 if mount_pitch:
  px,py=mount_pitch
  assert px<width and py<height
  for x in ((width-px)/2,(width+px)/2):
   for y in ((height-py)/2,(height+py)/2):
    m.add_line((x-2,y),(x+2,y));m.add_line((x,y-2),(x,y+2))
 path.parent.mkdir(parents=True,exist_ok=True);d.saveas(path);return path


def mounting_jobs():
 source=metadata(BASE/'NXZM/technical.pdf');source['pdf_pages']=[16]
 result=[]
 # Manufacturer table: A1(4P), A2(3P), B, C, D. C/D are mounting-centre pitches.
 for frames,a4,a3,height,px,py in [([125],300,312,240,267,220),([250],390,393,250,357,230),([400,630],535,540,334,475,304),([800],660,663,344,600,314)]:
  for poles,width in ((3,a3),(4,a4)):
   models=[f'NXZM-{frame}S/{poles}B' for frame in frames]
   row_ids=[r['id'] for r in ROWS.values() if r.get('brand')=='CHINT' and r['sku'] in models]
   assert len(row_ids)==len(models)
   key='NXZM-'+'-'.join(map(str,frames))+f'-{poles}P-MOUNTING';target=rectangle(BASE/'NXZM'/(key+'.dxf'),width,height,(px,py))
   info={**source,'dimension_table':{'overall_width_mm':width,'overall_height_mm':height,'mount_pitch_x_mm':px,'mount_pitch_y_mm':py,'poles':poles}}
   result.append(make_job(key,models,row_ids,info,[('MOUNTING',None,0,[width,height],target)],[width,height],
    'Page 16 table individually reviewed for the specific 3P/4P column and frame. Publish a mounting outline and centre crosses only. Do not stretch the illustrated 4P terminals into a 3P body or invent internal breaker geometry. Crosses mark documented mounting centres, not hole/slot diameters.',
    'ATS CHINT '+' / '.join(models)+' · mặt đế gá',f'{poles}P',{'Kiểu lắp':'Gá vít trên tấm lắp','Khoảng cách tâm gá X×Y (mm)':f'{px} × {py}'}))
 return result


def jobs():
 result=mounting_jobs();p=pdf('NJR2-D')
 for key,lines,page,rect,w,h in [
  ('NJR2-45D',[6],4,(146,340,208,452),145,268),
  ('NJR2-55-75D',[7,8],4,(147,553,222,667),200,310),
  ('NJR2-90-185D',[9,10,11,12,13],5,(168,136,227,255),253,529),
  ('NJR2-220-315D',[14,15,16,17],5,(170,316,228,438),293,564),
 ]:
  ids=[f'chint-dika-2026-06:8:1:{line}:4' for line in lines];models=[ROWS[i]['sku'] for i in ids]
  result.append(recovered(key,models,ids,p,[('FRONT',page,rect,w,h,0)],'Khởi động mềm CHINT '+' / '.join(models),spec={'Kiểu lắp':'Gá vít trên tấm lắp; lắp thẳng đứng'}))
 p=pdf('JSZ3', 'Catalog')
 result.append(recovered('JSZ3-A-F-Y',['JSZ3A*','JSZ3F','JSZ3Y'],[f'chint-dika-2026-06:7:0:{n}:5' for n in (4,5,6)],p,
  [('FRONT',3,(90,125,137,190),41,54.5,0)],'Rơ-le thời gian CHINT JSZ3A / JSZ3F / JSZ3Y'))
 p=pdf('NJYB3')
 result.append(recovered('NJYB3-8-11',['NJYB3-8','NJYB3-11'],[f'chint-dika-2026-06:7:1:{n}:6' for n in (4,5)],p,
  [('FRONT',3,(317,511,363,593),35.8,66.2,0)],'Rơ-le bảo vệ CHINT NJYB3-8 / NJYB3-11',spec={'Kiểu lắp':'Ray DIN'}))
 p=pdf('JD-5')
 for key,models,lines,rect,w,h in [('JD-5-80',['JD-5','JD-5-80B'],[8,10],(64,216,156,266),126,64),('JD-5-400',['JD-5'],[9],(58,438,170,480),156,66)]:
  result.append(recovered(key,models,[f'chint-dika-2026-06:7:1:{n}:6' for n in lines],p,
   [('FRONT',3,rect,w,h,0)],'Bảo vệ động cơ CHINT '+key,spec={'Kiểu lắp':'Gá vít'}))
 p=pdf('JZX')
 for group,line,rect in ((2,2,(52,113,92,209)),(4,3,(309,116,348,211))):
  result.append(recovered(f'JZX-22FD-{group}Z',[f'JZX-22FD/{group}Z'],[f'chint-dika-2026-06:6:1:{line}:5'],p,
   [('FRONT',5,rect,21.8,43,0)],f'Rơ-le CHINT JZX-22FD/{group}Z',spec={'Kiểu lắp':'Cắm trên đế phù hợp'}))
 p=pdf('JQX-13F')
 result.append(recovered('JQX-13F-2Z',['JQX-13F/2Z'],['chint-dika-2026-06:6:1:4:5'],p,
  [('FRONT',3,(317,135,348,191),21.5,43,0)],'Rơ-le CHINT JQX-13F/2Z',spec={'Kiểu lắp':'Cắm trên đế phù hợp'}))
 p=pdf('JQX-10F')
 result.append(recovered('JQX-10F-2Z',['JQX-10F/2Z'],['chint-dika-2026-06:6:1:5:5'],p,
  [('FRONT',2,(355,352,413,450),35,67,0)],'Rơ-le CHINT JQX-10F/2Z',spec={'Kiểu lắp':'Cắm trên đế phù hợp'}))
 p=pdf('NCH8','40～63 2P')
 result.append(recovered('NCH8-40-63-2P',['NCH8-40*','NCH8-63*'],[f'chint-dika-2026-06:11:1:{n}:9' for n in (6,7)],p,
  [('FRONT',1,(276,383,481,471),85,36,90)],'Contactor mô-đun CHINT NCH8-40 / NCH8-63 · 2P','2P',{'Kiểu lắp':'Ray DIN TH35-7.5'}))
 p=pdf('ND16');source=metadata(p);source['pdf_pages']=[4]
 # The catalogue gives a circular 30 mm head; no fictitious lens/ripple detail.
 target=p.parent/'ND16-22C-front.dxf';d=ezdxf.new('R2010');d.units=4;d.modelspace().add_circle((15,15),15);d.saveas(target)
 result.append(make_job('ND16-22C-2',['ND16-22C/2'],['chint-dika-2026-06:10:0:2:11'],source,[('FRONT',None,0,[30,30],target)],[30,30],
  'Manufacturer page 4 defines the 30 mm circular head. This is its dimension-based front outline; lens ripple texture, colour and internal voltage components are not invented.',
  'Đèn báo CHINT ND16-22C/2 · mặt trước',spec={'Kiểu lắp':'Trên cánh tủ'}))
 p=pdf('NP2');source=metadata(p);source['pdf_pages']=[9]
 target=p.parent/'NP2-ES542-front.dxf';d=ezdxf.new('R2010');d.units=4;d.modelspace().add_circle((20,20),20);d.saveas(target)
 result.append(make_job('NP2-ES542',['NP2-ES542'],['chint-dika-2026-06:10:0:18:11'],source,[('FRONT',None,0,[40,40],target)],[40,40],
  'ES542 is the 40 mm latching mushroom head shown in the manufacturer ES family. Publish a documented circular head outline only; no flat 30 mm head or fabricated contact-block detail is substituted.',
  'Nút dừng khẩn CHINT NP2-ES542 · mặt trước',spec={'Kiểu lắp':'Trên cánh tủ'}))
 p=pdf('JQX-13F');source=metadata(p);source['pdf_pages']=[2]
 target=rectangle(p.parent/'CZT08B-01-envelope.dxf',30,68)
 result.append(make_job('CZT08B-01',['CZT08B-01'],['chint-dika-2026-06:6:1:10:5'],source,[('MOUNTING',None,0,[30,68],target)],[30,68,28],
  'Manufacturer matching-socket table explicitly lists CZT08B-01, 68×30×28 mm, for the 2Z relay. This is a mounting-envelope reference, not an invented pin map or screw-hole drawing.',
  'Đế rơ-le CHINT CZT08B-01 · bao hình gá',spec={'Kiểu lắp':'Ray DIN hoặc gá vít theo loại đế'}))
 return result


if __name__=='__main__':writer.main(jobs(),report_name='chint_catalog_cad_review.json',reviewed_on='2026-11-06')
