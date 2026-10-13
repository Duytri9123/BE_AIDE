import unittest
from app.services.device_catalog_browser import build_catalog_page

class EquipmentPriceRelationshipTests(unittest.TestCase):
    def test_exact_device_can_have_multiple_price_rows(self):
        rows=[dict(id=str(i),currency='VND',item_name='A1',checked_at='2026-10-13',brand='ABB',category='MCCB',price=100,sku=str(i)) for i in range(3)]
        params=dict(supplier_items=rows,library_links={'0':'TB-one','1':'TB-one','2':'TB-two'},equipment_catalog_id='TB-one')
        page=build_catalog_page([],[],limit=1,**params)
        self.assertEqual(page['total'],2)
        self.assertEqual(page['items'][0]['id'],'0')
        self.assertEqual(build_catalog_page([],[],skip=1,limit=1,**params)['items'][0]['id'],'1')
        self.assertEqual(build_catalog_page([],[],supplier_items=rows,equipment_catalog_id='TB-unlinked')['total'],0)

if __name__=='__main__':
    unittest.main()
