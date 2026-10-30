"""Import reviewed overload-relay bodies; retain setting and terminal variants."""
import json,hashlib,re
from pathlib import Path
from ls_native_writer import ROOT,CAT,write_profile,price_option
from import_ls_step_family import entities,LABELS
from ezdxf import bbox
import ezdxf
BASE=CAT/'Chint/NguonBenNgoai';OUT=ROOT/'docs/chint-research-2026-10-23'
MAP12=[('FRONT','FRONT',180),('REAR','REAR',180),('SIDE-L','SIDE',180),('SIDE','SIDE-L',180),('TOP','BOTTOM',180),('BOTTOM','TOP',180)]
MAP38=[('FRONT','SIDE',-90),('REAR','SIDE-L',90),('SIDE-L','BOTTOM',0),('SIDE','TOP',180),('TOP','FRONT',-90),('BOTTOM','REAR',-90)]
MAP630=[('FRONT','BOTTOM',-90),('REAR','TOP',-90),('SIDE-L','REAR',90),('SIDE','FRONT',-90),('TOP','SIDE-L',0),('BOTTOM','SIDE',180)]
JOBS={'12':{'source':'PRIMARY-RECHECK-20261023/NXR-12-Thermal-Over-load-Relay-Drawing','mapping':MAP12,'nominal':[45,73,68]},'38':{'source':'PRIMARY-RECHECK-20261023/NXR-38-Thermal-Over-load-Relay-Drawing','mapping':MAP38,'nominal':[55,82,94]},'100':{'source':'NXR-100-INSTALLED-20261023','mapping':[(c,c,0) for c in LABELS],'nominal':[72,87,117]},'630':{'source':'PRIMARY-RECHECK-20261023/NXR-630-Thermal-Over-load-Relay-Drawing','mapping':MAP630,'nominal':[158.6,155.7,161.3],'material_code':'837133','variant':'125-400A'}}

def main():
 rows=json.loads((ROOT/'app/data/supplier_pricebooks.json').read_text(encoding='utf8'))['items'];paths=[];result=[]
 catalog_path=BASE/'PRIMARY-RECHECK-20261023/NXR-CATALOG';catalog=json.loads((catalog_path/'source.json').read_text(encoding='utf8'))
 for frame,job in JOBS.items():
  source_folder=BASE/job['source'];source=json.loads((source_folder/'source.json').read_text(encoding='utf8'));assert source.get('review_status')=='six_views_axes_and_dimensions_visually_verified'
  views,prefix=entities(job['source'],job['mapping'],'Chint');assert len(views)==6;b={c:bbox.extents(es).size for c,l,es in views};size=[b['FRONT'].x,b['FRONT'].y,b['SIDE'].x];assert all(abs(a-n)<=max(3,.04*n) for a,n in zip(size,job['nominal'])),(frame,size,job['nominal'])
  model='NXR-'+frame;matched=[r for r in rows if r['brand']=='CHINT' and r['category']=='THERMAL_RELAY' and r['sku'].startswith(model+' ') and (not job.get('material_code') or r['specifications'].get('Mã hàng')==job['material_code'])];assert matched
  expected={'12':12,'38':2,'100':8,'630':1}[frame];assert len(matched)==expected
  values=[float(n) for r in matched for n in re.findall(r'\d+(?:\.\d+)?',r['specifications']['Dải chỉnh định Ir (A)'])];setting=format(min(values),'g')+'–'+format(max(values),'g');dims=' × '.join(format(round(v,2),'g') for v in size)
  spec={'Kích thước CAD W×H×D (mm)':dims,'Dải chỉnh định Ir (A)':setting,'Tiếp điểm phụ':'1NO+1NC','Tiêu chuẩn':'IEC/EN 60947-4-1; IEC/EN 60947-5-1','Vị trí thường lắp':'Ngăn bảo vệ động cơ, trên tuyến động lực' if frame=='630' else 'Ngăn điều khiển động cơ, ghép với contactor','Kiểu lắp':'Gá vít độc lập trên tấm lắp' if frame=='630' else 'Lắp trực tiếp vào contactor phù hợp'}
  if frame=='630':spec['Bước đầu nối động lực (mm)']='48';source['terminal_variant_evidence']={'source_pdf':catalog['source_url'],'pdf_page':7,'actual_main_bolt_centers_x_mm':[-48,0,48],'actual_main_bolt_rows_y_mm':[-63.5,63.5],'native_bolt_hole_radius_mm':5,'matching_variant':'400A terminal configuration, setting 125–400 A','excluded_setting':'200–630 A: manufacturer drawing specifies different terminal pitch','basis':'Six main bolt holes fitted from original projected circular contours; identity comes from the named original NXR-630 manufacturer source and supplier model column, not from geometry alone.'}
  source.update(six_views_verified=True,complete_manufacturer_step_projection=True,step_sha256=hashlib.sha256((source_folder/'source.step').read_bytes()).hexdigest(),unit_evidence='Original manufacturer STEP in mm; imported MM and output DXF INSUNITS=4; all six opposed extents checked',axis_mapping=job['mapping'],technical_source_url=catalog['source_url'],technical_source_sha256=catalog['sha256'],technical_source_pages=[1,5,6,7],native_full_envelope_mm=size,nominal_catalog_mm=job['nominal'],electrical_rating_from_geometry=False)
  family=model+('-'+job['variant'] if job.get('variant') else '')+'-3P';label=model+(' · '+setting+' A' if frame=='630' else '')
  p=write_profile(family,'CHINT · Rơ-le nhiệt · '+label+' · 3P','THERMAL_RELAY',[model],'3P',[{**price_option(r,brand='CHINT'),'basis':'exact_named_manufacturer_step_family'} for r in matched],views,source,spec,brand='CHINT');paths.append(p)
  raw=json.loads(p.read_text(encoding='utf8'));raw['catalog_tham_khao']['source_row_scope']='explicit_only';raw['cong_dung']='Bảo vệ động cơ ba pha khi quá tải hoặc mất pha, tác động mạch điều khiển contactor.';p.write_text(json.dumps(raw,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
  result.append({'profile':p.relative_to(CAT).as_posix(),'model':model,'price_row_ids':[r['id'] for r in matched],'skus':[r['sku'] for r in matched],'dimensions_mm':dims,'setting_a':setting,'views':6,'terminal_pitch_mm':48 if frame=='630' else None})
 ledger=ROOT/'app/data/catalog_verified_view_health.json';health=json.loads(ledger.read_text(encoding='utf8'))
 for path in paths:
  for f in path.parent.glob('CadDon/*/ban_ve.dxf'):
   d=ezdxf.readfile(f);a=d.audit();assert d.units==4 and not a.errors and not a.fixes;health['files'][f.relative_to(CAT).as_posix()]={'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'preview_sha256':hashlib.sha256(f.with_name('xem_truoc.svg').read_bytes()).hexdigest()}
 ledger.write_text(json.dumps(health,ensure_ascii=False,indent=2),encoding='utf8');(OUT/'nxr-import.json').write_text(json.dumps({'items':result,'families':4,'views':24,'price_rows':23,'held':{'NXR-25':'No exact native manufacturer STEP found; NXR-38 has different body dimensions, never substitute it.','NXR-200':'Native assembly 128 x 134 x 141.2 mm vs manufacturer catalog 128 x 142 x 148 mm; terminal/assembly configuration unresolved.','NXR-630 200–630 A':'Terminal pitch differs from the 48 mm original CAD; do not reuse the 125–400 A body.'}},ensure_ascii=False,indent=2),encoding='utf8')
 from publish_abb_ct_index import main as publish_index
 publish_index([p.parent.name for p in paths],report_name='chint-full-faces-2026-10-21',brand='CHINT',category='THERMAL_RELAY',profile_root='Chint/ThietBi',refresh=False)

if __name__=='__main__':main()
