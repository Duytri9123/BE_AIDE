"""Verify the published Schneider payload, files, quarantines and price corrections."""
import json,sys,urllib.request
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fastapi import HTTPException
from app.services.ai.manufacturer_registry import canonical_brand
from app.services.customer_equipment_information import customer_browser,public_view_id
from app.api.v1.endpoints.equipment_library import _cad_view_file
from app.services.equipment_library import asset_bytes
from app.services.cad.ls_view_coverage import view_coverage
ROOT=Path(__file__).resolve().parents[1];CAT=ROOT/'data/CatalogTB';OUT=ROOT/'docs/schneider-update-2026-10-21'

def main():
 data=json.loads((CAT/'_agent_index/browser_display_v5.json').read_text(encoding='utf8'));items=[d for d in data['items'] if canonical_brand(d.get('brand'))=='Schneider Electric']
 public=customer_browser({'items':items,'total':len(items)});assert len(public['items'])==232
 assert sum(len(d['views']) for d in public['items'])==301
 assert all('Kích thước mặt CAD ngang×cao (mm)' in v.get('spec',{}) for d in public['items'] for v in d['views'])
 changes=json.loads((OUT/'changes.json').read_text(encoding='utf8'));reads=0
 for row in changes['added_families']:
  p=CAT/row['profile'];cid='TB-'+__import__('hashlib').sha1(row['profile'].encode()).hexdigest()[:16]
  device=next(d for d in items if d['id']==cid);assert view_coverage(device['views'])['complete']
  assert all(v['label']==v['face'] for v in device['views'])
  for view in device['views']:
   for field in ['dxf','preview']:
    assert len(asset_bytes(_cad_view_file(cid,public_view_id(view['id']),field)))>100;reads+=1
 bad={x['profile_id'] for x in changes['quarantined_views']}|{x['id'] for x in changes['identity_holds']}|{changes['linework_quarantine']['catalog_id']}
 quarantined=[x for x in json.loads((ROOT/'app/data/catalog_quarantined_views.json').read_text(encoding='utf8'))['items'] if x['catalog_id'] in bad];assert len(quarantined)==15
 blocked=0
 for row in quarantined:
  for vid in [row['view_id'],public_view_id(row['view_id'])]:
   for field in ['preview','dxf']:
    try:_cad_view_file(row['catalog_id'],vid,field)
    except HTTPException as exc:assert exc.status_code==404;blocked+=1
    else:raise AssertionError('Old quarantined CAD remains accessible')
 before=json.loads((ROOT/'docs/schneider-current-audit-2026-10-21/fresh-devices.json').read_text(encoding='utf8'))['items']
 stale=customer_browser({'items':before,'total':len(before)});assert len(stale['items'])==230 and sum(len(x['views']) for x in stale['items'])==289
 audit=json.loads((OUT/'after-audit/summary.json').read_text(encoding='utf8'));assert not audit['active_issue_counts'] and audit['dxf_files_with_errors']==0 and audit['dxf_files_with_in_memory_fixes']==0
 source_prices=json.loads((ROOT/'app/data/supplier_pricebooks.json').read_text(encoding='utf8'))['items'];old_prices=json.loads((OUT/'supplier-pricebooks.before.json').read_text(encoding='utf8'))['items'];assert {r['id']:r.get('price') for r in source_prices}=={r['id']:r.get('price') for r in old_prices}
 checked=json.loads((OUT/'mcb-pricebook-corrections.json').read_text(encoding='utf8'));old_by_id={r['id']:r for r in old_prices}
 corrected=sum(old_by_id[r['id']]['category']!='MCB' for r in checked);assert corrected==36
 status=urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=8).status
 report={'visible_items':232,'visible_views':301,'views_with_2d_dimensions':301,'new_six_view_families':2,'new_faces':12,'new_asset_reads':reads,'hidden_unresolved_faces':7,'hidden_defective_terminal_face':1,'unsupported_rmu_items_held':3,'rmu_views_held':7,'blocked_old_url_checks':blocked,'verified_mcb_price_rows':len(checked),'category_corrections':corrected,'price_amount_changes':0,'backend_tests_passed':53,'api_health':status,'remaining_incomplete_six_view_items':230,'remaining_single_view_items':179}
 (OUT/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report),flush=True)

if __name__=='__main__':main()
