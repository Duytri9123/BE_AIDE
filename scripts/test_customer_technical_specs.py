import unittest,tempfile,json
from pathlib import Path
from unittest.mock import patch
from app.services.customer_equipment_information import product_specs,customer_device
from app.services import customer_technical_specs as technical
from scripts.build_customer_technical_facts import exact_options,reference_facts,nums

class TechnicalFactsTests(unittest.TestCase):
 def test_current_list_is_not_misread_as_decimal_current(self):
  self.assertEqual(nums('15,20,30,40,50,60,75,100A'),[15,20,30,40,50,60,75,100])
  self.assertEqual(nums('0,16–0,25 A'),[.16,.25]);self.assertEqual(nums('12,5 A'),[12.5])
 def test_ls_pricebook_capacity_is_not_mislabelled_as_415v(self):
  result=technical.qualified_breaking_specs('LS Electric','ABN103c')
  self.assertEqual(result['Icu tại 415/460 V AC (kA)'],'18');self.assertEqual(result['Icu tại 380 V AC (kA)'],'22');self.assertEqual(result['Icu tại 220/250 V AC (kA)'],'35')
  self.assertEqual(technical.qualified_breaking_specs('LS Electric','ABN100c'),{})
 def test_screenshot_notes_are_hidden_but_installation_facts_remain(self):
  result=product_specs({'Đối chiếu cấu hình':'Kiểm tra In, Icu/Ics theo mã đặt hàng','Bao hình':'Giữ tư thế tay gạt và toàn bộ hình học gốc STEP','so_cuc':'3P','Kiểu lắp':'Cố định; đấu nối phía trước','Kích thước thân W×H×D (mm)':'90 × 155 × 75.5'})
  self.assertEqual(set(result),{'so_cuc','Kiểu lắp','Kích thước thân W×H×D (mm)'})
 def test_list_hint_does_not_publish_selection_instructions(self):
  d=customer_device({'id':'test-not-live','brand':'CHINT','type':'MCCB','display':'MCCB CHINT','spec_hint':'Dải mã tham khảo · kiểm tra điện áp và cấu hình khi chọn','views':[]})
  self.assertNotIn('spec_hint',d)
 def test_old_model_or_view_set_cannot_inherit_facts(self):
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder)/'facts.json';p.write_text(json.dumps({'items':{'x':{'model':'OLD','view_ids':['front'],'facts':{'Icu tại 415 V':'36'}}}}))
   with patch.object(technical,'PATH',p):
    technical._load.cache_clear();d={'id':'x','brand':'ABB','product_code':'NEW','views':[{'id':'front'}]};self.assertEqual(technical.technical_specs(d,{}),{})
 def test_dimensions_follow_selected_cad_variant(self):
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder)/'facts.json';p.write_text(json.dumps({'items':{'x':{'model':'XT1','view_ids':['a','b'],'view_facts':{'a':{'Kích thước CAD W×H×D (mm)':'78 × 180 × 109'}}}}}))
   with patch.object(technical,'PATH',p):
    technical._load.cache_clear();d={'id':'x','product_code':'XT1','views':[{'id':'a'},{'id':'b'}]};self.assertTrue(technical.view_technical_specs(d,'a'));self.assertEqual(technical.view_technical_specs(d,'b'),{})
 def test_reference_dimensions_must_agree_for_all_matching_codes(self):
  options=[{'model':'m1','specifications':{'Kích thước (mm)':'90 × 155 × 77','In':'100A'}},{'model':'m2','specifications':{'Kích thước (mm)':'120 × 155 × 77','In':'160A'}}]
  facts,_=reference_facts({},options);self.assertNotIn('Kích thước (mm)',facts);self.assertEqual(facts['Dải dòng định mức In (A)'],'100–160')
 def test_other_poles_and_other_rating_suffix_are_not_promoted(self):
  d={'brand':'CHINT','type':'MCCB','product_code':'NXM-250S','spec':{'so_cuc':'3P'},'catalog_references':{'options':[{'brand':'CHINT','model':'NXM-250S/3300 250A','specifications':{'In':'250A'}},{'brand':'CHINT','model':'NXM-250H/3300 250A','specifications':{'In':'250A'}},{'brand':'CHINT','model':'NXM-250S/4300 250A','specifications':{'In':'250A'}}]}}
  self.assertEqual([o['model'] for o in exact_options(d)],['NXM-250S/3300 250A'])
if __name__=='__main__':unittest.main()
