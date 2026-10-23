"""Check public six-view bodies, exact pole-specific price rows and native hashes."""
import hashlib,json,sys,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));CAT=ROOT/'data/CatalogTB'
from app.services.catalogtb_browser import _refresh_browser_data
from app.services.customer_equipment_information import customer_device,customer_information_rows
from app.services.catalog_publication_policy import public_device_allowed
from app.services.library_catalog_information import source_rows,information_rows
from app.services.catalog_family_matching import row_poles
from app.services.cad.ls_view_coverage import view_coverage

def main():
 if '--reuse-snapshot' not in sys.argv:_refresh_browser_data(CAT)
 snapshot=json.loads((CAT/'_agent_index/browser_display_v5.json').read_text(encoding='utf8'));devices={d['id']:d for d in snapshot['items']}
 rows=[r for r in source_rows() if r.get('brand')=='Shihlin'];report=[]
 for pole in [3,4]:
  path=CAT/f'Shihlin/ThietBi/OFFICIAL-BM250-SN-{pole}P/thong_tin_thiet_bi.json'
  raw=json.loads(path.read_text(encoding='utf8'));cid='TB-'+hashlib.sha1(path.relative_to(CAT).as_posix().encode()).hexdigest()[:16]
  d=devices[cid];public=customer_device(d)
  assert public_device_allowed(public) and len(public['views'])==6 and view_coverage(d['views'])['complete']
  assert public['spec']['Kích thước CAD W×H×D (mm)']==raw['thong_so']['Kích thước CAD W×H×D (mm)']
  matched=information_rows(d,rows);assert matched and all(row_poles(r)==str(pole)+'P' for r in matched),(pole,matched)
  assert all(re.fullmatch(r'BM250-SN(?:-'+str(pole)+r'P-\d+A)?',r['sku']) for r in matched),matched
  expected={o['model'] for o in raw['catalog_tham_khao']['options']};published=customer_information_rows(matched,d)
  assert expected<={r['sku'] for r in published}
  for view in raw['cad_don']:
   f=path.parent/view['duong_dan'];assert hashlib.sha256(f.read_bytes()).hexdigest()==view['unit_verification']['sha256']
  report.append({'id':cid,'poles':str(pole)+'P','views':6,'dimensions':public['spec']['Kích thước CAD W×H×D (mm)'],'customer_price_rows':len(published),'matched_poles':[row_poles(r) for r in matched]})
 result={'families':2,'views':12,'price_rows':2,'public_verified':True,'items':report,'unmatched_2p':'Held: no 2P native model in manufacturer archive; never substitute the 3P/4P body'}
 (ROOT/'docs/catalog-completion-2026-10-23/shihlin-bm250-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
 print(json.dumps(result,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
