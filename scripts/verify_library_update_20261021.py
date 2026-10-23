"""Exercise published file lookup and selected CAD envelopes for the new delta."""
import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ls_native_writer import ROOT,CAT
from app.api.v1.endpoints.equipment_library import _cad_view_file
from app.services.equipment_library import asset_bytes
from app.services.customer_equipment_information import public_view_id
from app.services.cad.catalogtb_assets import assets
from app.services.cad.device_envelope import selected_envelope

def main():
 files=[];boxes=[];all_assets=assets(refresh=True)
 for report in ['ls-update-faces-2026-10-21','chint-full-faces-2026-10-21']:
  rows=json.loads((ROOT/'docs'/(report+'.json')).read_text());folder='LS' if report.startswith('ls-') else 'Chint';count=0
  for family in sorted({r['family'] for r in rows}):
   p=CAT/folder/'ThietBi'/('OFFICIAL-'+family)/'thong_tin_thiet_bi.json';d=json.loads(p.read_text(encoding='utf8'));relative=p.relative_to(CAT).as_posix();cid='TB-'+hashlib.sha1(relative.encode()).hexdigest()[:16]
   for v in d['cad_don']:
    for field in ['dxf','preview']:
     path=_cad_view_file(cid,public_view_id(v['id_hinh_goc']),field);assert len(asset_bytes(path))>100;count+=1
   front=next(a for a in all_assets if a['profile_path']==relative and a['face']=='front')
   dimensions=selected_envelope({'cad':{'asset_id':front['id']}});assert all(x>0 for x in dimensions)
   boxes.append({'brand':d['hang_xac_nhan'],'family':family,'envelope_mm':dimensions})
  files.append({'report':report,'service_file_reads':count});print(json.dumps(files[-1]),flush=True)
 result={'files':files,'envelopes':boxes}
 (ROOT/'docs/ls-library-update-2026-10-21/service-and-envelope-validation.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(boxes))
if __name__=='__main__':main()
