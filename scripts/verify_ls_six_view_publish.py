"""Validate every reconciled LS face and every complete source view-set."""
import sys,json,hashlib,gc
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import ezdxf
from ezdxf import bbox
from ls_native_writer import CAT,ROOT,REPORT
from ls_projection_compaction import source_segment_count
from app.services.cad.ls_view_coverage import view_coverage
from app.services.cad.catalogtb_assets import resolve
from app.services.cad.device_envelope import selected_envelope
records=json.loads(REPORT.read_text());n=0
for r in records:
 p=CAT/r['path']/'ban_ve.dxf';d=ezdxf.readfile(p)
 assert d.units==4 and source_segment_count(d.modelspace())>5 and not d.audit().errors,p
 assert not any(e.dxftype() in ['DIMENSION','TEXT','MTEXT','LEADER','MLEADER'] for e in d.modelspace()),p
 assert hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256'],p
 b=bbox.extents(d.modelspace()).size
 assert abs(b.x-r['width_mm'])<.01 and abs(b.y-r['height_mm'])<.01,p
 assert (p.parent/'xem_truoc.svg').is_file(),p
 n+=1;del d;gc.collect()
sets=0
for p in (CAT/'LS/ThietBi').glob('OFFICIAL-STEP-*/thong_tin_thiet_bi.json'):
 d=json.loads(p.read_text(encoding='utf8'))
 if d.get('browser_hidden'):continue
 views=d.get('cad_don',[]);assert view_coverage(views)['complete'],p
 assert all(v['bo_tri_trong_tu']['cho_phep_chen'] for v in views),p
 assert sum(bool(v['bo_tri_trong_tu'].get('envelope_depth_source')) for v in views)==1,p
 sets+=1
result={'faces_validated':n,'complete_step_families':sets,'checks':['DXF mm','nonempty geometry','DXF audit','no annotation entities','SHA256','recorded bounds','SVG exists','six distinct views per variant','one preferred depth source']}
(ROOT/'docs/ls-library-rebuild-2026-10-20/six-view-validation.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result))
