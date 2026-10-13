from pathlib import Path
import sys,json,hashlib
from collections import Counter
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'BE_AIDE'));sys.stdout.reconfigure(encoding='utf8')
from app.services.device_catalog_engine import DeviceCatalogEngine
from app.services.catalogtb_browser import browser_data
from app.services.cad import catalogtb_assets as ca
engine=DeviceCatalogEngine.get_instance();ui={r['id']:r for r in browser_data()['items']};assets=ca.assets(refresh=True);m=json.loads((ca.ROOT/'ai_library_manifest.json').read_text(encoding='utf8'));fail=[];rows=[]
for item in m['items']:
 p=ca.ROOT/item['profile'];d=json.loads(p.read_text(encoding='utf8'));cid='TB-'+hashlib.sha1(item['profile'].encode()).hexdigest()[:16];display=ui.get(cid) or next((v for v in ui.values() if cid in v.get('member_profile_ids',[])),None)
 matches=engine.search_references(item['category_code'],query=item['name'],limit=835)
 if not any(r['reference_path']==item['profile'] for r in matches):fail.append([item['profile'],'agent_lookup_missing'])
 if display is None:fail.append([item['profile'],'frontend_missing'])
 if d.get('nhan_dien_bo_sung_20261010') and display and display['type']!=item['category_code']:fail.append([item['profile'],'frontend_stale_type'])
 rows.append(dict(profile=item['profile'],name=item['name'],category=item['category_code'],exact_sku_verified=item.get('exact_SKU_verified',False),auto_select=d.get('auto_select',False),needs_review=d.get('needs_review',True),unknown_faces=[v['source_id'] for v in item['views'] if v['face']=='unknown']))
report=dict(profile_count=len(rows),function_identified=sum(r['category']!='UNCLASSIFIED' for r in rows),unclassified=[r for r in rows if r['category']=='UNCLASSIFIED'],profiles_with_unknown_faces=sum(bool(r['unknown_faces']) for r in rows),unknown_views=sum(len(r['unknown_faces']) for r in rows),units_not_confirmed_mm=sum(v['units_code']!=4 for i in m['items'] for v in i['views']),failure_count=len(fail),failures=fail,profiles=rows,scope='Saved code: manifest, profile, agent full lookup, frontend metadata. Not all-image vision or exact SKU verification.')
(ROOT/'outputs/catalogtb-agent-audit/pipeline-recognition-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps({k:v for k,v in report.items() if k not in ('profiles','unclassified','failures')},ensure_ascii=False));print('Profiles',len(rows));assert not fail,fail[:5]
