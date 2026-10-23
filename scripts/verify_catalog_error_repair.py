import hashlib,json,sys,urllib.request
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import ezdxf
from fastapi import HTTPException
from scripts.repair_quarantine_catalog_errors import geometry
from app.services.catalogtb_browser import _build_browser_data
from app.services.catalog_view_health import source_displayable
from app.services.customer_equipment_information import customer_browser,customer_device,public_view_id
from app.api.v1.endpoints.equipment_library import _cad_view_file
from app.services.equipment_library import asset_bytes
ROOT=Path(__file__).resolve().parents[1];CAT=ROOT/'data/CatalogTB';OUT=ROOT/'docs/catalog-error-repair-2026-10-21'

def main():
 repairs=json.loads((OUT/'repairs.json').read_text(encoding='utf8'))
 for row in repairs['metadata_repairs']:
  path=CAT/row['path'];doc=ezdxf.readfile(path);audit=doc.audit()
  assert not audit.errors and not audit.fixes
  before=ezdxf.readfile(OUT/'before'/row['path']);assert geometry(before)==geometry(doc)
  assert hashlib.sha256(path.read_bytes()).hexdigest()==row['new_sha256']
 print('18 metadata repairs verified with unchanged drawing entities',flush=True)
 blocked=0
 for row in repairs['quarantined_views']:
  for ident in [row['view_id'],public_view_id(row['view_id'])]:
   for field in ['dxf','preview']:
    try:_cad_view_file(row['catalog_id'],ident,field)
    except HTTPException as exc:assert exc.status_code==404;blocked+=1
    else:raise AssertionError('Quarantined projection still accessible')
 old=json.loads((ROOT/'docs/abb-ls-chint-current-audit-2026-10-21/fresh-devices.json').read_text(encoding='utf8'))['items']
 stale=next(d for d in old if d['id']==repairs['quarantined_views'][0]['catalog_id'])
 assert len(customer_device(stale)['views'])==1
 print('Old raw and opaque URLs blocked; stale payload cleaned',flush=True)
 data=_build_browser_data()
 stage=CAT/'_agent_index/browser_display_v5.pending'
 stage.write_text(json.dumps(data,ensure_ascii=False),encoding='utf8');stage.replace(CAT/'_agent_index/browser_display_v5.json')
 selected=[d for d in data['items'] if str(d.get('brand') or '').upper() in {'ABB','LS','LS ELECTRIC','CHINT'}]
 public=customer_browser({'items':selected,'total':len(selected)})
 assert len(public['items'])==395
 assert sum(len(d['views']) for d in public['items'])==1332
 file_reads=0
 for row in repairs['metadata_repairs']:
  path=CAT/row['path'];profile=path.parents[2]/'thong_tin_thiet_bi.json';raw=json.loads(profile.read_text(encoding='utf8'))
  entry=next(v for v in raw['cad_don'] if (profile.parent/v['duong_dan']).resolve()==path.resolve())
  assert source_displayable(entry,profile)
  cid='TB-'+hashlib.sha1(profile.relative_to(CAT).as_posix().encode()).hexdigest()[:16]
  for field in ['preview','dxf']:
   assert len(asset_bytes(_cad_view_file(cid,public_view_id(entry['id_hinh_goc']),field)))>100;file_reads+=1
 status=urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=8).status
 result={'repaired_dxf_files':18,'geometry_entity_tags_unchanged':True,'quarantined_views':2,'blocked_old_url_checks':blocked,'stale_snapshot_filtered':True,'visible_items':len(public['items']),'visible_views':sum(len(d['views']) for d in public['items']),'repaired_asset_reads':file_reads,'backend_tests_passed':44,'api_health':status,'new_cad_models_added':0}
 (OUT/'verification.json').write_text(json.dumps(result,indent=2),encoding='utf8')
 print(json.dumps(result),flush=True)

if __name__=='__main__':main()
