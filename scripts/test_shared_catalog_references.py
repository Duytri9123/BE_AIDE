import json
import unittest
from pathlib import Path
from unittest.mock import patch

from app.services.catalogtb_browser import browser_page, _build_browser_data
from app.services.device_catalog_engine import DeviceCatalogEngine
from app.services.cad.library_taxonomy import explicit_brands


class SharedCatalogReferences(unittest.TestCase):
    def test_shared_brand_filter_preserves_source_identity(self):
        row = dict(id='A', brand='Morele', display='Đèn báo', type='LIGHT',
                   catalog_references={'options':[{'brand':'Andex','model':'---'}]})
        with patch('app.services.catalogtb_browser.browser_data', return_value={'items':[row], 'total':1}):
            result = browser_page(brand='Andex')
        self.assertEqual(result['total'], 1)
        self.assertEqual(result['items'][0]['brand'], 'Morele')
        self.assertIn('Andex', result['brands'])

    def test_ai_search_accepts_shared_geometry_without_approving_a_model(self):
        engine = object.__new__(DeviceCatalogEngine)
        engine.reference_profiles = [dict(category='LIGHT', name='Đèn báo', brand='Morele', poles=None,
                                         reference_path='test', catalog_references={'options':[{'brand':'Andex'}]})]
        result = engine.search_references('LIGHT', brand='Andex')
        self.assertEqual(result[0]['brand_match'], 'shared_cad_reference')
        self.assertFalse(result[0]['auto_select'])
        self.assertFalse(result[0]['exact_model'])
        self.assertEqual(result[0]['brand'], 'Morele')

    def test_all_profiles_have_references_and_no_requested_price(self):
        root = Path(__file__).resolve().parents[1]/'data/CatalogTB'
        paths = list(root.rglob('thong_tin_thiet_bi.json'))
        self.assertGreater(len(paths), 800)
        for path in paths:
            with self.subTest(profile=path.relative_to(root)):
                d = json.loads(path.read_text(encoding='utf-8-sig'))
                self.assertEqual(d['gia_ban']['don_gia'], '---')
                self.assertTrue(d['catalog_tham_khao']['options'])
                self.assertTrue(all(o['price']=='---' and not o['exact_cad_match'] for o in d['catalog_tham_khao']['options']))

    def test_morele_lights_and_fuse_holders_are_available(self):
        root = Path(__file__).resolve().parents[1]/'data/CatalogTB/DenBaoNutNhanCauChiContactor/ThietBi'
        fuse = json.loads((root/'CauChi_1P/thong_tin_thiet_bi.json').read_text(encoding='utf8'))
        self.assertTrue(any(o['brand']=='Morele' and o['model']=='RT18-32' for o in fuse['catalog_tham_khao']['options']))
        rows = _build_browser_data()['items']
        self.assertTrue(any(any(o['brand']=='Morele' and o['model']=='AD16-22CS' for o in d['catalog_references']['options']) for d in rows))

    def test_brand_recognition_does_not_depend_on_priced_catalog(self):
        self.assertEqual(explicit_brands('Đèn báo Idec'), ['IDEC'])
        self.assertEqual(explicit_brands('Đèn báo vô danh'), [])


if __name__ == '__main__':
    unittest.main()
