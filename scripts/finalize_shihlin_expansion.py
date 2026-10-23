"""Publish/reindex the reviewed batch, then verify actual customer contracts."""
import subprocess,sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from publish_abb_ct_index import main as publish_index
batch=json.loads((ROOT/'docs/catalog-completion-2026-10-23/shihlin-expansion-import.json').read_text(encoding='utf8'))
publish_index([Path(i['profile']).parent.name for i in batch['items']],report_name='shihlin-full-faces-2026-10-23',brand='Shihlin',category='MCCB',profile_root='Shihlin/ThietBi',refresh=False)
from app.services.catalogtb_browser import _refresh_browser_data
_refresh_browser_data(ROOT/'data/CatalogTB')
for script,args in [('build_customer_technical_facts.py',['--reuse-cad']),('measure_customer_cad_views.py',[]),('build_customer_technical_facts.py',['--reuse-cad']),('verify_customer_cad_measurements.py',[]),('verify_shihlin_expansion.py',['--reuse-snapshot']),('verify_shihlin_bm250.py',['--reuse-snapshot']),('verify_mitsubishi_customer_batch.py',[]),('report_all_brand_price_cad_coverage.py',[]),('report_customer_face_gaps.py',[]),('refresh_catalogtb_recognition.py',['--index-only']),('audit_catalogtb_agent_inventory.py',[])]:
 print('Running',script,flush=True)
 subprocess.run([sys.executable,'-X','utf8',str(ROOT/'scripts'/script),*args],cwd=ROOT,check=True)
