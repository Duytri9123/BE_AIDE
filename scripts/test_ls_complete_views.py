import unittest,tempfile,json
from pathlib import Path
from unittest.mock import patch
from app.services.cad.ls_view_coverage import view_coverage,require_complete_ls_views
from app.services.cad.library_assets import requested_asset
from app.services.cad.automatic_selection import select_device_geometry
class LSViewsTests(unittest.TestCase):
 def test_six_views_are_required_and_generic_side_does_not_prove_both_sides(self):
  r=view_coverage([{'huong_nhin':x} for x in ['Mặt trước','Mặt bên','Mặt trên']]);self.assertFalse(r['complete']);self.assertIn('rear',r['missing_faces']);self.assertIn('left',r['missing_faces']);self.assertIn('right',r['missing_faces'])
 def test_six_explicit_source_views_complete(self):
  r=view_coverage([{'huong_nhin':x} for x in ['Mặt trước','Mặt sau','Mặt bên trái','Mặt bên phải','Mặt trên','Mặt dưới']]);self.assertTrue(r['complete'])
 def test_missing_file_cannot_count_as_a_view(self):
  r=view_coverage([{'huong_nhin':'Mặt trước','available':False}]);self.assertIn('front',r['missing_faces'])
 def test_customer_status_does_not_combine_different_variants(self):
  from app.services.customer_equipment_information import customer_device
  views=[{'id':str(i),'face':label,'label':label,'cad_variant_id':('fixed' if i<3 else 'withdraw')} for i,label in enumerate(['Mặt trước','Mặt sau','Mặt bên trái','Mặt bên phải','Mặt trên','Mặt dưới'])]
  with patch('app.services.customer_equipment_information.reference_options',return_value=([],[])):
   d=customer_device({'id':'ls','brand':'LS','display':'LS','views':views})
  self.assertTrue(all(not v['cad_coverage']['complete'] for v in d['views']))
 def test_two_insertable_side_views_have_one_explicit_depth_source(self):
  from app.services.cad.device_envelope import selected_envelope
  f={'id':'tb:f','family_id':'ls','variant_id':'a','face':'front'}
  sides=[{'family_id':'ls','variant_id':'a','face':'side','placement':{'cho_phep_chen':True,'envelope_depth_source':False}}, {'family_id':'ls','variant_id':'a','face':'side','placement':{'cho_phep_chen':True,'envelope_depth_source':True}}]
  with patch('app.services.cad.catalogtb_assets.resolve',return_value=f),patch('app.services.cad.catalogtb_assets.assets',return_value=[f,*sides]),patch('app.services.cad.device_envelope._bounds',side_effect=[(36,83),(72,83)]) as b:
   self.assertEqual(selected_envelope({'cad':{'asset_id':'tb:f'}}),(36,83,72))
   self.assertEqual(b.call_args_list[1].args[0],sides[1])
 def test_other_brand_is_unaffected(self):
  self.assertIsNone(require_complete_ls_views({'brand':'ABB'}))
 def test_ls_existing_dimensions_do_not_replace_missing_cad(self):
  from app.services.cad.physical_layout_engine import PhysicalLayoutEngine
  with self.assertRaisesRegex(ValueError,'LS.*bổ sung'):
   PhysicalLayoutEngine.get_component_dimensions({'brand':'LS','dimensions':{'w':20,'h':80,'d':70}})
 def test_ls_without_cad_never_falls_back_to_generic_drawing(self):
  with self.assertRaisesRegex(ValueError,'LS.*bổ sung'):requested_asset({'brand':'LS Electric','category':'MCB'})
 def test_ls_price_rows_must_match_auxiliary_contacts(self):
  from app.services.catalog_product_sections import aux_contacts_compatible
  d={'brand':'LS','type':'CONTACTOR','spec':{'Tiếp điểm phụ':'1a1b'}}
  self.assertFalse(aux_contacts_compatible(d,{'sku':'MC-32a','specifications':{'In (A)':'32A (2a2b)'}}))
  self.assertTrue(aux_contacts_compatible(d,{'sku':'MC-32a','specifications':{'In (A)':'32A (1a1b)'}}))
  self.assertTrue(aux_contacts_compatible({**d,'brand':'ABB'},{'specifications':{}}))
 def test_ls_dc_coil_cannot_select_ac_geometry(self):
  asset={'id':'tb:ls','brand':'LS','name':'MC-32a','search_aliases':[],'specifications':{'dong_dinh_muc':'32','Loại cuộn hút':'AC'},'electrical_variants':[]}
  with patch('app.services.cad.automatic_selection.candidates',return_value=[asset]):
   r=select_device_geometry({'brand':'LS','category':'CONTACTOR','in_a':32,'spec':'220VDC','selection_source':'default_brand'})
  self.assertTrue(r['cad']['supplement_required']);self.assertFalse(r['cad'].get('asset_id'));self.assertIn('AC/DC',r['cad']['automatic_selection']['rejected'][0]['reason'])
 def test_ls_missing_angles_cannot_be_selected_automatically(self):
  asset={'id':'tb:ls','brand':'LS','name':'LS','search_aliases':[],'specifications':{},'electrical_variants':[]}
  with patch('app.services.cad.automatic_selection.candidates',return_value=[asset]),patch('app.services.cad.ls_view_coverage.require_complete_ls_views',side_effect=ValueError('LS cần bổ sung CAD: Mặt sau')):
   r=select_device_geometry({'brand':'LS','category':'MCB','selection_source':'default_brand'})
  self.assertTrue(r['cad']['supplement_required']);self.assertTrue(r['cad']['requires_selection']);self.assertFalse(r['cad'].get('asset_id'));self.assertIn('Mặt sau',r['cad']['automatic_selection']['rejected'][0]['reason'])
if __name__=='__main__':unittest.main()
