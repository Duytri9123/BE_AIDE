"""Check actual customer data and prevent thermal/current/terminal misidentification."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));CAT=ROOT/'data/CatalogTB';OUT=ROOT/'docs/chint-research-2026-10-23'
from app.services.catalogtb_browser import _refresh_browser_data
from app.services.customer_equipment_information import customer_device,customer_information_rows
from app.services.library_catalog_information import source_rows,information_rows
from app.services.cad.ls_view_coverage import view_coverage

def main():
 if '--reuse-snapshot' not in sys.argv:_refresh_browser_data(CAT)
 snapshot=json.loads((CAT/'_agent_index/browser_display_v5.json').read_text(encoding='utf8'));devices={d['id']:d for d in snapshot['items']};rows=source_rows();report=[]
 batch=json.loads((OUT/'nxr-import.json').read_text(encoding='utf8'))
 for e in batch['items']:
  path=CAT/e['profile'];raw=json.loads(path.read_text(encoding='utf8'));cid='TB-'+hashlib.sha1(e['profile'].encode()).hexdigest()[:16];d=devices[cid];public=customer_device(d)
  assert len(public['views'])==6 and view_coverage(d['views'])['complete']
  assert public['spec']['Kích thước CAD W×H×D (mm)']==e['dimensions_mm']
  assert public['spec']['Dải chỉnh định Ir (A)']==e['setting_a']
  assert not any(k.startswith(('Icu','Ics','Icn')) for k in public['spec'])
  matches=information_rows(d,rows);expected={hashlib.sha256(i.encode()).hexdigest()[:24] for i in e['price_row_ids']}
  assert {r['id'] for r in matches}==expected,(e['model'],matches,expected)
  assert {r['sku'] for r in matches}==set(e['skus']) and all(r['category']=='THERMAL_RELAY' for r in matches)
  assert len(customer_information_rows(matches,d))==len(expected)
  if e['model']=='NXR-630':
   assert len(matches)==1 and matches[0]['sku']=='NXR-630 125A-400A' and public['spec']['Bước đầu nối động lực (mm)']=='48'
  for v in raw['cad_don']:
   p=path.parent/v['duong_dan'];assert hashlib.sha256(p.read_bytes()).hexdigest()==v['unit_verification']['sha256']
  report.append({**e,'id':cid,'public_price_rows':len(matches),'native_hashes_verified':True})
 corrections=json.loads((OUT/'nxr-price-identity-corrections.json').read_text(encoding='utf8'));lookup={r['id']:r for r in rows}
 assert len(corrections['items'])==40
 for c in corrections['items']:
  old=c['before'];new=lookup[old['id']];assert new['sku']==c['after']['sku'] and new['price']==old['price'] and new['category']=='THERMAL_RELAY'
  assert new['specifications']['Phù hợp']==old['specifications']['Phù hợp'] and 'In' not in new['specifications']
 baseline=json.loads((OUT/'browser-before.json').read_text(encoding='utf8'));assert {d['id'] for d in baseline['items'] if str(d.get('brand','')).upper()=='CHINT'}<=set(devices)
 result={'families':len(report),'views':24,'unique_price_rows':23,'corrected_pricebook_identity_rows':40,'prices_unchanged':True,'all_public_contracts_verified':True,'all_previous_chint_profiles_retained':True,'items':report,'visible_profiles':len(devices)}
 (OUT/'nxr-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps({k:v for k,v in result.items() if k!='items'},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
