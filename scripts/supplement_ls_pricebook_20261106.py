"""Publish LS catalogue geometry for exact rows of the selected October book.

These are dimension-calibrated catalogue references, not manufacturing CAD.
Only actually illustrated pole fronts are published; single-pole end drawings
are not repeated across multi-pole bodies. Partial references never authorize
automatic cabinet insertion or transfer electrical ratings into the pricebook.
"""
import hashlib,json,shutil,sqlite3,sys
from pathlib import Path
import ezdxf
from ezdxf.addons.drawing import Frontend,RenderContext,svg,layout,matplotlib

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.chint_pdf_geometry import vector_view
from scripts.supplement_chint_native2d import sync_agent_export
from app.services.price_row_cad_detail import row_configuration_digest
from app.services.catalog_product_sections import pole_compatible
CAT=ROOT/'data/CatalogTB';BASE=CAT/'LS/NguonBenNgoai/PRICEBOOK-REVIEW-20261106'
ROWS=[r for r in json.loads((ROOT/'app/data/supplier_pricebooks.json').read_text(encoding='utf8'))['items'] if r['brand']=='LS Electric']
LABELS={'FRONT':'Mặt trước','SIDE':'Mặt bên','TOP':'Mặt trên','REAR':'Mặt sau','MOUNTING':'Mặt đế gá theo bản vẽ','CUTOUT':'Lỗ khoét cánh','SIDE-L':'Mặt bên trái','BOTTOM':'Mặt dưới'}


def jobs():
 result=[]
 fronts63=[(151.3,657.4,170.3,745),(192.2,657.4,228.9,745),(241.7,657.4,296.1,745),(308.5,657.4,380.6,745)]
 fronts125=[(204.3,599.4,226.8,671.1),(262.1,599.4,306,671.1),(332.1,599.4,397.4,671.1),(422.4,599.4,509.1,671.1)]
 for poles in range(1,5):
  models=[f'LA63{s} {poles}P' for s in ('N','H','L')]
  views=[('FRONT',12,fronts63[poles-1],17.6*poles,83),('SIDE',12,(401.5,657.4,477.3,745),72,83)]
  if poles==1:views.append(('TOP',12,(498.4,657.5,517.3,734.5),17.6,72))
  result.append((f'LA63-N-H-L-{poles}P',models,f'{poles}P',[17.6*poles,83,72],views))
  views=[('FRONT',23,fronts125[poles-1],26.7*poles,83),('SIDE',23,(346.3,681.3,406.7,753),72,83)]
  if poles==1:views.append(('TOP',23,(454.8,685.1,477.4,745.5),26.7,72))
  result.append((f'LA125H-{poles}P',[f'LA125H {poles}P'],f'{poles}P',[26.7*poles,83,72],views))
 result.append(('LB63N-1PN',['LB63N 1P+N'],'1P+N',[35.6,83,72],
  [('FRONT',42,(180.1,616.9,226.9,729.2),35.6,83),('SIDE',42,(288.9,616.8,384.7,729.3),72,83),('TOP',42,(437.1,622.4,483.7,718),35.6,72)]))
 for key,models,y0,y1 in [('AX',['Auxiliary switch: AX for LA/LC','Auxiliary switch: AX for LB'],338.4,406.3),('AL',['Alarm switch: AL for LA/LC','Alarm switch: AL for LB'],688.2,756.1)]:
  result.append(('L-SERIES-'+key,models,None,[8.8,83,72],[('FRONT',65,(263.8,y0,275.9,y1),8.8,83),('SIDE',65,(306.4,y0,367,y1),72,83)]))
 result.append(('L-SERIES-SHT',['Shunt for LA/LC','Shunt for LB'],None,[17.6,83,72],
  [('FRONT',66,(244.1,324,263.1,391.1),17.6,83),('SIDE',66,(286.1,324,346,391.1),72,83)]))
 return result


def main(review_jobs=None,report_name='ls_october_geometry_review.json'):
 health_path=ROOT/'app/data/catalog_verified_view_health.json';health=json.loads(health_path.read_text(encoding='utf8'))
 overlay_path=ROOT/'app/data/catalogtb_published_information.json';overlay=json.loads(overlay_path.read_text(encoding='utf8'))
 results=[];records=[];paths=[]
 for entry in (jobs() if review_jobs is None else review_jobs):
  key,models,poles,size,view_specs=entry[:5]
  pdf=Path(entry[5]) if len(entry)>5 else BASE/'l-series.pdf'
  source=json.loads(pdf.with_suffix('.json').read_text(encoding='utf8'))
  assert hashlib.sha256(pdf.read_bytes()).hexdigest()==source['sha256']
  selected=[r for r in ROWS if r['sku'] in models];assert selected and {r['sku'] for r in selected}==set(models),key
  if poles:assert all(pole_compatible({'spec':{'so_cuc':poles}},r) for r in selected)
  folder=CAT/'LS/ThietBi'/('OFFICIAL-PDF-'+key);folder.mkdir(parents=True,exist_ok=True);path=folder/'thong_tin_thiet_bi.json'
  cid='TB-'+hashlib.sha1(path.relative_to(CAT).as_posix().encode()).hexdigest()[:16];model=' / '.join(models);kind=selected[0]['category']
  restriction='Manufacturer LS L-Series catalogue illustrates this exact model family and pole front. Width/height calibrate catalogue art to printed millimetres; drawn internal details remain schematic. No mirrored, stretched or repeated single-pole front is used to invent another pole count. Only verified views are published. Price-row electrical ratings and VAT remain those of the uploaded October pricebook. This partial reference does not authorize fabrication or automatic insertion.'
  if len(entry)>6:restriction=entry[6]
  settings=entry[7] if len(entry)>7 else {}
  info={**source,'geometry_representation':'Dimension-calibrated catalogue reference','pdf_pages':sorted({v[1] for v in view_specs}),'reviewed_on':'2026-11-06','restriction':restriction,'exact_sku_approval':False}
  info['geometry_representation']=settings.get('geometry_representation',info['geometry_representation'])
  options=[{'brand':'LS Electric','model':r['sku'],'source_row_id':r['id'],'specifications':r['specifications'],'source_url':r['source_url'],'source_page':r['source_page'],
    'basis':'reviewed_ls_october_pdf_geometry','exact_cad_match':False,'source_row_configuration_sha256':row_configuration_digest(r),
    'reviewed_device_model':model,'reviewed_device_poles':poles,'geometry_compatibility_review':{'assessment':restriction,'electrical_equivalence':False}} for r in selected]
  refs={'category':kind,'options':options,'source_row_scope':'explicit_only','row_links_reviewed':True}
  name=settings.get('name') or 'LS '+(' / '.join(models) if poles else 'L-Series '+key.rsplit('-',1)[-1])
  profile={'nhom':'LS','hang_xac_nhan':'LS Electric','ma_dong_san_pham':model,'ten_san_pham':name,'ten_kieu':name,'ban_chat':kind,
   'cong_dung':'Bản vẽ tham chiếu bố trí thiết bị theo catalogue hãng.','thong_so':{**({'so_cuc':poles} if poles else {}),'Kiểu lắp':'Ray DIN 35 mm','Kích thước bản vẽ W×H×D (mm)':' × '.join(map(str,size))},
   'catalog_tham_khao':refs,'auto_select':False,'needs_review':True,'nhan_dien_ai':{'loai_thiet_bi_code':kind,'cac_ma_dong_san_pham':models,'exact_SKU_confirmed':False},
   'nguon_tham_khao':[source['source_url']],'source_catalog_review':info,'cad_don':[]}
  profile['thong_so'].update(settings.get('extra_spec') or {})
  profile['thong_so']['Kiểu lắp']=settings.get('mounting_type','Theo bản vẽ tham chiếu của hãng')
  index_views=[]
  for view_spec in view_specs:
   code,page,window,width,height=view_spec[:5]
   if len(view_spec)>5:
    raw=Path(view_spec[5]);calibration={'source_pdf_page':page,'documented_width_mm':width,'documented_height_mm':height,'method':'Dimension-based reference or reviewed native view; see restriction','source_dxf_sha256':hashlib.sha256(raw.read_bytes()).hexdigest(),'source_dxf':raw.relative_to(CAT).as_posix()}
   else:
    raw=BASE/(key+'-'+code+'.dxf');calibration=vector_view(pdf,page,window,width,raw,physical_height_mm=height,require_whole_paths=settings.get('require_whole_paths',True))
   label=(settings.get('view_labels') or {}).get(code,LABELS[code])
   ident='LS-PDF-'+key+'-'+code;dest=folder/'CadDon'/ident;dest.mkdir(parents=True,exist_ok=True);drawing=dest/'ban_ve.dxf';shutil.copyfile(raw,drawing)
   doc=ezdxf.readfile(drawing);audit=doc.audit();assert doc.units==4 and not audit.errors and not audit.fixes
   backend=svg.SVGBackend();Frontend(RenderContext(doc),backend).draw_layout(doc.modelspace(),finalize=True)
   (dest/'xem_truoc.svg').write_text(backend.get_string(layout.Page(0,0,layout.Units.mm)),encoding='utf8');matplotlib.qsave(doc.modelspace(),dest/'preview.png',dpi=95)
   evidence={**info,'vector_calibration':calibration,'sha256':hashlib.sha256(drawing.read_bytes()).hexdigest(),'view':code,'coordinate_scale_to_mm':1}
   (dest/'evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf8')
   (dest/'thong_tin_cad_chen.json').write_text(json.dumps({'evidence':evidence,'hinh_hoc_lap_dat':{'don_vi':'mm'}},ensure_ascii=False,indent=2),encoding='utf8')
   profile['cad_don'].append({'id_hinh_goc':ident,'huong_nhin':label,'nhan_hien_thi':label,'duong_dan':drawing.relative_to(folder).as_posix(),'model_codes':models,'unit_verification':evidence,'bo_tri_trong_tu':{'cho_phep_chen':False}})
   rel='catalogtb/'+dest.relative_to(CAT).as_posix();index_views.append({'id':ident,'name':label,'state':label,'preview':{'path':rel+'/xem_truoc.svg'},'dxf':{'path':rel+'/ban_ve.dxf'},'placement':{'cho_phep_chen':False}})
   health['files'][drawing.relative_to(CAT).as_posix()]={'sha256':evidence['sha256'],'preview_sha256':hashlib.sha256((dest/'xem_truoc.svg').read_bytes()).hexdigest()}
  profile['cad_chen_tu']={k:profile['cad_don'][0][k] for k in ('id_hinh_goc','huong_nhin','duong_dan')}
  path.write_text(json.dumps(profile,ensure_ascii=False,indent=2)+'\n',encoding='utf8');paths.append(path)
  overlay['profiles'][cid]={'catalog_tham_khao':refs}
  records.append({'catalog_id':cid,'record_type':'source_cad_device_or_assembly','display_name':name,'model':model,'brand':'LS Electric','brand_verified':True,'category':kind,'description':profile['cong_dung'],'specifications':{'poles':poles},'price':None,'cad':{'status':'source_cad_unverified_sku','views':index_views,'default_view_id':index_views[0]['id'],'preview':index_views[0]['preview'],'dxf':index_views[0]['dxf']},'auto_select':False,'evidence':info})
  results.append({'id':cid,'profile':path.relative_to(CAT).as_posix(),'models':models,'views':len(index_views),'row_ids':[r['id'] for r in selected]})
 for target,data in ((health_path,health),(overlay_path,overlay)):
  pending=target.with_suffix('.tmp');pending.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8');pending.replace(target)
 with sqlite3.connect(CAT/'_agent_index/equipment_catalog.sqlite') as db:
  for r in records:
   db.execute('INSERT OR REPLACE INTO equipment VALUES(?,?,?,?,?,?,?,?,?)',(r['catalog_id'],'LS Electric',r['category'],r['model'],r['display_name'],r['record_type'],None,r['cad']['status'],json.dumps(r,ensure_ascii=False)))
   db.execute('DELETE FROM equipment_fts WHERE catalog_id=?',(r['catalog_id'],));db.execute('INSERT INTO equipment_fts VALUES(?,?,?,?,?,?)',(r['catalog_id'],'LS Electric',r['category'],r['model'],r['display_name'],r['model']))
 ids={r['catalog_id'] for r in records};sync_agent_export(ids)
 from unittest.mock import patch
 from app.services.catalogtb_browser import _build_browser_data
 original=Path.rglob
 def limited(self,pattern,*args,**kw):return iter(paths) if self==CAT and pattern=='thong_tin_thiet_bi.json' else original(self,pattern,*args,**kw)
 with patch.object(Path,'rglob',limited):rebuilt=_build_browser_data()
 assert {d['id'] for d in rebuilt['items']}==ids
 snapshot_path=CAT/'_agent_index/browser_display_v5.json';snapshot=json.loads(snapshot_path.read_text(encoding='utf8'))
 snapshot['items']=[d for d in snapshot['items'] if d['id'] not in ids]+rebuilt['items'];snapshot['total']=len(snapshot['items']);snapshot['view_count']=sum(len(d['views']) for d in snapshot['items'])
 for category in snapshot['categories']:category['count']=sum(d['category']==category['name'] for d in snapshot['items'])
 pending=snapshot_path.with_suffix('.tmp');pending.write_text(json.dumps(snapshot,ensure_ascii=False),encoding='utf8');pending.replace(snapshot_path)
 (ROOT/'app/data'/report_name).write_text(json.dumps({'checked_on':'2026-11-06','items':results},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 print(json.dumps({'profiles':len(results),'views':sum(r['views'] for r in results),'row_links':sum(len(r['row_ids']) for r in results)}),flush=True)

if __name__=='__main__':main()
