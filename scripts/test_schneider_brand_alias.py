import unittest
from unittest.mock import patch
from app.services.catalogtb_browser import browser_page
from app.services.customer_equipment_information import customer_browser

class SchneiderBrandAliasTests(unittest.TestCase):
 def test_alias_filter_includes_both_snapshot_spellings(self):
  items=[{'id':str(i),'brand':brand,'category':'MCB','views':[]} for i,brand in enumerate(['Schneider','Schneider Electric','ABB'])]
  with patch('app.services.catalogtb_browser.browser_data',return_value={'items':items,'total':3}):
   for alias in ['Schneider','Schneider Electric']:
    data=browser_page(brand=alias)
    self.assertEqual(data['total'],2)
    self.assertEqual(data['brands'],['ABB','Schneider Electric'])
 def test_customer_payload_normalizes_cached_brand_list_and_items(self):
  with patch('app.services.customer_equipment_information.customer_device',side_effect=lambda d:d):
   data=customer_browser({'brands':['Schneider','Schneider Electric','ABB'],'items':[]})
   self.assertEqual(data['brands'],['ABB','Schneider Electric'])

if __name__=='__main__':unittest.main()
