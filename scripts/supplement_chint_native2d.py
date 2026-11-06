"""Publish reviewed CHINT 2D geometry and DIKA browsing links.

Source DWGs are converted with AutoCAD Core Console; no geometry is rescaled.
The 120–225 sheet has rear, side and top views, so no front view is invented.
Electrical order variants remain price-row choices, never geometry approval.
User-authorized compatibility review considers mechanical fit, not literal
nameplate equality; native source markings and dimensional differences remain
recorded in the evidence. Existing NXM outlines are verified front views only.
"""
import hashlib
import json
import math
import sqlite3
import sys
from pathlib import Path

import ezdxf
from ezdxf import bbox
from ezdxf.addons import Importer
from ezdxf.addons.drawing import Frontend, RenderContext, svg, layout, matplotlib
from ezdxf.math import Matrix44

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.services.price_row_cad_detail import row_configuration_digest
from app.services.catalog_product_sections import pole_compatible

CAT=ROOT/'data/CatalogTB'
BASE=CAT/'Chint/NguonBenNgoai/NXC-NATIVE2D-20261105'
LABELS={'FRONT':'Mặt trước','REAR':'Mặt sau','SIDE':'Mặt bên','TOP':'Mặt trên'}
# Selection windows lie in the empty space between complete native projections.
# Expected dimensions are from individually reviewed source geometry; the
# manufacturer maximum envelopes are checked separately, without stretching.
JOBS=[
 {'source':'NXC-40-65-AC-Contactor-Drawing','models':['NXC-40','NXC-50','NXC-65'],'lines':[13,14,15],
  'nominal':[77,129,118],'size':[76,127.5,116.5],
  'views':[('FRONT',(-535,-10,-390,85),90,[76,127.5]),
           ('SIDE',(-535,90,-390,225),90,[116.5,127.5]),
           ('TOP',(-370,90,-265,225),0,[76,116.5])],
  'restriction':'Nameplate reads NXC-65; manufacturer explicitly groups NXC-40/50/65 under the same mechanical drawing. User accepts geometry compatibility; electrical nameplate is not transferred.'},
 {'source':'NXC-120-225-AC-Contactor-Drawing','models':['NXC-120','NXC-160','NXC-185','NXC-225'],'lines':[19,20,21,22],
  'nominal':[127,182,156],'size':[125.3,179.6,157.2],
  'views':[('REAR',(1370,80,1530,280),0,[125.3,179.6]),
           ('SIDE',(1100,-115,1340,85),90,[157.2,179.6]),
           ('TOP',(1370,-115,1530,85),180,[125.3,157.2])],
  'restriction':'Common named 120–225 manufacturer drawing; no front projection in this sheet.'},
 {'source':'NXC-265-400-AC-Contactor-Drawing','models':['NXC-265','NXC-400'],'lines':[23,25],
  'nominal':[150,236,207],'size':[149,235.3,206.8],
  'views':[('FRONT',(1180,30,1350,280),0,[149,235.3]),
           ('SIDE',(880,30,1140,280),0,[206.8,235.3]),
           ('TOP',(1180,320,1350,550),180,[149,206.8])],
  'restriction':'Named 265–400 family; electrical coil variant is selected independently.'},
 {'source':'NXC-500-630-AC-Contactor-Drawing','models':['NXC-500','NXC-630'],'lines':[26,27],
  'nominal':[165,248,225],'size':[164.2,246,224.1],
  'views':[('FRONT',(1440,160,1630,430),0,[164.2,246]),
           ('SIDE',(1060,160,1310,430),0,[224.1,246]),
           ('TOP',(1440,470,1630,750),180,[164.2,224.1])],
  'restriction':'Native 2D drawing resolves the short height of the held STEP source.'},
]
for pole,width in ((2,35.6),(3,53.4),(4,71.2)):
 JOBS.append({'source':f'NXB-63-{pole}P','folder':CAT/f'Chint/NguonBenNgoai/NXB-63-{pole}P',
  'models':['NXB-63','NXB-63H'],'kind':'MCB','poles':f'{pole}P','unitless_dimension_review':True,
  'row_ids':[f'chint-dika-2026-06:2:0:{line}:{ {2:5,3:6,4:8}[pole]}' for line in range(3 if pole<4 else 5,8)],
  'nominal':[18*pole,81,77.8],'size':[width,81,79.836 if pole==4 else 77.836],
  'views':[('FRONT',(35,15,145,100),90,[width,81]),
           ('SIDE',(35,115,145,210),90,[79.836 if pole==4 else 77.836,81])],
  'restriction':'NXB-63H accepted as NXB-63 cabinet geometry after review of poles, TH35 rail, 45 mm front opening, body envelope and terminal layout. Actual CAD envelope is retained, including the roughly 2 mm extra depth on 4P. No 10kA rating or exact mechanical interchangeability is asserted.'})
for source,models,lines,size,nominal in [
 ('SRC_CHINT_d5a8ac975547',['NXM-125S'],[3],[78,134],[78,135]),
 ('SRC_CHINT_3551f69f1564',['NXM-400S','NXM-630S'],[6,7],[140,257],[140,257]),
 ('SRC_CHINT_0c6295b3044d',['NXM-800S'],[8],[182,270],[182,270]),
 ('SRC_CHINT_a5c5ebc505f4',['NXM-1000S'],[9],[210,280],[210,280]),
 ('SRC_CHINT_2f7527c08497',['NXM-1600H'],[12],[210,370],[210,370]),
]:
 JOBS.append({'source':source,'legacy_profile':CAT/f'Chint/ThietBi/{source}/thong_tin_thiet_bi.json',
  'models':models,'kind':'MCCB','poles':'3P','nominal':nominal,'size':size,
  'row_ids':[f'chint-dika-2026-06:3:0:{line}:5' for line in lines],
  'views':[('FRONT',None,0,size)],
  'restriction':'GPT visual review confirms three separate terminal positions at each end and the frame-specific front width/height in CHINT NXM catalog pages 27–28. Source block identifies the NXM frame; abbreviated or omitted S suffix is accepted for front geometry. This is an existing source-backed 2D cabinet outline, not a six-view manufacturer model or electrical approval.'})


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def sync_agent_export(ids):
 with sqlite3.connect(CAT/'_agent_index/equipment_catalog.sqlite') as db:
  total=db.execute('SELECT count(*) FROM equipment').fetchone()[0]
  records=[json.loads(row[0]) for row in db.execute('SELECT record_json FROM equipment WHERE catalog_id IN ('+','.join('?' for _ in ids)+')',list(ids))]
 export=CAT/'_agent_index/equipment_catalog.jsonl'
 current=[json.loads(line) for line in export.read_text(encoding='utf8').splitlines() if line.strip()]
 current=[row for row in current if row['catalog_id'] not in ids]+records
 pending=export.with_suffix('.tmp');pending.write_text(''.join(json.dumps(row,ensure_ascii=False)+'\n' for row in current),encoding='utf8');pending.replace(export)
 manifest=CAT/'_agent_index/manifest.json';data=json.loads(manifest.read_text(encoding='utf8'))
 data.update(records=total,catalogtb_profiles=total);manifest.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')


def main(jobs=None, report_name='chint_native2d_review.json', reviewed_on='2026-11-05'):
 rows={r['id']:r for r in json.loads((ROOT/'app/data/supplier_pricebooks.json').read_text(encoding='utf8'))['items']}
 health_path=ROOT/'app/data/catalog_verified_view_health.json'
 health=json.loads(health_path.read_text(encoding='utf8'))
 snapshot_path=CAT/'_agent_index/browser_display_v5.json'
 snapshot=json.loads(snapshot_path.read_text(encoding='utf8'))
 overlay_path=ROOT/'app/data/catalogtb_published_information.json'
 overlay=json.loads(overlay_path.read_text(encoding='utf8'))
 records=[];devices=[];results=[]
 for job in (JOBS if jobs is None else jobs):
  if job.get('source_info'):
   source=dict(job['source_info']);input_dxf=Path(job['input_dxf'])
  elif job.get('legacy_profile'):
   from app.services.cad.catalogtb_assets import normalized_source
   raw=json.loads(job['legacy_profile'].read_text(encoding='utf8'))
   input_dxf=normalized_source(job['legacy_profile'].parent/raw['cad_don'][0]['duong_dan'])
   source={'source_page':'https://www.chintglobal.com/global/en/products/low-voltage/iec/secondary-power-distribution/nxm.html',
    'source_url':json.loads((CAT/'Chint/NguonBenNgoai/NXM-CATALOG/source.json').read_text(encoding='utf8'))['source_url'],
    'source_profile':job['legacy_profile'].relative_to(CAT).as_posix(),'source_dxf_sha256':digest(input_dxf)}
  else:
   folder=job.get('folder') or BASE/job['source'];source=json.loads((folder/'source.json').read_text(encoding='utf8'))
   assert digest(folder/'source.dwg')==source['sha256']
   input_dxf=folder/'source.dxf'
  doc=ezdxf.readfile(input_dxf);assert doc.units==4 or (doc.units==0 and job.get('unitless_dimension_review'))
  kind=job.get('kind','CONTACTOR');poles=job.get('poles','3P')
  source.update(converted_dxf_sha256=digest(input_dxf),
   technical_source_url=job.get('technical_source_url') or json.loads((CAT/('Chint/NguonBenNgoai/NXM-CATALOG/source.json' if kind=='MCCB' else 'Chint/NguonBenNgoai/NXB-63H-CATALOG/source.json' if kind=='MCB' else 'Chint/NguonBenNgoai/PRIMARY-RECHECK-20261023/NXC-CATALOG/source.json')).read_text(encoding='utf8'))['source_url'],
   technical_source_pages=job.get('technical_source_pages',[27,28] if kind=='MCCB' else [9] if kind=='MCB' else [12,13]),nominal_catalog_maximum_mm=job.get('nominal'),
   native_envelope_mm=job['size'],reviewed_on=reviewed_on,restriction=job['restriction'],
   unit_evidence=job.get('unit_evidence') or ('Native dimension endpoints measure 81 units for the explicitly marked 81 mm height; pole widths agree with 36/54/72 mm minus source tolerance; scale factor 1' if kind=='MCB' else 'Native AutoCAD DXF INSUNITS=4; dimension entities and catalog maxima reviewed; scale factor 1'),
   exact_sku_approval=False)
  if job.get('nominal'):assert all(abs(a-b)<3 for a,b in zip(job['size'],job['nominal']))
  models=job['models'];model=' / '.join(models);family='NATIVE2D-'+job['source'].removesuffix('-AC-Contactor-Drawing')
  path=CAT/'Chint/ThietBi'/('OFFICIAL-'+family)/'thong_tin_thiet_bi.json'
  cid='TB-'+hashlib.sha1(path.relative_to(CAT).as_posix().encode()).hexdigest()[:16]
  options=[]
  row_ids=job.get('row_ids') or [f'chint-dika-2026-06:4:0:{line}:{column}' for line in job['lines'] for column in (15,18)]
  for row_id in row_ids:
    row=rows[row_id]
    assert row['sku'] in models and row['brand']=='CHINT' and (not poles or pole_compatible({'spec':{'so_cuc':poles}},row))
    options.append({'brand':'CHINT','model':row['sku'],'source_row_id':row['id'],
     'specifications':row['specifications'],'source_url':row['source_url'],'source_page':row['source_page'],
     'basis':'reviewed_chint_native2d','exact_cad_match':False,
     'source_row_configuration_sha256':row_configuration_digest(row),
     'reviewed_device_model':model,'reviewed_device_poles':poles,
     'geometry_compatibility_review':{'assessment':job['restriction'],'user_accepts_compatible_geometry':True,'electrical_equivalence':False}})
  refs={'category':kind,'options':options,'source_row_scope':'explicit_only','row_links_reviewed':True}
  name=job.get('name') or (kind if kind in ('MCB','MCCB') else 'Khởi động từ')+' CHINT '+model+(' · '+poles if poles else '')
  spec={**({'so_cuc':poles} if poles else {}),'Kiểu lắp':'Ray DIN TH35-7.5' if kind=='MCB' else 'Gá ray DIN hoặc gá vít trên tấm lắp' if job['source'].startswith('NXC-40') else 'Gá vít trên tấm lắp',
   ('Kích thước CAD W×H×D (mm)' if len(job['size'])==3 else 'Kích thước hình chiếu trước W×H (mm)'):' × '.join(map(str,job['size']))}
  spec.update(job.get('spec') or {})
  profile={'nhom':'CHINT','hang_xac_nhan':'CHINT','ma_dong_san_pham':model,'ten_san_pham':name,
   'ten_kieu':name,'ban_chat':kind,'cong_dung':job.get('use') or ('Đóng cắt và bảo vệ mạch điện.' if kind in ('MCB','MCCB') else 'Đóng cắt và điều khiển tải động cơ.'),
   'thong_so':spec,'catalog_tham_khao':refs,'auto_select':False,'needs_review':True,
   'nhan_dien_ai':{'loai_thiet_bi_code':kind,'cac_ma_dong_san_pham':models,'so_cuc':int(poles[0]) if poles else None,'exact_SKU_confirmed':False},
   'nguon_tham_khao':[source['source_page'],source['source_url']],'tu_khoa_tim_kiem':['CHINT',*models],
   'muc_do_xac_nhan':'Bản vẽ họ thiết bị chính hãng; chọn riêng cấu hình điện và phụ kiện.',
   'cad_don':[],'source_catalog_review':source}
  entity_boxes=[]
  for ent in doc.modelspace():
   if ent.dxftype() in {'DIMENSION','INSERT','TEXT','MTEXT'} or any(t in ent.dxf.layer for t in ('AXIS','DIMENSION','ALL_DIM')) or ent.dxf.layer in {'尺寸线','文字层','中心线','双点画线'}:continue
   box=bbox.extents([ent])
   if box.has_data:entity_boxes.append((ent,box))
  browser_views=[];record_views=[]
  for view_job in job['views']:
   code,rect,angle,expected=view_job[:4]
   if len(view_job)>4:
    doc=ezdxf.readfile(view_job[4]);assert doc.units==4
    entity_boxes=[(ent,bbox.extents([ent])) for ent in doc.modelspace()]
   selected=[]
   for ent,box in entity_boxes:
    if rect is None:selected.append(ent);continue
    inside=box.extmin.x>=rect[0] and box.extmin.y>=rect[1] and box.extmax.x<=rect[2] and box.extmax.y<=rect[3]
    intersects=box.extmax.x>rect[0] and box.extmax.y>rect[1] and box.extmin.x<rect[2] and box.extmin.y<rect[3]
    assert not (intersects and not inside),(job['source'],code,'window clips geometry',ent.dxf.handle)
    if inside:selected.append(ent)
   target=ezdxf.new('R2010');target.units=4;importer=Importer(doc,target);importer.import_entities(selected);importer.finalize()
   for ent in target.modelspace():ent.transform(Matrix44.z_rotate(math.radians(angle)))
   bounds=bbox.extents(target.modelspace());assert all(abs(a-b)<.03 for a,b in zip((bounds.size.x,bounds.size.y),expected)),(job['source'],code,tuple(bounds.size))
   for ent in target.modelspace():ent.transform(Matrix44.translate(-bounds.extmin.x,-bounds.extmin.y,0))
   audit=target.audit();assert not audit.errors and not audit.fixes
   ident='CHINT-'+family+'-'+code;dest=path.parent/'CadDon'/ident;dest.mkdir(parents=True,exist_ok=True)
   drawing=dest/'ban_ve.dxf';target.saveas(drawing)
   backend=svg.SVGBackend();Frontend(RenderContext(target),backend).draw_layout(target.modelspace(),finalize=True)
   (dest/'xem_truoc.svg').write_text(backend.get_string(layout.Page(0,0,layout.Units.mm)),encoding='utf8')
   matplotlib.qsave(target.modelspace(),dest/'preview.png',dpi=90)
   evidence={**source,'view':code,'source_window':rect,'rotation_degrees':angle,'coordinate_scale_to_mm':1,
    'source_entity_count':len(selected),'sha256':digest(drawing)}
   (dest/'evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf8')
   (dest/'thong_tin_cad_chen.json').write_text(json.dumps({'evidence':evidence,'hinh_hoc_lap_dat':{'don_vi':'mm'}},ensure_ascii=False,indent=2),encoding='utf8')
   profile['cad_don'].append({'id_hinh_goc':ident,'huong_nhin':LABELS[code],'nhan_hien_thi':LABELS[code],
    'duong_dan':drawing.relative_to(path.parent).as_posix(),'model_codes':models,'unit_verification':evidence,
    'bo_tri_trong_tu':{'cho_phep_chen':False}})
   relative='catalogtb/'+dest.relative_to(CAT).as_posix()
   record_views.append({'id':ident,'name':LABELS[code],'state':LABELS[code],
    'preview':{'path':relative+'/xem_truoc.svg'},'dxf':{'path':relative+'/ban_ve.dxf'},'placement':{'cho_phep_chen':False}})
   browser_views.append({'id':ident,'label':LABELS[code],'face':LABELS[code],'model_codes':models,
    'preview':f'/equipment-library/{cid}/views/{ident}/preview','download':f'/equipment-library/{cid}/views/{ident}/dxf'})
   health['files'][drawing.relative_to(CAT).as_posix()]={'sha256':digest(drawing),'preview_sha256':digest(dest/'xem_truoc.svg')}
  profile['cad_chen_tu']={k:profile['cad_don'][0][k] for k in ('id_hinh_goc','huong_nhin','duong_dan')}
  path.write_text(json.dumps(profile,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
  overlay['profiles'][cid]={'catalog_tham_khao':refs}
  devices.append({'id':cid,'display':name,'category':'CHINT','brand':'CHINT','brand_kind':'manufacturer',
   'brand_label':'CHINT','product_code':model,'type':kind,'spec':spec,'views':browser_views,
   'primary_view':browser_views[0]['id'],'catalog_references':refs,'auto_select':False,'needs_review':True})
  record={'catalog_id':cid,'record_type':'source_cad_device_or_assembly','display_name':name,'model':model,
   'brand':'CHINT','brand_verified':True,'category':kind,'description':profile['cong_dung'],
   'specifications':{'poles':poles},'price':None,'cad':{'status':'source_cad_unverified_sku','views':record_views,
    'default_view_id':record_views[0]['id'],'preview':record_views[0]['preview'],'dxf':record_views[0]['dxf']},
   'auto_select':False,'evidence':source}
  records.append(record);results.append({'profile':path.relative_to(CAT).as_posix(),'id':cid,'models':models,'views':len(browser_views),'row_ids':[o['source_row_id'] for o in options]})
 # Publish the asset index and the metadata snapshot only after validating views.
 with sqlite3.connect(CAT/'_agent_index/equipment_catalog.sqlite') as db:
  for record in records:
   cid=record['catalog_id'];db.execute('INSERT OR REPLACE INTO equipment VALUES(?,?,?,?,?,?,?,?,?)',
    (cid,'CHINT',record['category'],record['model'],record['display_name'],record['record_type'],None,record['cad']['status'],json.dumps(record,ensure_ascii=False)))
   db.execute('DELETE FROM equipment_fts WHERE catalog_id=?',(cid,))
   db.execute('INSERT INTO equipment_fts VALUES(?,?,?,?,?,?)',(cid,'CHINT',record['category'],record['model'],record['display_name'],record['model']))
 ids={d['id'] for d in devices};snapshot['items']=[d for d in snapshot['items'] if d['id'] not in ids]+devices
 snapshot['total']=len(snapshot['items']);snapshot['view_count']=sum(len(d['views']) for d in snapshot['items'])
 for category in snapshot['categories']:category['count']=sum(d['category']==category['name'] for d in snapshot['items'])
 for target,data in ((health_path,health),(overlay_path,overlay),(snapshot_path,snapshot)):
  pending=target.with_suffix('.tmp');pending.write_text(json.dumps(data,ensure_ascii=False,indent=2 if target!=snapshot_path else None),encoding='utf8');pending.replace(target)
 sync_agent_export(ids)
 (ROOT/'app/data'/report_name).write_text(json.dumps({'reviewed_on':reviewed_on,'items':results},ensure_ascii=False,indent=2),encoding='utf8')
 print(json.dumps({'profiles':len(records),'views':sum(r['views'] for r in results),'row_links':sum(len(r['row_ids']) for r in results)}),flush=True)


if __name__=='__main__':main()
