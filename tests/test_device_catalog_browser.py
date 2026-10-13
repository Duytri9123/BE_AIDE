import unittest
from app.services.device_catalog_browser import build_catalog_page

class CatalogBrowserTests(unittest.TestCase):
    def test_item_name_is_model_key_and_different_ratings_are_preserved(self):
        rows=[{'id':'v1','sku':'LA63N 3P','item_name':'LA63N 3P','name':'LA63N 3P','brand':'LS Electric','category':'MCB','price':428000,'currency':'VND','checked_at':'2026-10-13','effective_date':'2026-10-01'},
              {'id':'v2','sku':'LA63N 3P','item_name':'LA63N 3P','name':'LA63N 3P','brand':'LS Electric','category':'MCB','price':440000,'currency':'VND','checked_at':'2026-10-13','effective_date':'2026-10-01'}]
        result=build_catalog_page([],[],supplier_items=rows)
        self.assertEqual(result['primary_key'],'item_name')
        self.assertEqual(result['total'],2)
        self.assertEqual(len({r['model_key'] for r in result['items']}),1)
        self.assertEqual({r['price'] for r in result['items']},{428000,440000})
    def test_web_seller_price_keeps_provenance_separate_from_catalog(self):
        row={'id':'offer','sku':'AT8N','name':'Timer AT8N','brand':'Autonics','category':'TIMER','price':390000,'currency':'VND','source_url':'https://seller.example/at8n','source_label':'Seller','checked_at':'2026-10-13','source_kind':'web_seller'}
        result=build_catalog_page([],[],web_offers=[row])
        self.assertEqual(result['items'][0]['source_url'],row['source_url'])
        self.assertEqual(result['items'][0]['source_kind'],'web_seller')
        self.assertEqual(result['items'][0]['model_key'],'Autonics::AT8N')
        self.assertEqual(build_catalog_page([],[],web_offers=[{**row,'currency':'USD'}])['items'],[])
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
