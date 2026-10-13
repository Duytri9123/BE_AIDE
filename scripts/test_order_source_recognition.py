"""Regression checks with independent source evidence and deliberate mutations."""
from pathlib import Path
import sys,json,unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'BE_AIDE'),str(ROOT/'tmp/tudien_deps')]
from app.services.cad import catalogtb_assets as ca
from app.core.device_patterns import DevicePatterns
from app.services.ai.source_reconciliation import compare_item,quote_spec,release_review
from app.services.cad.source_drawing_audit import physical_occurrences
from app.services.cad.output_status import output_status

class EvidenceRegression(unittest.TestCase):
 def test_live_measurement_inventory(self):
  a=ca.assets(refresh=True)
  self.assertTrue(any(r['profile_path'].startswith('BienDong/') for r in a))
  meters=ca.candidates('METER',measurement_function='current')
  self.assertTrue(meters)
  self.assertTrue(all(r['measurement_function']=='current' and 'AmpeKeKim' in r['profile_path'] for r in meters))
  self.assertTrue(any(r['category']=='CONTACTOR' and 'MC_6a-18a_3P' in r['profile_path'] for r in a))
 def test_control_ct_tags_are_not_transformers(self):
  self.assertIsNone(DevicePatterns.CT_PATTERN.search('CT1: công tắc 2 vị trí; CT2: công tắc 2 vị trí'))
  self.assertIsNotNone(DevicePatterns.CT_PATTERN.search('CT 63/5'))
 def test_real_ct_top_view_can_be_inserted(self):
  from app.services.cad.library_assets import requested_asset,insert_library_asset
  import ezdxf
  asset=next(a for a in ca.assets() if a['category']=='CT' and a['face']=='top' and 'MORELE/MSQ-30/' in a['profile_path'])
  self.assertEqual(requested_asset({'cad':{'asset_id':asset['id']}}),(True,asset['id']))
  d=ezdxf.new('R2018');d.units=4
  w,h=insert_library_asset(d.modelspace(),asset['id'],100,200)
  self.assertGreater(w,0);self.assertGreater(h,0);self.assertEqual(len(d.modelspace()),1)
 def test_independent_source_quantities(self):
  r=json.loads((ROOT/'outputs/order-447-457-audit/reconciliation.json').read_text(encoding='utf8'))
  self.assertEqual(r['counts_pdf'],{'BV1':9,'BV2':8,'DB.HT':4,'PX1':16,'PX2':10})
  self.assertEqual(sum(r['counts_pdf'].values()),47)
  self.assertEqual(r['counts_pdf'],r['counts_quote'])
  self.assertEqual(r['counts_cad_bodies']['DB.HT'],0)
  self.assertFalse(r['release_ready'])
 def test_duplicate_projections_and_side_mounted_supply(self):
  rows=[{'effective_name':'PS','owner_face':'mounting_plate','properties':{'Options':'Side'}},
        {'effective_name':'PS','owner_face':'side_projection','properties':{'Options':'Side'}}]
  self.assertEqual(len(physical_occurrences(rows,{'PS':'POWER_SUPPLY'})),1)
 def test_native_visible_width_not_insertion_point(self):
  rows=json.loads((ROOT/'outputs/order-447-457-audit/cad-face-occurrences.json').read_text(encoding='utf8'))
  mcbs=[r for r in rows if r['effective_name']=='BKN-LS' and r['owner_face']=='mounting_plate']
  self.assertEqual(len(mcbs),43)
  for r in mcbs:
   p=int(r['properties']['Visibility1'][0]);b=r['visible_bounds_mm']
   self.assertAlmostEqual(b[2]-b[0],18*p,places=2)
  self.assertTrue(any(abs(r['xy'][1]-r['visible_bounds_mm'][1])>1000 for r in mcbs))
 def test_wrong_ka_or_omitted_spare_blocks_release(self):
  for field,before,after in [('quantity',8,6),('breaking_capacity_ka',4.5,6),('poles',2,1),('category','RCBO','MCB')]:
   r=compare_item('changed',{'pdf':{field:before,'evidence':'PDF'},'cad':{field:after,'evidence':'CAD'}},fields=(field,))
   self.assertEqual(r['status'],'different');self.assertFalse(release_review([r])['release_ready'])
 def test_missing_model_is_not_a_match(self):
  r=compare_item('unknown',{'pdf':{'model':None,'evidence':'PDF'},'cad':{'model':None,'evidence':'CAD'}},fields=('model',))
  self.assertFalse(r['release_ready'])
 def test_pole_designation_and_explicit_revision(self):
  r=quote_spec('RCBO 2P 16A 4.5kA 30mA => 6kA')
  self.assertEqual((r['current_a'],r['breaking_capacity_ka'],r['residual_current_ma']),(16,6,30))
  self.assertEqual(quote_spec('LB63N 1P+N')['pole_designation'],'1P+N')
 def test_file_created_does_not_mean_design_complete(self):
  self.assertFalse(output_status('CAD','quote',{'placements':[{'tag':'Q0'}]},devices=[{'tag':'Q0'}])['success'])
  self.assertFalse(output_status('CAD','quote',{'placements':[{'tag':'Q0'}],'source_reconciliation':{'release_ready':False,'unresolved_items':['Q0']}},devices=[{'tag':'Q0'}])['success'])
 def test_wrong_owner_face_is_detectable(self):
  r=compare_item('selector',{'source':{'mounting_face':'inner_door','evidence':'DWG'},'generated':{'mounting_face':'outer_door','evidence':'DXF'}},fields=('mounting_face',))
  self.assertFalse(r['release_ready']);self.assertEqual(r['status'],'different')

if __name__=='__main__':unittest.main(verbosity=2)
