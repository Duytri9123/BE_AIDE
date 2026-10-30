"""Refresh generated customer data, exact matching evidence and recognition indexes."""
import subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from app.services.catalogtb_browser import _refresh_browser_data
_refresh_browser_data(ROOT/'data/CatalogTB')
for name,args in [('build_customer_technical_facts.py',['--reuse-cad']),('measure_customer_cad_views.py',[]),('build_customer_technical_facts.py',['--reuse-cad']),('verify_customer_cad_measurements.py',[]),('verify_chint_nxc_expansion.py',['--reuse-snapshot']),('verify_chint_nxr_expansion.py',['--reuse-snapshot']),('verify_chint_nm8n125_expansion.py',['--reuse-snapshot']),('report_all_brand_price_cad_coverage.py',[]),('report_customer_face_gaps.py',[]),('refresh_catalogtb_recognition.py',['--index-only']),('audit_catalogtb_agent_inventory.py',[])]:
 print('Running',name,flush=True)
 subprocess.run([sys.executable,'-X','utf8',str(ROOT/'scripts'/name),*args],cwd=ROOT,check=True)
