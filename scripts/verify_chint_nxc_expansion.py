"""Verify real public views, manufacturer identity, pole/coil and price boundaries."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));CAT=ROOT/'data/CatalogTB';OUT=ROOT/'docs/chint-research-2026-10-23'
from app.services.catalogtb_browser import _refresh_browser_data
from app.services.customer_equipment_information import customer_device,customer_information_rows
from app.services.library_catalog_information import information_rows,source_rows
from app.services.catalog_family_matching import row_poles
from app.services.cad.ls_view_coverage import view_coverage

def main():
 if '--reuse-snapshot' not in sys.argv:_refresh_browser_data(CAT)
 data=json.loads((CAT/'_agent_index/browser_display_v5.json').read_text(encoding='utf8'));devices={d['id']:d for d in data['items']};batch=json.loads((OUT/'nxc-import.json').read_text(encoding='utf8'));rows=source_rows();items=[]
 for entry in batch['items']:
  path=CAT/entry['profile'];raw=json.loads(path.read_text(encoding='utf8'));cid='TB-'+hashlib.sha1(entry['profile'].encode()).hexdigest()[:16]
  d=devices[cid];public=customer_device(d);assert public['brand']=='CHINT' and len(public['views'])==6 and view_coverage(d['views'])['complete']
  assert public['spec']['Kích thước CAD W×H×D (mm)']==entry['dimensions_mm']
  assert public['spec']['Điện áp cuộn hút']==entry['coil']
  assert not any(k.startswith(('Icu','Ics','Icn')) for k in public['spec']),'Contactor is not a circuit breaker'
  matched=information_rows(d,rows);expected={hashlib.sha256(r.encode()).hexdigest()[:24] for r in entry['price_row_ids']}
  assert {r['id'] for r in matched}==expected,(entry['group'],matched,expected)
  assert {r['sku'] for r in matched}==set(entry['skus']) and all(row_poles(r)=='3P' for r in matched)
  published=customer_information_rows(matched,d);assert len(published)==len(entry['price_row_ids'])
  for v in raw['cad_don']:
   f=path.parent/v['duong_dan'];assert hashlib.sha256(f.read_bytes()).hexdigest()==v['unit_verification']['sha256']
  if entry['group']=='40-65':assert entry['models']==['NXC-40']
  if entry['group']=='265-400':assert entry['models']==['NXC-400']
  assert raw['auto_select'] is False and raw['nhan_dien_ai']['exact_SKU_confirmed'] is False
  items.append({**entry,'id':cid,'public_price_rows':len(published),'native_hashes_verified':True})
 baseline=json.loads((OUT/'browser-before.json').read_text(encoding='utf8'));old={i['id'] for i in baseline['items'] if str(i.get('brand','')).upper()=='CHINT'};assert old<=set(devices),old-set(devices)
 result={'families':len(items),'views':sum(i['views'] for i in items),'unique_price_rows':len({r for i in items for r in i['price_row_ids']}),'all_public_contracts_verified':True,'all_previous_chint_profiles_retained':True,'visible_profiles':len(devices),'items':items}
 (OUT/'nxc-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps({k:v for k,v in result.items() if k!='items'},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
