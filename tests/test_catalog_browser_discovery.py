import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from app.services.catalogtb_browser import browser_data


class CatalogDiscoveryTest(TestCase):
    @patch('app.services.catalogtb_browser.read_snapshot', return_value=None)
    @patch('app.services.catalogtb_browser.write_snapshot', return_value=False)
    def test_new_profile_is_visible_without_rebuilding_html(self, write_snapshot, read_snapshot):
        with TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'index.html').write_text('<script id="catalog-data" type="application/json">{"profiles":[],"categories":[]}</script>',encoding='utf8')
            device=root/'NewDevice';device.mkdir()
            (device/'front.dxf').write_text('fixture',encoding='utf8')
            (device/'thong_tin_thiet_bi.json').write_text(json.dumps({
                'ten_san_pham':'New device','nhom':'New category',
                'cad_don':[{'id_hinh_goc':'front','duong_dan':'front.dxf','huong_nhin':'Mặt trước'}]
            }),encoding='utf8')
            with patch('app.services.catalogtb_browser.CATALOG_TB_ROOT',root):
                data=browser_data()
            self.assertEqual(data['total'],1)
            self.assertEqual(data['view_count'],1)
            self.assertEqual(data['items'][0]['brand'],'Asian')
            self.assertEqual(data['categories'][0]['name'],'New category')

    def test_approximate_identity_keeps_original_alias_and_unverified_status(self):
        from app.services.catalogtb_browser import _build_browser_data
        with TemporaryDirectory() as folder:
            root=Path(folder); device=root/'Drive';device.mkdir()
            (root/'index.html').write_text('<script id="catalog-data" type="application/json">{"profiles":[],"categories":[]}</script>',encoding='utf8')
            (device/'front.dxf').write_text('fixture',encoding='utf8')
            (device/'thong_tin_thiet_bi.json').write_text(json.dumps({
                'ten_san_pham':'Mitsubishi FR-S500','nhom':'Drive',
                'tu_khoa_tim_kiem':['INVERTER-0.75K'],
                'nhan_dien_web':{'brand_candidate':'Mitsubishi Electric','status':'visual_family_match','user_accepts_approximate_family':True},
                'cad_don':[{'id_hinh_goc':'front','duong_dan':'front.dxf','huong_nhin':'Mặt trước'}]
            }),encoding='utf8')
            with patch('app.services.catalogtb_browser.CATALOG_TB_ROOT',root):
                item=_build_browser_data()['items'][0]
            self.assertEqual(item['brand'],'Mitsubishi Electric')
            self.assertEqual(item['brand_identification_status'],'visual_family_match')
            self.assertIn('INVERTER-0.75K',item['search_aliases'])
            self.assertFalse(item['auto_select'])
