"""Pricebook membership is independent of CAD links and price availability."""
import unittest
from app.services.device_catalog_browser import build_catalog_page, customer_catalog_page

class UnpricedCatalogTests(unittest.TestCase):
    def rows(self):
        return [dict(id='priced',brand='ABB',sku='A1',name='A1',category='MCCB',price=100,vat_status='excluded'),
                dict(id='unpriced',brand='ABB',sku='A2',name='A2',category='ACCESSORY',price=None)]

    def test_all_products_without_cad_are_retained(self):
        result=build_catalog_page([],[],catalog_items=self.rows())
        self.assertEqual(result['total'],2)
        maker=next(m for m in result['brands'] if m['name']=='ABB')
        self.assertEqual(maker['product_count'],2)
        self.assertEqual(maker['price_count'],1)
        self.assertIn('ACCESSORY',[c['code'] for c in maker['catalog_categories']])
        self.assertEqual(len(maker['priced_categories']),1)

    def test_pagination_and_customer_fields_keep_missing_price(self):
        result=customer_catalog_page(build_catalog_page([],[],catalog_items=self.rows(),skip=1,limit=1))
        self.assertEqual(result['total'],2)
        row=result['items'][0]
        self.assertEqual(row['sku'],'A2')
        self.assertIsNone(row['price'])
        self.assertIn('Giá bán',row['columns'])
        for key in ('source_url','source_page','source_sha256','source_row'):
            self.assertNotIn(key,row)

    def test_unpriced_category_can_be_searched(self):
        result=build_catalog_page([],[],catalog_items=self.rows(),brand='ABB',category='ACCESSORY',q='A2')
        self.assertEqual([r['sku'] for r in result['items']],['A2'])

if __name__=='__main__':unittest.main()
