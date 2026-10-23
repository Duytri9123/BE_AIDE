import asyncio
import unittest
from unittest.mock import patch
from app.services.library_reference_prices import priced_references,reference_rows,enrich_browser_prices


class LibraryReferencePricesTests(unittest.TestCase):
    def row(self,**changes):
        return {'id':'price-25','sku':'NDK-25VA IEC','item_name':'NDK-25VA IEC','brand':'CHINT',
                'category':'TRANSFORMER','price':541200,'currency':'VND','checked_at':'2026-10-16',
                'source_url':'https://example.invalid/book.pdf','source_kind':'supplier_pricebook',
                'specifications':{'Công suất':'25VA'},**changes}

    def device(self,**changes):
        return {'id':'drawing','brand':'CHINT','type':'Transformer','product_code':None,
                'catalog_references':{'category':'TRANSFORMER','options':[{'brand':'CHINT','model':'NDK','basis':'catalog_type_reference'}]},**changes}

    def test_price_index_reuses_rows_and_invalidates_on_new_revision(self):
        from app.services.library_reference_prices import published_price_index
        first = [self.row()]
        revised = [self.row(price=600000)]
        with patch('app.services.ai.takeoff_pricebook.published_rows', return_value=first) as published:
            initial = published_price_index()
            self.assertIs(published_price_index(), initial)
            published.return_value = revised
            updated = published_price_index()
            self.assertIsNot(updated, initial)
            self.assertEqual(next(iter(updated.values()))[0]['price'], 600000)

    def test_family_prices_do_not_choose_one_voltage_or_capacity(self):
        rows=[self.row(),self.row(id='price-50',sku='NDK-50VA IEC',price=710600)]
        result=priced_references(self.device(),rows)['options'][0]
        self.assertIsNone(result['price'])
        self.assertEqual(len(result['price_choices']),2)
        self.assertEqual(self.device()['product_code'],None)

    def test_wrong_maker_type_and_number_prefix_are_excluded(self):
        device=self.device(catalog_references={'category':'TRANSFORMER','options':[{'brand':'CHINT','model':'NDK-25'}]})
        rows=[self.row(sku='NDK-250VA IEC'),self.row(brand='ABB'),self.row(category='MCB')]
        self.assertEqual(reference_rows(device,rows),[])

    def test_explicit_source_row_id_never_falls_back_to_other_variant(self):
        device=self.device(catalog_references={'category':'TRANSFORMER','options':[{'brand':'CHINT','model':'NDK','source_row_id':'missing'}]})
        self.assertEqual(reference_rows(device,[self.row()]),[])

    def test_front_view_label_is_not_a_product_code(self):
        device=self.device(catalog_references={'category':'TRANSFORMER','options':[{'brand':'CHINT','model':'Mặt trước'}]})
        self.assertEqual(reference_rows(device,[self.row()]),[])

    def test_browser_exposes_actual_order_models_without_overwriting_identity(self):
        device=self.device()
        with patch('app.services.ai.takeoff_pricebook.published_rows',return_value=[self.row()]):
            result=enrich_browser_prices({'items':[device]})['items'][0]
        self.assertEqual(result['reference_product_codes'],['NDK-25VA IEC'])
        self.assertEqual(result['catalog_references']['options'][0]['price'],541200)
        self.assertIsNone(result['product_code'])
        self.assertNotIn('price_choices',device['catalog_references']['options'][0])

    def test_zct_category_alias_resolves_ct_prices(self):
        device=self.device(catalog_references={'category':'ZCT','options':[{'brand':'Mikro','model':'ZCT40S'}]})
        self.assertEqual(len(reference_rows(device,[self.row(brand='Mikro',sku='ZCT40S',category='CT')])),1)

    def test_search_finds_order_code_belonging_to_documented_family(self):
        from app.services.catalogtb_browser import browser_page
        device=self.device(display='Biến áp CHINT NDK',product_code='NDK',search_aliases=[],category='Chint')
        with patch('app.services.catalogtb_browser.browser_data',return_value={'items':[device],'total':1}),\
             patch('app.services.ai.takeoff_pricebook.published_rows',return_value=[self.row()]):
            result=browser_page(q='NDK-25VA')
        self.assertEqual(result['total'],1)
        self.assertEqual(result['items'][0]['product_code'],'NDK')

    def test_api_returns_documented_reference_without_asserting_cad_link(self):
        from app.api.v1.endpoints.device_catalog import catalog
        rows=[self.row()]
        with patch('app.services.catalogtb_browser.browser_data',return_value={'items':[self.device()]}),\
             patch('app.services.ai.takeoff_pricebook.published_rows',return_value=rows),\
             patch('app.services.library_price_matching.device_configuration_links',return_value={}),\
             patch('app.services.library_price_matching.device_price_diagnostic',return_value={'status':'missing_transformer_configuration','message':'missing'}),\
             patch('app.api.v1.endpoints.device_catalog.load_supplier_items',return_value=rows),\
             patch('app.api.v1.endpoints.device_catalog.load_web_offers',return_value=[]),\
             patch('app.api.v1.endpoints.device_catalog.load_links',return_value={}),\
             patch('app.api.v1.endpoints.device_catalog.load_price_options',return_value={}):
            result=asyncio.run(catalog(equipment_catalog_id='drawing',skip=0,limit=100,current_user=None))
        self.assertEqual(result['total'],1)
        self.assertEqual(result['price_diagnostic']['status'],'catalog_reference_prices')
        self.assertFalse(result['items'][0].get('has_cad'))
        self.assertNotEqual(result['items'][0]['id'],'price-25')


if __name__=='__main__':unittest.main()
