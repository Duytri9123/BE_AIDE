import unittest
from unittest.mock import patch
from app.services.catalogtb_browser import catalog_query_matches, browser_page
from scripts.complete_catalog_references import ndk_references


class CatalogQueryTests(unittest.TestCase):
    def test_source_identity_precedes_a_generic_reference(self):
        generic={'id':'generic','display':'Mẫu biến áp','catalog_references':{'options':ndk_references()}}
        source={'id':'source','display':'CHINT NDK-25','brand':'CHINT','product_code':'NDK-25'}
        with patch('app.services.catalogtb_browser.browser_data',return_value={'items':[generic,source],'total':2}), \
             patch('app.services.ai.takeoff_pricebook.published_rows',return_value=[]):
            result=browser_page(q='NDK25')
        self.assertEqual([x['id'] for x in result['items']],['source','generic'])

    def test_reordered_unaccented_and_punctuation_variants(self):
        self.assertTrue(catalog_query_matches('chint bien ap', 'Biến áp điều khiển CHINT'))
        self.assertTrue(catalog_query_matches('NDK25 CHINT', 'CHINT NDK-25'))
        self.assertFalse(catalog_query_matches('NDK-25', 'CHINT NDK-250'))
        self.assertTrue(catalog_query_matches('NSX100 Schneider', 'Schneider NSX100N'))
        self.assertFalse(catalog_query_matches('NSX100', 'Schneider NSX1000N'))

    def test_reference_model_is_searchable_without_pricebook_or_false_cad_identity(self):
        item = {'id':'drawing', 'display':'Biến áp CHINT', 'brand':'CHINT',
                'product_code':None, 'catalog_references':{'options':ndk_references()}}
        with patch('app.services.catalogtb_browser.browser_data', return_value={'items':[item], 'total':1}), \
             patch('app.services.ai.takeoff_pricebook.published_rows', return_value=[]):
            result = browser_page(q='NDK1000 chint')
        self.assertEqual(result['total'], 1)
        self.assertIsNone(result['items'][0]['product_code'])
        options = result['items'][0]['catalog_references']['options']
        self.assertEqual(len(options), 16)
        self.assertTrue(all(not o['exact_cad_match'] for o in options))


if __name__ == '__main__':
    unittest.main()
