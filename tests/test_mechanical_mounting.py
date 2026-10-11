import unittest
from app.services.cad.mechanical_mounting import mounting_review, check_main_device_depth


class MountingTests(unittest.TestCase):
    def fixture(self):
        return {'dimensions': {'depth': 300}, 'mechanical_anchors': {
            key: {'verified': True, 'source_handles': ['A1'], 'depth_from_rear_mm': value}
            for key, value in [('rebate', 280), ('mounting_plane', 30), ('inner_door_plane', 220)]}}

    def device(self):
        return {'verified_mounting_geometry': {'verified': True, 'source_reference': 'installation-sheet',
                'body_projection_mm': 110, 'operating_plane_range_mm': [180, 200]}}

    def test_bbox_does_not_establish_mounting(self):
        result = mounting_review({'dimensions': {'depth': 300}, 'faces': [{'clean_bounds': [0, 0, 600, 1000]}]})
        self.assertEqual(len(result['missing']), 3)
        self.assertFalse(result['rebate_is_mounting_support'])

    def test_reversed_door_plane_fails(self):
        item = self.fixture()
        item['mechanical_anchors']['inner_door_plane']['depth_from_rear_mm'] = 20
        self.assertEqual(check_main_device_depth(item, self.device())['status'], 'invalid_datum_order')

    def test_handle_must_reach_inner_door(self):
        device = self.device()
        device['verified_mounting_geometry']['operating_plane_range_mm'] = [120, 150]
        result = check_main_device_depth(self.fixture(), device)
        self.assertEqual(result['status'], 'depth_conflict')
        self.assertFalse(result['handle_reaches_inner_door'])

    def test_depth_fit_is_not_fabrication_approval(self):
        result = check_main_device_depth(self.fixture(), self.device())
        self.assertEqual(result['status'], 'depth_fit')
        self.assertEqual(result['mount_to_inner_door_mm'], 190)
        self.assertFalse(result['release_ready'])

    def test_unreferenced_datum_and_nan_rejected(self):
        item = self.fixture()
        item['mechanical_anchors']['rebate']['source_handles'] = []
        item['mechanical_anchors']['mounting_plane']['depth_from_rear_mm'] = float('nan')
        self.assertEqual(mounting_review(item)['missing'], ['rebate', 'mounting_plane'])
