import unittest
from unittest.mock import patch
from app.services.library_price_matching import configuration_links,device_price_diagnostic
from app.services.library_review_scope import exact_price_required
from app.services.catalogtb_browser import _build_browser_data


class SourceFaceTests(unittest.TestCase):
    def test_templates_never_receive_device_price(self):
        device={'id':'T','type':'MOUNTING_TEMPLATE','brand':'Schneider Electric',
                'brand_identification_status':'verified','product_code':'EZC100','spec':{'so_cuc':'3P'}}
        row={'id':'P','sku':'EZC100N3100','brand':'Schneider Electric','category':'MCCB','price':100}
        self.assertFalse(exact_price_required(device))
        self.assertEqual(configuration_links(device,[row]),{})
        with patch('app.services.catalogtb_browser.browser_data',return_value={'items':[device]}):
            self.assertEqual(device_price_diagnostic('T')['status'],'mounting_reference')

    def test_assembly_is_not_one_component_price(self):
        device={'id':'A','type':'ASSEMBLY_REFERENCE','brand_identification_status':'verified','product_code':'LV429640'}
        self.assertTrue(exact_price_required(device))
        self.assertEqual(configuration_links(device,[]),{})
        with patch('app.services.catalogtb_browser.browser_data',return_value={'items':[device]}):
            self.assertEqual(device_price_diagnostic('A')['status'],'assembly_requires_components')

    def test_visual_findings_preserve_unselected_configuration(self):
        devices={d['id']:d for d in _build_browser_data()['items']}
        front=devices['TB-0032dd9bb37e0165']
        self.assertEqual(front['product_code'],'LC1F185')
        self.assertEqual(front['spec']['so_cuc'],'3P')
        self.assertFalse(front['auto_select'])
        self.assertTrue(front['needs_review'])
        self.assertNotIn('dong_dinh_muc_da_chon',front['spec'])
        top=devices['TB-ec0313c7afab5af4']
        self.assertEqual(top['product_code'],'BKN')
        self.assertTrue(all(v['face']=='Mặt trên' for v in top['views']))
        self.assertEqual(devices['TB-117815138f330cbe']['type'],'ASSEMBLY_REFERENCE')


if __name__=='__main__':unittest.main()
