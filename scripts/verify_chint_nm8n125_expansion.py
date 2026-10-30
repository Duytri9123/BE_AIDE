"""Check published NM8N dimensions, exact price scope and engraved-current limits."""
import hashlib,json,sys,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));CAT=ROOT/'data/CatalogTB';OUT=ROOT/'docs/chint-research-2026-10-23'
from app.services.catalogtb_browser import _refresh_browser_data
from app.services.customer_equipment_information import customer_device,customer_information_rows
from app.services.library_catalog_information import information_rows,source_rows
from app.services.cad.ls_view_coverage import view_coverage
from app.services.catalog_family_matching import row_poles

def main():
 if '--reuse-snapshot' not in sys.argv:_refresh_browser_data(CAT)
 snapshot=json.loads((CAT/'_agent_index/browser_display_v5.json').read_text(encoding='utf8'));devices={d['id']:d for d in snapshot['items']};rows=source_rows();items=[]
 batch=json.loads((OUT/'nm8n125-import.json').read_text(encoding='utf8'))
 for e in batch['items']:
  p=CAT/e['profile'];raw=json.loads(p.read_text(encoding='utf8'));cid='TB-'+hashlib.sha1(e['profile'].encode()).hexdigest()[:16];device=devices[cid];public=customer_device(device)
  assert public['brand']=='CHINT' and len(public['views'])==6 and view_coverage(device['views'])['complete']
  # Public measured dimensions use two decimals; import evidence keeps three.
  numbers=lambda value:[float(n) for n in re.findall(r'\d+(?:\.\d+)?',str(value))]
  actual=numbers(public['spec']['Kích thước CAD W×H×D (mm)']);expected_dimensions=numbers(e['dimensions_mm'])
  assert len(actual)==len(expected_dimensions)==3 and all(abs(a-b)<=.006 for a,b in zip(actual,expected_dimensions)),(actual,expected_dimensions)
  assert 'Icu / Ics tại '+e['voltage'] in public['spec']
  assert raw['thong_so']['Điện áp công bố Icu/Ics']==e['voltage']
  assert public['spec']['Kiểu lắp']=='Cố định trên tấm lắp; đấu nối phía trước'
  matched=information_rows(device,rows);expected={hashlib.sha256(r.encode()).hexdigest()[:24] for r in e['price_row_ids']}
  assert {r['id'] for r in matched}==expected,(e['poles'],len(matched),len(expected))
  assert {r['sku'] for r in matched}==set(e['skus']) and all(row_poles(r)==e['poles'] and r['category']=='MCCB' for r in matched)
  assert all(r['specifications']['Điện áp công bố Icu/Ics']==e['voltage'] for r in matched)
  published=customer_information_rows(matched,device);assert len(published)==len(expected)
  for r in published:
   column=r['columns'].index('Điện áp công bố Icu/Ics');assert r['cells'][column]==e['voltage']
  if e['poles']=='1P':assert len(matched)==1 and matched[0]['sku']=='NM8N-125C TM 125 1P'
  else:assert len(matched)==30 and {r['specifications']['Icu'] for r in matched}=={'36kA','50kA','100kA'}
  assert raw['auto_select'] is False and raw['catalog_tham_khao']['source_row_scope']=='explicit_only'
  for v in raw['cad_don']:
   f=p.parent/v['duong_dan'];assert hashlib.sha256(f.read_bytes()).hexdigest()==v['unit_verification']['sha256']
  items.append({**e,'id':cid,'public_price_rows':len(matched),'native_hashes_verified':True})
 baseline=json.loads((OUT/'browser-before.json').read_text(encoding='utf8'));assert {d['id'] for d in baseline['items'] if str(d.get('brand','')).upper()=='CHINT'}<=set(devices)
 report={'families':len(items),'views':sum(e['views'] for e in items),'unique_price_rows':sum(len(e['price_row_ids']) for e in items),'all_public_contracts_verified':True,'all_previous_chint_profiles_retained':True,'visible_profiles':len(devices),'items':items}
 (OUT/'nm8n125-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({k:v for k,v in report.items() if k!='items'},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
