"""Publish only individually reviewed NXC axes, dimensions, coils and price IDs."""
import hashlib,json,re,sys
from pathlib import Path
from ls_native_writer import CAT,ROOT,write_profile,price_option
from import_ls_step_family import entities
from ezdxf import bbox
import ezdxf
BASE=CAT/'Chint/NguonBenNgoai/PRIMARY-RECHECK-20261023'
OUT=ROOT/'docs/chint-research-2026-10-23'
MAP06=[('FRONT','FRONT',90),('REAR','REAR',-90),('SIDE-L','TOP',90),('SIDE','BOTTOM',90),('TOP','SIDE',90),('BOTTOM','SIDE-L',90)]
MAP18=[('FRONT','SIDE',90),('REAR','SIDE-L',-90),('SIDE-L','TOP',0),('SIDE','BOTTOM',180),('TOP','REAR',90),('BOTTOM','FRONT',90)]
MAP25=[('FRONT','SIDE-L',90),('REAR','SIDE',-90),('SIDE-L','TOP',180),('SIDE','BOTTOM',0),('TOP','FRONT',90),('BOTTOM','REAR',90)]
MAP225=[('FRONT','REAR',0),('REAR','FRONT',0),('SIDE-L','SIDE',0),('SIDE','SIDE-L',0),('TOP','TOP',180),('BOTTOM','BOTTOM',180)]
MAP40=[('FRONT','FRONT',-90),('REAR','REAR',90),('SIDE-L','BOTTOM',-90),('SIDE','TOP',-90),('TOP','SIDE-L',-90),('BOTTOM','SIDE',-90)]
MAP400=[('FRONT','SIDE',180),('REAR','SIDE-L',180),('SIDE-L','REAR',180),('SIDE','FRONT',180),('TOP','BOTTOM',-90),('BOTTOM','TOP',90)]
MAP500=[('FRONT','SIDE-L',0),('REAR','SIDE',0),('SIDE-L','REAR',0),('SIDE','FRONT',0),('TOP','TOP',90),('BOTTOM','BOTTOM',-90)]
# New mappings may only be added after examining all six original projections.
JOBS={'06-16':{'models':['06','09','12','16'],'mapping':MAP06,'nominal_mm':[45.5,75,88]},'18-22':{'models':['18','22'],'mapping':MAP18,'nominal_mm':[45.5,75,88]},'25-38':{'models':['25','32','38'],'mapping':MAP25,'nominal_mm':[56.5,87,93]},'225':{'models':['225'],'mapping':MAP225,'nominal_mm':[127,182,156]}}
JOBS.update({'40-65':{'models':['40'],'mapping':MAP40,'nominal_mm':[77,129,118],'publication_key':'40','restriction':'Native front plate explicitly reads NXC-40; NXC-50 and NXC-65 require their own correctly labelled front source.'},'75-100':{'models':['75','85','100'],'mapping':MAP18,'nominal_mm':[87,132,127]},'265-400':{'models':['400'],'mapping':MAP400,'nominal_mm':[150,236,207],'publication_key':'400','restriction':'Native front plate explicitly reads NXC-400; do not relabel this native geometry NXC-265 or NXC-330.'},'500-630':{'models':['500','630'],'mapping':MAP500,'nominal_mm':[165,248,225]}})
JOBS['500-630']['held']='Full projected height 227.8 mm vs 248 mm catalog maximum; terminal/casing configuration requires reconciliation before price mapping.'
JOBS['120']={'models':['120'],'mapping':MAP225,'nominal_mm':[127,182,156],'held':'Exact BRep side projection has isolated long artifacts; front height 179.6 vs side height 234.356 mm. Opposed-view envelope invariant failed. Preserve native source; do not reuse NXC-225 geometry for NXC-120.'}

def main():
 OUT.mkdir(exist_ok=True);rows=json.loads((ROOT/'app/data/supplier_pricebooks.json').read_text(encoding='utf8'))['items'];paths=[];result=[]
 catalog=json.loads((BASE/'NXC-CATALOG/source.json').read_text(encoding='utf8'))
 for group,job in JOBS.items():
  if len(sys.argv)>1 and group not in sys.argv[1:]:continue
  if job.get('held'):continue
  folder=BASE/f'NXC-{group}-AC-Contactor-Drawing';source=json.loads((folder/'source.json').read_text(encoding='utf8'))
  assert source.get('review_status')=='six_views_axes_and_dimensions_visually_verified',group
  views,prefix=entities(folder.relative_to(CAT/'Chint/NguonBenNgoai').as_posix(),job['mapping'],'Chint');assert views and len(views)==6
  b={c:bbox.extents(es).size for c,l,es in views};size=[b['FRONT'].x,b['FRONT'].y,b['SIDE'].x]
  assert all(abs(a-n)<=max(3,.04*n) for a,n in zip(size,job['nominal_mm'])),(group,size,job['nominal_mm'])
  models=['NXC-'+m for m in job['models']];matched=[r for r in rows if r['brand']=='CHINT' and r['category']=='CONTACTOR' and re.match(r'^(?:'+ '|'.join(re.escape(m) for m in models)+r')(?=\s|$)',r['sku'])]
  assert len(matched)==len(models) and all((r.get('specifications') or {}).get('Số cực')=='3P' for r in matched)
  universal=int(job['models'][0])>=265
  assert all(('AC/DC' in r['sku'])==universal for r in matched),(group,matched)
  source.update(source_url=source['source_url'],six_views_verified=True,complete_manufacturer_step_projection=True,step_sha256=hashlib.sha256((folder/'source.step').read_bytes()).hexdigest(),axis_mapping=job['mapping'],unit_evidence='Manufacturer STEP imported MM; DXF INSUNITS=4; complete native dimensions checked against NXC catalog pages 12–13',technical_source_url=catalog['source_url'],technical_source_sha256=catalog['sha256'],technical_source_pages=[1,4,5,6,12,13],nominal_catalog_maximum_mm=job['nominal_mm'],native_complete_envelope_mm=size,sku_approval=False)
  dims=' × '.join(format(round(v,2),'g') for v in size)
  spec={'Kích thước CAD W×H×D (mm)':dims,'Kiểu lắp':'Gá vít trên tấm lắp' if int(job['models'][0])>=120 else 'Gá ray DIN hoặc gá vít trên tấm lắp','Vị trí thường lắp':'Ngăn điều khiển tải, động cơ','Điện áp cuộn hút':'220–240 V AC/DC' if universal else '220 V AC, 50/60 Hz','Dòng làm việc Ie AC-3 (A)':' / '.join(str(int(m)) for m in job['models'])}
  aux={str(r['specifications'].get('Tiếp điểm') or '') for r in matched}
  if len(aux)==1 and next(iter(aux)):spec['Tiếp điểm phụ']=next(iter(aux))
  label=group if len(models)>1 else job['models'][0]
  if job.get('restriction'):source['printed_model_restriction']=job['restriction']
  p=write_profile('NXC-'+job.get('publication_key',group)+'-3P',f'CHINT · Contactor · NXC-{label} · 3P','CONTACTOR',models,'3P',[{**price_option(r,brand='CHINT'),'basis':'exact_named_manufacturer_step_family'} for r in matched],views,source,spec,brand='CHINT');paths.append(p)
  raw=json.loads(p.read_text(encoding='utf8'));raw['catalog_tham_khao']['source_row_scope']='explicit_only';raw['cong_dung']='Đóng cắt và điều khiển tải động cơ bằng cuộn hút.';p.write_text(json.dumps(raw,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
  result.append({'profile':p.relative_to(CAT).as_posix(),'group':group,'models':models,'price_row_ids':[r['id'] for r in matched],'skus':[r['sku'] for r in matched],'dimensions_mm':dims,'nominal_catalog_maximum_mm':job['nominal_mm'],'views':6,'coil':spec['Điện áp cuộn hút'],'mounting':spec['Kiểu lắp']})
 health_path=ROOT/'app/data/catalog_verified_view_health.json';health=json.loads(health_path.read_text(encoding='utf8'))
 for path in paths:
  for f in path.parent.glob('CadDon/*/ban_ve.dxf'):
   d=ezdxf.readfile(f);a=d.audit();assert d.units==4 and not a.errors and not a.fixes
   health['files'][f.relative_to(CAT).as_posix()]={'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'preview_sha256':hashlib.sha256(f.with_name('xem_truoc.svg').read_bytes()).hexdigest()}
 health_path.write_text(json.dumps(health,ensure_ascii=False,indent=2),encoding='utf8')
 report_path=OUT/'nxc-import.json'
 if len(sys.argv)>1 and report_path.exists():
  replaced={r['group'] for r in result};result=[r for r in json.loads(report_path.read_text(encoding='utf8'))['items'] if r['group'] not in replaced]+result
 report_path.write_text(json.dumps({'items':result,'families':len(result),'views':6*len(result),'price_rows':sum(len(r['price_row_ids']) for r in result),'held':{g:j['held'] for g,j in JOBS.items() if j.get('held')}},ensure_ascii=False,indent=2),encoding='utf8')
 from publish_abb_ct_index import main as publish_index
 publish_index([p.parent.name for p in paths],report_name='chint-full-faces-2026-10-21',brand='CHINT',category='CONTACTOR',profile_root='Chint/ThietBi',refresh=False)

if __name__=='__main__':main()
