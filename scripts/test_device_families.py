import asyncio
import unittest
from app.services.cad.device_families import build_families, identity
from app.api.v1.endpoints.cad_library import manifest
from app.api.v1.endpoints.devices import browse_library
from app.db.session import AsyncSessionLocal


class FamilyTests(unittest.TestCase):
    def test_cml_three_views_are_one_device_not_whole_table(self):
        families = build_families(manifest()['items'])
        cml = next(f for f in families if f['id'] == 'ct:cml250a')
        self.assertEqual({v['face'] for v in cml['views']}, {'front', 'side', 'top'})
        self.assertEqual(len(cml['views']), 3)
        self.assertIn('CML250A', cml['name'])
        self.assertTrue(all('400' not in a for a in cml['asset_ids']))

    def test_lamps_shared_across_libraries_but_colors_stay_separate(self):
        families = build_families(manifest()['items'])
        lamps = [f for f in families if f['id'].startswith('pilot:')]
        self.assertEqual(len(lamps), 3)
        self.assertTrue(all(len(f['views']) == 1 for f in lamps))
        self.assertIn('Đèn báo pha màu vàng', [f['name'] for f in lamps])

    def test_unrelated_blocks_and_source_tables_are_not_components(self):
        from app.services.cad.device_families import usable_component
        for name in ('khungtenAsean', 'KHUNG CHUẨN', 'fdfd', '$AUDIT_BAD_BLOCK_RECORD1'):
            self.assertFalse(usable_component({'name': name, 'library': 'formtu'}))
        self.assertFalse(usable_component({'name': 'Đèn báo', 'library': 'source_cells'}))
        self.assertTrue(usable_component({'name': 'Q_FAN120X120', 'library': 'formtu'}))
        from app.services.cad.library_taxonomy import classify
        self.assertEqual(classify('Tu 30KVAR')['group'], 'Tụ bù và cuộn kháng')

    def test_mechanical_dimensions_do_not_imply_safe_installation(self):
        from types import SimpleNamespace
        from app.services.cad.mounting_profile import mounting_profile, SIDES
        model = SimpleNamespace(dimensions={'w': 100, 'h': 200, 'd': 80}, parameters={'_verified': True})
        self.assertFalse(mounting_profile(model)['ready_for_layout'])
        model.parameters['mounting_profile'] = dict(dimensions_verified=True, wiring_verified=True,
            thermal_verified=True, source='model installation drawing, revision A', clearances_mm=dict.fromkeys(SIDES, 20))
        self.assertTrue(mounting_profile(model)['ready_for_layout'])
        model.parameters['mounting_profile']['clearances_mm']['top'] = float('nan')
        self.assertFalse(mounting_profile(model)['ready_for_layout'])

    def test_unknown_face_is_not_guessed_by_ratio(self):
        from app.api.v1.endpoints.cad_library import guess_view_label
        self.assertEqual(guess_view_label(10, 100), 'Hình nguồn')

    def test_pagination_and_filter_happen_after_grouping(self):
        async def run():
            async with AsyncSessionLocal() as db:
                first = await browse_library(limit=2, db=db)
                second = await browse_library(skip=2, limit=2, db=db)
                self.assertEqual(len(first['items']), 2)
                self.assertFalse({i['id'] for i in first['items']} & {i['id'] for i in second['items']})
                lamps = await browse_library(q='Đèn báo pha màu vàng', db=db)
                self.assertEqual(lamps['total'], 1)
                self.assertEqual(len(lamps['items'][0]['parameters']['cad']['views']), 1)
                side = await browse_library(q='CML250A', face='side', db=db)
                self.assertEqual(side['total'], 1)
                self.assertEqual(side['items'][0]['parameters']['variant_count'], 1)
                self.assertEqual(len(side['items'][0]['parameters']['cad']['views']), 3)
        asyncio.run(run())


if __name__ == '__main__': unittest.main()
