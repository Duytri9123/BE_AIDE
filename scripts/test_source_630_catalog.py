import hashlib,json,unittest
from fastapi import HTTPException
from pathlib import Path
from app.services.catalogtb_browser import _build_browser_data
from app.services.equipment_library import get_equipment,asset_available
from app.api.v1.endpoints.equipment_library import _cad_view_file

ROOT=Path(__file__).resolve().parents[1];CAT=ROOT/'data/CatalogTB'

class Source630Catalog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=json.loads((ROOT/'docs/source-630-catalog-processing.json').read_text(encoding='utf8'))
        cls.browser=_build_browser_data()

    def test_all_630_sources_are_accounted_for_without_changing_originals(self):
        rows=self.report['items']
        self.assertEqual(len(rows),630)
        self.assertEqual(len({r['source'] for r in rows}),630)
        for row in rows:
            with self.subTest(source=row['source']):
                self.assertTrue(row['status'].startswith('processed_'))
                self.assertEqual(hashlib.sha256((CAT/row['source']).read_bytes()).hexdigest(),row['source_sha256'])

    def test_information_profiles_have_specs_codes_sources_and_blank_prices(self):
        for row in self.report['items']:
            if not row.get('profile'):continue
            data=json.loads((CAT/row['profile']).read_text(encoding='utf8'))
            with self.subTest(profile=row['profile']):
                self.assertTrue(data['thong_so'])
                self.assertTrue(data['catalog_tham_khao']['options'])
                self.assertEqual(data['gia_ban']['don_gia'],'---')
                self.assertFalse(data['auto_select'])
                self.assertFalse(data['nhan_dien_ai']['fabrication_ready'])

    def test_source_preview_is_served_by_equipment_index(self):
        row=next(r for r in self.report['items'] if r['status']=='processed_information_profile')
        cid='TB-'+hashlib.sha1(row['profile'].encode()).hexdigest()[:16]
        record=get_equipment(cid)
        self.assertIsNotNone(record)
        view=record['cad']['views'][0]
        self.assertTrue(asset_available(_cad_view_file(cid,view['id'],'preview')))
        self.assertTrue(asset_available(_cad_view_file(cid,view['id'],'dxf')))

    def test_no_visible_item_has_an_empty_information_table(self):
        self.assertGreater(self.browser['total'],1000)
        self.assertTrue(all(d.get('catalog_references',{}).get('options') for d in self.browser['items']))

    def test_spd_from_user_screenshot_has_3pn_and_manufacturer_options(self):
        item=next(d for d in self.browser['items'] if 'Chống sét lan truyền 3P+N' in d['display'])
        self.assertEqual(item['spec']['so_cuc'],'3P+N')
        options=item['catalog_references']['options']
        self.assertTrue(any(o['model']=='Acti9 iPRD40r / A9L40601' and o['price']=='---' for o in options))
        self.assertTrue(any(o['brand']=='Suntree' for o in options))

    def test_pending_manifest_count_is_zero_and_duplicates_remain_traceable(self):
        rows=json.loads((CAT/'ai_library_manifest.json').read_text(encoding='utf8'))['source_cad_documents']
        self.assertEqual(len(rows),630)
        self.assertTrue(all(r['status'].startswith('processed_') for r in rows))
        self.assertEqual(sum(r['status']=='processed_duplicate_geometry' for r in rows),160)
        self.assertTrue(all(r.get('information_profile') for r in rows if r['status']=='processed_duplicate_geometry'))

    def test_all_grouped_family_views_resolve_without_cross_family_fallback(self):
        groups=[d for d in self.browser['items'] if d.get('member_profile_ids')]
        self.assertTrue(groups)
        for group in groups:
            for view in group['views']:
                with self.subTest(group=group['id'],view=view['id']):
                    self.assertTrue(asset_available(_cad_view_file(group['id'],view['id'],'preview')))
                    self.assertTrue(asset_available(_cad_view_file(group['id'],view['id'],'dxf')))
        stranger=next(d for d in self.browser['items'] if d.get('source_catalog_review'))
        with self.assertRaises(HTTPException):
            _cad_view_file(groups[0]['id'],stranger['views'][0]['id'],'preview')

if __name__=='__main__':unittest.main()
