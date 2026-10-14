import unittest
from unittest.mock import patch
from app.services.library_review_scope import exact_price_required
from app.services.library_price_matching import device_price_diagnostic


class ReviewScopeTests(unittest.TestCase):
    def test_electrical_equipment_stays_required(self):
        for kind in ('MCB','MCCB','CONTACTOR','RELAY','ATS','POWER_SUPPLY','CAPACITOR','METER','INVERTER'):
            self.assertTrue(exact_price_required({'type':kind,'brand_identification_status':'unknown'}))

    def test_terminal_and_accessories_are_optional_without_invented_prices(self):
        from app.services.ai.takeoff_pricebook import match_device
        for device in ({'type':'TERMINAL_BLOCK'},{'category':'Cầu đấu'},{'type':'INTERLOCK'},
                       {'brand_identification_status':'not_applicable'}):
            self.assertFalse(exact_price_required(device))
        with patch('app.services.catalogtb_browser.browser_data',return_value={'items':[{'id':'T1','type':'TERMINAL_BLOCK'}]}):
            result=device_price_diagnostic('T1')
        self.assertEqual(result['status'],'optional_price')
        self.assertNotIn('price',result)
        match=match_device({'category':'TERMINAL_BLOCK','part_number':'UNKNOWN'},[])
        self.assertFalse(match['exact_price_required'])
        self.assertIsNone(match['row'])
        self.assertIn('không bắt buộc',match['note'])

    def test_full_model_wrong_poles_is_diagnosed(self):
        device={'id':'D1','brand':'Mitsubishi Electric','brand_identification_status':'verified',
                'product_code':'NF125-CV','type':'MCCB','spec':{'so_cuc':'4P'}}
        row={'id':'R1','sku':'ORDER1','item_name':'NF125-CV 3P 100A','brand':'Mitsubishi Electric',
             'category':'MCCB','price':100,'specifications':{'Số cực':'3P','In (A)':'100'}}
        with (patch('app.services.catalogtb_browser.browser_data',return_value={'items':[device]}),
             patch('app.services.ai.takeoff_pricebook.published_rows',return_value=[row]),
             patch('app.services.library_price_matching.device_configuration_links',return_value={})):
            result=device_price_diagnostic('D1')
        self.assertEqual(result['status'],'different_poles')
        self.assertIn('3P',result['message'])
        self.assertIn('4P',result['message'])


if __name__=='__main__':unittest.main()
