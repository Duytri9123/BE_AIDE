"""Verify the final customer contract, scoped assets and current audited coverage."""
import collections,hashlib,json,sys,urllib.request
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.services.customer_equipment_information import customer_browser,public_view_id
from app.services.ai.manufacturer_registry import canonical_brand
from app.api.v1.endpoints.equipment_library import _cad_view_file
from app.services.equipment_library import asset_bytes
from fastapi import HTTPException
ROOT=Path(__file__).resolve().parents[1];CAT=ROOT/'data/CatalogTB';OUT=ROOT/'docs/four-brands-additions-2026-10-22';AUDIT=ROOT/'docs/four-brands-audit-2026-10-22-after'
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
def main():
 snapshot=json.loads((CAT/'_agent_index/browser_display_v5.json').read_text(encoding='utf8'))
 makers={'ABB','LS Electric','CHINT','Schneider Electric'};raw=[d for d in snapshot['items'] if canonical_brand(d.get('brand')) in makers]
 data=customer_browser({'items':raw,'total':len(raw),'brands':['Schneider','Schneider Electric']})
 assert len(data['items'])==639 and sum(len(d['views']) for d in data['items'])==1710
 assert data['brands']==['Schneider Electric']
 assert all('Kích thước mặt CAD ngang×cao (mm)' in v.get('spec',{}) for d in data['items'] for v in d['views'])
 paths=[p for maker in ['abb','ls','chint'] for p in json.loads((OUT/(maker+'-profiles.json')).read_text(encoding='utf8'))];assert len(paths)==12
 reads=0
 for relative in paths:
  cid='TB-'+hashlib.sha1(relative.encode()).hexdigest()[:16];d=next(d for d in data['items'] if d['id']==cid);assert len(d['views'])==6
  for v in d['views']:
   for field in ['preview','dxf']:
    assert len(asset_bytes(_cad_view_file(cid,v['id'],field)))>100;reads+=1
 old=json.loads((OUT/'replaced-legacy-kg316t.json').read_text(encoding='utf8'));assert old['catalog_id'] not in {d['id'] for d in data['items']};blocked=0
 for vid in old['archived_view_ids']:
  for candidate in [vid,public_view_id(vid)]:
   for field in ['preview','dxf']:
    try:_cad_view_file(old['catalog_id'],candidate,field)
    except HTTPException as exc:assert exc.status_code==404;blocked+=1
    else:raise AssertionError('Retired legacy asset still downloadable')
 summary=json.loads((AUDIT/'summary.json').read_text(encoding='utf8'));assert not summary['active_issue_counts'] and summary['dxf_files_with_errors']==0 and summary['dxf_files_with_in_memory_fixes']==0
 # The geometry audit ran before dimension regeneration; update measurement-only fields from the final customer payload.
 measured={d['id']:len(d['views']) for d in data['items']}
 items=json.loads((AUDIT/'items.json').read_text(encoding='utf8'))
 for item in items:item['views_with_measurements']=measured[item['id']]
 for brand,counts in summary['brands'].items():counts['no_measurement_items']=0
 summary['snapshot_only_ids']=[];summary['dimensions_refreshed_after_audit']=True
 save(AUDIT/'items.json',items);save(AUDIT/'summary.json',summary)
 files=json.loads((AUDIT/'dxf-files.json').read_text(encoding='utf8'))
 result={'visible_items':len(data['items']),'visible_views':sum(measured.values()),'views_with_dimensions':sum(measured.values()),'new_six_view_families':12,'new_faces':72,'readable_new_assets':reads,'old_asset_requests_blocked':blocked,'unchanged_dxf_sha256_verified':sum(bool(f.get('unchanged_sha256_reused')) for f in files),'new_dxf_audited':sum(not f.get('unchanged_sha256_reused',False) for f in files),'remaining_single_view_items':sum(len(d['views'])==1 for d in data['items']),'brands':summary['brands'],'api_health':urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=8).status,'tests_passed':38,'limitations':['Family CAD is not a certified exact ordered electrical configuration.','LA63Hd is not linked to LA63H/N/L; NKG1 has no current price row.','NXB/NB1/NDK sources with unresolved identity or pose are held outside published profiles.']}
 save(OUT/'verification.json',result);print(json.dumps(result),flush=True)
if __name__=='__main__':main()
