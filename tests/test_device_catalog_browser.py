import unittest
from app.services.device_catalog_browser import build_catalog_page

class CatalogBrowserTests(unittest.TestCase):
    def test_filters_dates_and_private_fields(self):
        prices=[{'key':'a','name':'MCB','brand':'LS','category':'MCB','price':150000,'updated_at':'2026-10-13','updated_by':'private@example.test'},
                {'key':'b','name':'Timer','brand':'CHINT','category':'TIMER','price':250000,'updated_at':'2026-10-12'}]
        result=build_catalog_page([],prices,brand='LS',category='MCB',q='a')
        self.assertEqual(result['total'],1)
        self.assertEqual(result['items'][0]['price'],150000)
        self.assertEqual(result['items'][0]['updated_at'],'2026-10-13')
        self.assertNotIn('updated_by',result['items'][0])
        self.assertNotIn('private@example.test',str(result))
    def test_no_fabricated_prices_and_pagination(self):
        prices=[{'key':str(i),'brand':'LS','category':'MCB','price':i} for i in range(4)]
        result=build_catalog_page([],prices,skip=1,limit=1)
        self.assertEqual(result['total'],3)
        self.assertEqual(len(result['items']),1)
        self.assertTrue(any(b['categories'] for b in result['brands']))
        self.assertEqual(build_catalog_page([],[])['items'],[])
