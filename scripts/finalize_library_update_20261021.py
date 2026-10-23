"""Validate and index this day's reviewed LS/CHINT delta, preserving historical audits."""
import json,hashlib,sys,csv
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import ezdxf
from ezdxf import bbox
from ls_native_writer import CAT,ROOT,REPORT
from ls_projection_compaction import source_segment_count
from app.services.cad.ls_view_coverage import view_coverage
from import_ls_rotary_handle_faces import JOBS
from publish_abb_ct_index import main as publish

def main():
 families={'STEP-'+j[0].replace('/','-') for j in JOBS}
 ls=[r for r in json.loads(REPORT.read_text()) if r['family'] in families]
 (ROOT/'docs/ls-update-faces-2026-10-21.json').write_text(json.dumps(ls,indent=2),encoding='utf8')
 chint=json.loads((ROOT/'docs/chint-full-faces-2026-10-21.json').read_text())
 results=[]
 for brand,records,report_name in [('LS',ls,'ls-update-faces-2026-10-21'),('CHINT',chint,'chint-full-faces-2026-10-21')]:
  folder='LS' if brand=='LS' else 'Chint'
  for r in records:
   p=CAT/r['path']/'ban_ve.dxf';d=ezdxf.readfile(p);size=bbox.extents(d.modelspace()).size
   assert d.units==4 and source_segment_count(d.modelspace())>5 and not d.audit().errors,p
   assert not any(e.dxftype() in ['DIMENSION','TEXT','MTEXT','LEADER','MLEADER'] for e in d.modelspace()),p
   assert hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256'],p
   assert abs(size.x-r['width_mm'])<.01 and abs(size.y-r['height_mm'])<.01,p
   assert (p.parent/'xem_truoc.svg').is_file(),p
  fs=sorted({r['family'] for r in records});price_ids=set()
  for f in fs:
   p=CAT/folder/'ThietBi'/('OFFICIAL-'+f)/'thong_tin_thiet_bi.json';d=json.loads(p.read_text(encoding='utf8'));vs=d['cad_don']
   assert len(vs)==6 and view_coverage(vs)['complete'],p
   assert all(v['bo_tri_trong_tu']['cho_phep_chen'] for v in vs)
   assert sum(bool(v['bo_tri_trong_tu'].get('envelope_depth_source')) for v in vs)==1
   opts=d['catalog_tham_khao']['options'];assert all(o['brand']==brand and o['exact_cad_match'] is False for o in opts)
   price_ids.update(o['source_row_id'] for o in opts)
  result={'brand':brand,'families':len(fs),'faces_validated':len(records),'linked_price_rows':len(price_ids),'checks':['mm','DXF audit','geometry segments','SHA256','bounds','SVG','six distinct views','preferred depth side','brand and price link isolation']};results.append(result);print(json.dumps(result),flush=True)
  publish(['OFFICIAL-'+f for f in fs],report_name=report_name,brand=brand,category='MIXED',profile_root=folder+'/ThietBi',refresh=brand=='CHINT')
 out=ROOT/'docs/ls-library-update-2026-10-21';out.mkdir(exist_ok=True)
 (out/'delta-validation.json').write_text(json.dumps(results,indent=2),encoding='utf8')
 import audit_ls_pricebook_cad_coverage as audit
 audit.OUT=out;audit.main()

if __name__=='__main__':main()
