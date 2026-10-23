"""Validate the new delta, publish it, then verify the refreshed customer library."""
import json,hashlib,sys,collections
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import ezdxf
from ezdxf import bbox
from ls_native_writer import ROOT,CAT
from ls_projection_compaction import source_segment_count
from publish_abb_ct_index import main as publish
from app.services.cad.ls_view_coverage import view_coverage
OUT=ROOT/'docs/ls-chint-face-review-2026-10-21'

def main():
 result=[]
 for brand,folder in [('LS','LS'),('CHINT','Chint')]:
  report='ls-chint-review-additions-'+brand;records=json.loads((ROOT/'docs'/(report+'.json')).read_text());families=sorted({r['family'] for r in records})
  for r in records:
   p=CAT/r['path']/'ban_ve.dxf';d=ezdxf.readfile(p);size=bbox.extents(d.modelspace()).size
   assert d.units==4 and not d.audit().errors and source_segment_count(d.modelspace())>5
   assert not any(e.dxftype() in {'TEXT','MTEXT','DIMENSION','LEADER','MLEADER'} for e in d.modelspace())
   assert hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256']
   assert abs(size.x-r['width_mm'])<.01 and abs(size.y-r['height_mm'])<.01
   assert (p.parent/'xem_truoc.svg').is_file()
  for family in families:
   p=CAT/folder/'ThietBi'/('OFFICIAL-'+family)/'thong_tin_thiet_bi.json';d=json.loads(p.read_text(encoding='utf8'))
   assert len(d['cad_don'])==6 and view_coverage(d['cad_don'])['complete']
   if brand=='LS':assert not d['catalog_tham_khao']['options'] and d['cau_truc_cum']['physical_units_per_cad']==2
  result.append({'brand':brand,'families':len(families),'new_faces_validated':len(records)})
  print(json.dumps(result[-1]),flush=True)
  if '--verify-only' not in sys.argv:publish(['OFFICIAL-'+f for f in families],report_name=report,brand=brand,category='MIXED',profile_root=folder+'/ThietBi',refresh=brand=='CHINT')
 data=json.loads((CAT/'_agent_index/browser_display_v5.json').read_text(encoding='utf8'));unknown=[]
 from app.services.cad.catalogtb_assets import face_code
 counts=collections.Counter()
 for item in data['items']:
  brand=str(item.get('brand') or '').upper()
  if brand not in {'LS','LS ELECTRIC','CHINT'}:continue
  counts[brand+'_profiles']+=1
  for view in item.get('views',[]):
   counts[brand+'_views']+=1
   if face_code(view.get('face'))=='unknown' or any(x in str(view.get('label') or '').lower() for x in ['chưa xác','chua xac']):unknown.append({'id':item['id'],'view':view})
 assert not unknown,unknown
 panel='DenBaoNutNhanCauChiContactor/ThietBi/SOURCE_d99fbb3779c7d135/thong_tin_thiet_bi.json';panel_id='TB-'+hashlib.sha1(panel.encode()).hexdigest()[:16]
 item=next(x for x in data['items'] if x['id']==panel_id);assert item['type']=='ASSEMBLY_REFERENCE',item['type']
 # Exercise all public view file lookups for the 18 additions and 6 repaired views.
 from app.api.v1.endpoints.equipment_library import _cad_view_file
 from app.services.equipment_library import asset_bytes
 from app.services.customer_equipment_information import public_view_id
 reads=0
 repaired=json.loads((OUT/'resolved-views.json').read_text(encoding='utf8'));ids={r['id'] for r in repaired}
 for item in data['items']:
  for view in item.get('views',[]):
   if view['id'] not in ids and not any(view['id']==(brand+'-OFFICIAL-'+r['family']+'-'+r['view']) for brand in ['LS','CHINT'] for r in json.loads((ROOT/('docs/ls-chint-review-additions-'+brand+'.json')).read_text())):continue
   for field in ['dxf','preview']:
    path=_cad_view_file(item['id'],public_view_id(view['id']),field);assert len(asset_bytes(path))>100;reads+=1
 removed=json.loads((OUT/'removed-views.json').read_text(encoding='utf8'))
 summary={'new_additions':result,'reidentified_views':len(repaired),'deleted_unidentifiable_views':len(removed),'browser_unknown_orientations':len(unknown),'browser_counts':dict(counts),'service_file_reads':reads}
 (OUT/'publish-validation.json').write_text(json.dumps(summary,indent=2),encoding='utf8');print(json.dumps(summary),flush=True)
if __name__=='__main__':main()
