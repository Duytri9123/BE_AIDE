"""Verify published native views and physical-variant price boundaries."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from app.services.catalogtb_browser import _refresh_browser_data
from app.services.customer_equipment_information import customer_device,customer_information_rows
from app.services.library_catalog_information import source_rows,information_rows
from app.services.catalog_family_matching import row_poles
from app.services.cad.ls_view_coverage import view_coverage
CAT=ROOT/'data/CatalogTB';REPORT=ROOT/'docs/catalog-completion-2026-10-23'

def main():
 if '--reuse-snapshot' not in sys.argv:_refresh_browser_data(CAT)
 snapshot=json.loads((CAT/'_agent_index/browser_display_v5.json').read_text(encoding='utf8'));devices={d['id']:d for d in snapshot['items']}
 batch=json.loads((REPORT/'shihlin-expansion-import.json').read_text(encoding='utf8'));rows=source_rows();result=[]
 correction=next(r for r in rows if r['id']=='full-pricebook:526f6e0388003fe93f9dd320')
 assert correction['sku']=='MT-400N' and correction['category']=='ACCESSORY' and correction['price']==14258000
 for entry in batch['items']:
  path=CAT/entry['profile'];raw=json.loads(path.read_text(encoding='utf8'))
  cid='TB-'+hashlib.sha1(entry['profile'].encode()).hexdigest()[:16];d=devices[cid];public=customer_device(d)
  assert len(public['views'])==6 and view_coverage(d['views'])['complete'],cid
  assert public['spec']['Kích thước CAD W×H×D (mm)']==entry['dimensions_mm']
  expected_380={'BM30-CN':'1.5','BM1000-HS':'100','BM630s-STA':'25','BM630s-LTA':'36','BM630s-HTA':'50','BM630s-RTA':'70'}[entry['model']]
  assert str(public['spec']['Icu tại 380 V AC (kA)'])==expected_380,(cid,public['spec'])
  actual=information_rows(d,rows);expected={hashlib.sha256(r.encode()).hexdigest()[:24] for r in entry['price_rows']}
  assert {r['id'] for r in actual}==expected,(cid,actual,expected)
  assert all(r['sku']==entry['model'] and row_poles(r)==entry['poles'] for r in actual)
  published=customer_information_rows(actual,d);assert len(published)==len(expected)
  for v in raw['cad_don']:
   f=path.parent/v['duong_dan'];assert hashlib.sha256(f.read_bytes()).hexdigest()==v['unit_verification']['sha256']
  result.append({**entry,'id':cid,'customer_price_rows':len(published),'views':6,'native_hashes_verified':True})
 assert len(result)==9 and sum(len(i['price_rows']) for i in result)==9
 previous=json.loads((REPORT/'browser-before-shihlin-refresh.json').read_text(encoding='utf8'))
 # Preserve every earlier profile; an exact source fix must not hide old CAD.
 if isinstance(previous,list):old={i['id'] if isinstance(i,dict) else i for i in previous}
 else:old=set(previous.get('ids') or [i['id'] for i in previous.get('items',[])])
 assert old<=set(devices),old-set(devices)
 output={'families':9,'views':54,'price_rows':9,'public_verified':True,'items':result,'all_previous_profiles_retained':True,'visible_profiles':len(devices)}
 (REPORT/'shihlin-expansion-verification.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf8')
 print(json.dumps({k:v for k,v in output.items() if k!='items'},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
