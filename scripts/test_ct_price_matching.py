import unittest
from app.services.ai.takeoff_pricebook import match_device

class CtPriceMatchingTests(unittest.TestCase):
 def row(self,**changes):
  return dict(id='ct',brand='ABB',category='CT',sku='CT-300',item_name='CT1M 300/5A',price=100,specifications={'Tỷ số':'300/5A'},**changes)
 def test_metering_ct_does_not_match_a_residual_transformer(self):
  row=self.row();row.update(sku='ZCT300',item_name='ZCT 300',specifications={})
  self.assertEqual(match_device({'category':'CT','spec':'300/5A'},[row])['status'],'not_found')
 def test_primary_and_secondary_ratio_both_have_to_match(self):
  for ratio in ('200/5A','300/1A'):
   self.assertEqual(match_device({'category':'CT','spec':ratio},[self.row()])['status'],'not_found')
  self.assertEqual(match_device({'category':'CT','spec':'300/5A','in_a':300},[self.row()])['candidate_count'],1)
 def test_body_code_without_ratio_is_not_automatically_priced(self):
  self.assertEqual(match_device({'category':'CT','brand':'ABB','part_number':'CT-300','spec':''},[self.row()])['status'],'needs_selection')

if __name__=='__main__':unittest.main()
