"""Sequential publication, measurements and public contract verification."""
import subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from app.services.catalogtb_browser import _refresh_browser_data
_refresh_browser_data(ROOT/'data/CatalogTB')
for script,args in [('build_customer_technical_facts.py',['--reuse-cad']),('measure_customer_cad_views.py',[]),('build_customer_technical_facts.py',['--reuse-cad']),('verify_customer_cad_measurements.py',[]),('verify_mitsubishi_customer_batch.py',[]),('report_all_brand_price_cad_coverage.py',[])]:
 print('Running',script,flush=True)
 subprocess.run([sys.executable,'-X','utf8',str(ROOT/'scripts'/script),*args],cwd=ROOT,check=True)
