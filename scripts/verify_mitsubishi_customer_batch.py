"""Reconcile native six-view imports with source price rows and public output."""
import hashlib,json,sys,collections
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
CAT=ROOT/'data/CatalogTB'
from app.services.customer_equipment_information import customer_device,customer_information_rows
from app.services.library_catalog_information import information_rows,source_rows
from app.services.cad.ls_view_coverage import view_coverage
from app.services.catalog_publication_policy import public_device_allowed

def main():
 data=json.loads((CAT/'_agent_index/browser_display_v5.json').read_text(encoding='utf8'))
 devices={d['id']:d for d in data['items']};source=[r for r in source_rows() if r.get('brand')=='Mitsubishi Electric'];report=[];all_ids=set()
 for path in sorted((CAT/'Mitsubishi/ThietBi').glob('OFFICIAL-STEP-*/thong_tin_thiet_bi.json')):
  raw=json.loads(path.read_text(encoding='utf8'));cid='TB-'+hashlib.sha1(path.relative_to(CAT).as_posix().encode()).hexdigest()[:16]
  assert cid in devices,(cid,'not published');d=devices[cid]
  assert len(d['views'])==6 and view_coverage(d['views'])['complete'],(cid,'incomplete')
  public=customer_device(d);assert len(public['views'])==6 and public_device_allowed(public)
  assert all(v.get('spec') for v in public['views']),(cid,'missing dimensions')
  ids={o['source_row_id'] for o in raw['catalog_tham_khao']['options']};all_ids.update(ids)
  information=information_rows(d,source);public_rows=customer_information_rows(information,d)
  got={r['sku'] for r in public_rows};expected={o['model'] for o in raw['catalog_tham_khao']['options']}
  assert expected<=got,(cid,'missing price SKUs',sorted(expected-got))
  assert all(r.get('price') is None or isinstance(r['price'],(int,float)) for r in public_rows)
  report.append({'id':cid,'model':d['product_code'],'views':6,'price_rows':len(ids),'customer_skus':len(got)})
  if len(report)%25==0:print('Verified Mitsubishi customer families',len(report),flush=True)
 assert len(report)==230,len(report)
 result={'families':len(report),'views':len(report)*6,'unique_price_rows':len(all_ids),'all_customer_price_skus_verified':True,'items':report}
 (ROOT/'docs/mitsubishi-customer-verification-2026-10-22.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
 print(json.dumps({k:v for k,v in result.items() if k!='items'}),flush=True)
if __name__=='__main__':main()
