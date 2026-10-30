"""Publish individually reviewed NM8N-125 bodies, preserving printed ratings."""
import hashlib,json,re,sys
from pathlib import Path
import ezdxf
from ezdxf import bbox
from ls_native_writer import ROOT,CAT,write_profile,price_option
from import_ls_step_family import entities

BASE=CAT/'Chint/NguonBenNgoai/PRIMARY-RECHECK-20261023'
OUT=ROOT/'docs/chint-research-2026-10-23'
MAP1=[('FRONT','SIDE',-90),('REAR','SIDE-L',90),('SIDE-L','BOTTOM',0),('SIDE','TOP',180),('TOP','FRONT',-90),('BOTTOM','REAR',-90)]
MAP3=[('FRONT','TOP',180),('REAR','BOTTOM',180),('SIDE-L','SIDE',-90),('SIDE','SIDE-L',90),('TOP','FRONT',180),('BOTTOM','REAR',0)]
JOBS=[('1P','NM8N-MCCB-Drawing-125-1P',MAP1,True),('3P','NM8N-MCCB-Drawing-125-3P-asm',MAP3,False),('4P','../NM8N-125-4P-REVIEWED-20261023',MAP3,False)]

def main():
 rows=json.loads((ROOT/'app/data/supplier_pricebooks.json').read_text(encoding='utf8'))['items'];result=[];paths=[]
 catalog_folder=CAT/'Chint/NguonBenNgoai/NM8N-CATALOG';catalog=json.loads((catalog_folder/'source.json').read_text(encoding='utf8'))
 for poles,folder,mapping,fixed125 in JOBS:
  if len(sys.argv)>1 and poles not in sys.argv[1:]:continue
  src=BASE/folder;source=json.loads((src/'source.json').read_text(encoding='utf8'))
  assert source['review_status']=='six_views_axes_and_dimensions_visually_verified'
  views,prefix=entities('PRIMARY-RECHECK-20261023/'+folder,mapping,'Chint');assert len(views)==6
  b={c:bbox.extents(es).size for c,_,es in views};size=[b['FRONT'].x,b['FRONT'].y,b['SIDE'].x]
  assert abs(size[0]-({'1P':35,'3P':90,'4P':120}[poles]))<.3 and abs(size[1]-140)<1.3 and abs(size[2]-108.5)<.2,size
  matched=[r for r in rows if r['brand']=='CHINT' and r['category']=='MCCB' and re.fullmatch(r'NM8N-125[CSH] TM \d+ '+('4C' if poles=='4P' else poles),r['sku']) and (not fixed125 or r['specifications'].get('In')=='125A')]
  assert len(matched)==(1 if fixed125 else 30)
  models=sorted({r['sku'].split()[0] for r in matched});dims=' × '.join(format(round(v,3),'g') for v in size)
  voltage='220/230/240 V AC' if fixed125 else '380/400/415 V AC'
  spec={'Kích thước CAD W×H×D (mm)':dims,'Kích thước thân W×H×D (mm)':str({'1P':35,'3P':90,'4P':120}[poles])+' × 140 × 78.5','Dòng định mức In (A)':'125' if fixed125 else '16–125','Điện áp công bố Icu/Ics':voltage,'Icu / Ics tại '+voltage:'36 / 36 kA (C)' if fixed125 else 'C: 36 / 36 kA; S: 50 / 50 kA; H: 100 / 100 kA','Kiểu lắp':'Cố định trên tấm lắp; đấu nối phía trước','Vị trí thường lắp':'Ngăn phân phối điện, bảo vệ lộ nguồn hoặc lộ ra','Cơ cấu bảo vệ':'Nhiệt từ TM','Tiêu chuẩn':'IEC/EN 60947-2'}
  source.update(six_views_verified=True,complete_manufacturer_step_projection=True,step_sha256=hashlib.sha256((src/'source.step').read_bytes()).hexdigest(),axis_mapping=mapping,unit_evidence='Original STEP imported MM; output DXF INSUNITS=4; six opposed extents checked without rescaling',technical_source_url=catalog['source_url'],technical_source_sha256=hashlib.sha256((catalog_folder/'source.pdf').read_bytes()).hexdigest(),technical_source_pages=[4,21,22,24],native_complete_envelope_mm=size,nominal_body_mm=[{'1P':35,'3P':90,'4P':120}[poles],140,78.5],nominal_depth_with_operating_handle_mm=108.5,electrical_rating_from_geometry=False,printed_rating_restriction='Original 1P side embossing reads 125A; only 125 A price row linked' if fixed125 else 'Native 3P/4P exterior has no current or breaking-capacity value; reviewed TM frame options only; 4C neutral protection must be selected by exact ordering code, never inferred from exterior CAD; no DC or rear/plug-in variants',geometry_review='Original full exterior with handle, screws and terminals retained; front line terminals 1/3/5 above load 2/4/6; no extracted material added or removed')
  family='NM8N-125-'+poles+('-125A' if fixed125 else '-TM')
  name='CHINT · MCCB · NM8N-125 · '+poles+' · '+('125 A · 36 kA' if fixed125 else '16–125 A · 36/50/100 kA')
  options=[]
  for row in matched:
   option=price_option(row,brand='CHINT');option['specifications']['Điện áp công bố Icu/Ics']=voltage;options.append(option)
  p=write_profile(family,name,'MCCB',models,poles,options,views,source,spec,brand='CHINT');raw=json.loads(p.read_text(encoding='utf8'));raw['catalog_tham_khao']['source_row_scope']='explicit_only';raw['cong_dung']='Đóng cắt và bảo vệ quá tải, ngắn mạch cho mạch phân phối điện.';p.write_text(json.dumps(raw,ensure_ascii=False,indent=2)+'\n',encoding='utf8');paths.append(p)
  result.append({'profile':p.relative_to(CAT).as_posix(),'poles':poles,'dimensions_mm':dims,'price_row_ids':[r['id'] for r in matched],'skus':[r['sku'] for r in matched],'views':6,'voltage':voltage,'printed_current_restriction_a':125 if fixed125 else None})
 ledger=ROOT/'app/data/catalog_verified_view_health.json';health=json.loads(ledger.read_text(encoding='utf8'))
 for p in paths:
  for f in p.parent.glob('CadDon/*/ban_ve.dxf'):
   d=ezdxf.readfile(f);audit=d.audit();assert d.units==4 and not audit.errors and not audit.fixes
   health['files'][f.relative_to(CAT).as_posix()]={'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'preview_sha256':hashlib.sha256(f.with_name('xem_truoc.svg').read_bytes()).hexdigest()}
 ledger.write_text(json.dumps(health,ensure_ascii=False,indent=2),encoding='utf8')
 report_path=OUT/'nm8n125-import.json'
 if len(sys.argv)>1 and report_path.exists():
  replaced={r['poles'] for r in result};result=[r for r in json.loads(report_path.read_text(encoding='utf8'))['items'] if r['poles'] not in replaced]+result
 (OUT/'nm8n125-import.json').write_text(json.dumps({'items':result,'families':len(result),'views':sum(r['views'] for r in result),'price_rows':sum(len(r['price_row_ids']) for r in result),'held':{'2P':'Source side embossing reads 160A despite NM8N-125 source filename; do not attach 16–125 A price rows.'}},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 from publish_abb_ct_index import main as publish_index
 publish_index([p.parent.name for p in paths],report_name='chint-full-faces-2026-10-21',brand='CHINT',category='MCCB',profile_root='Chint/ThietBi',refresh=False)

if __name__=='__main__':main()
