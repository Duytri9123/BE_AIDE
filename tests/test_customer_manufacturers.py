import unittest
from app.services.customer_manufacturers import CUSTOMER_MANUFACTURERS
from app.services.ai.manufacturer_registry import canonical_brand
from app.services.device_catalog_browser import build_catalog_page,customer_catalog_page


class CustomerManufacturerTests(unittest.TestCase):
    def test_exact_requested_scope_without_discovery_reintroduction(self):
        documents = [{'brand':brand,'url':'https://internal.example/document'}
                     for brand in ('355 DECOR','HD Hyundai Electric','WAGO','BTB Electric')]
        result=customer_catalog_page(build_catalog_page([],[],documents=documents))
        self.assertEqual(len(result['brands']),32)
        self.assertEqual({maker['name'] for maker in result['brands']},set(CUSTOMER_MANUFACTURERS))
        for brand in ('Autonics','WAGO','TECO','Crouzet','355 DECOR','HD Hyundai Electric'):
            self.assertNotIn(brand,{maker['name'] for maker in result['brands']})

    def test_excluded_prices_cannot_reappear_in_all_brands_or_direct_query(self):
        prices=[{'key':'old','brand':'Autonics','category':'TIMER','price':100},
                {'key':'new','brand':'CHINT','category':'MCB','price':200}]
        result=build_catalog_page([],prices)
        self.assertEqual(result['priced_total'],1)
        self.assertEqual(result['items'][0]['brand'],'CHINT')
        self.assertEqual(build_catalog_page([],prices,brand='Autonics')['total'],0)

    def test_aliases_keep_one_manufacturer_identity(self):
        expected={'Mitsubishi':'Mitsubishi Electric','Idec Izumi':'IDEC','Epcos':'TDK / EPCOS',
                  'TDK':'TDK / EPCOS','Ducati':'Ducati Energia','Sino SP Vanlock':'Sino - Vanlock',
                  'Chint':'CHINT','Emic':'EMIC','Shihlin Electric':'Shihlin'}
        for raw,name in expected.items():
            self.assertEqual(canonical_brand(raw),name)

    def test_requested_brand_without_price_remains_unpriced(self):
        result=build_catalog_page([],[],brand='Delixi')
        self.assertEqual(result['items'],[])
        maker=next(m for m in result['brands'] if m['name']=='Delixi')
        self.assertEqual(maker['price_count'],0)
