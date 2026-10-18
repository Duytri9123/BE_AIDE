import unittest
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from app.services.catalog_verified_configuration import apply_verified_configuration

class ConfigurationTests(unittest.TestCase):
    def test_shared_legend_does_not_assert_unsupported_four_pole_model(self):
        device={'brand':'Mitsubishi Electric','product_code':'NF125-CV','display':'NF125-CV 4P',
                'spec':{'so_cuc':'4P','dong_dinh_muc':'50 A'},
                'source_identification':{'source_models_read':['NF125-CV','NF125-SV']}}
        self.assertTrue(apply_verified_configuration(device))
        self.assertIsNone(device['product_code'])
        self.assertEqual(device['display'],'MCCB Mitsubishi 125AF · 4P')
        self.assertEqual(device['spec'],{'so_cuc':'4P','co_khung':'125 AF'})
        self.assertFalse(device['auto_select'])

    def test_three_pole_and_single_label_are_not_relabelled(self):
        for pole,labels in [('3P',['NF125-CV','NF125-SV']),('4P',['NF125-CV'])]:
            device={'brand':'Mitsubishi Electric','product_code':'NF125-CV','spec':{'so_cuc':pole},
                    'source_identification':{'source_models_read':labels}}
            self.assertFalse(apply_verified_configuration(device))
            self.assertEqual(device['product_code'],'NF125-CV')

    def test_persisted_browser_snapshot_is_corrected_before_background_refresh(self):
        from app.services import catalogtb_browser as browser
        device={'id':'test','brand':'Mitsubishi Electric','category':'Mitsubishi','views':[],
            'product_code':'NF400-CW','spec':{'so_cuc':'4P'},
            'source_identification':{'source_models_read':['NF400-CW','NF400-SW']}}
        with TemporaryDirectory() as folder:
            snapshot=Path(folder)/'snapshot.json'
            snapshot.write_text(json.dumps({'items':[device],'categories':[]}),encoding='utf8')
            with patch.object(browser,'_cache',None),patch.object(browser,'_cache_root',None),\
                 patch.object(browser,'_snapshot_path',return_value=snapshot),patch.object(browser,'Thread'),\
                 patch.object(browser,'_build_browser_data',side_effect=AssertionError('Unexpected full scan')),\
                 patch('app.services.catalog_complementary_views.merge_complementary_views',side_effect=lambda rows:rows):
                result=browser.browser_data()['items'][0]
                self.assertEqual(result['display'],'MCCB Mitsubishi 400AF · 4P')
                self.assertIsNone(result['product_code'])

if __name__=='__main__':unittest.main()
