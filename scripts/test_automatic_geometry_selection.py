import unittest
from app.services.cad.automatic_selection import select_device_geometry


class AutomaticGeometrySelectionTests(unittest.TestCase):
    def test_conflicting_typed_and_literal_poles_block_selection(self):
        result = select_device_geometry(dict(category='MCB', brand='LS', spec='2P 16A 6kA',
            poles=3, in_a=16, icu_ka=6, quantity=1))
        self.assertNotIn('asset_id', result['cad'])
        self.assertEqual(result['cad']['automatic_selection']['reason'], 'source_spec_conflict')

    def test_literal_breaking_capacity_cannot_be_lost_in_selection(self):
        result = select_device_geometry(dict(category='MCB', brand='LS',
            spec='1P 16A 10kA', poles=None, in_a=None, icu_ka=None, quantity=1))
        self.assertEqual(result['icu_ka'], 10)
        self.assertNotIn('asset_id', result['cad'])

    def test_literal_two_pole_contactor_cannot_select_three_pole_geometry(self):
        result = select_device_geometry(dict(category='CONTACTOR', brand='LS',
            spec='2P 16A', poles=None, in_a=None, quantity=6, selection_source='default_brand'))
        self.assertEqual(result['poles'], 2)
        self.assertEqual(result['in_a'], 16)
        self.assertNotIn('asset_id', result['cad'])

    def test_selects_compatible_ls_family_without_frontend_picker(self):
        result = select_device_geometry(dict(category='MCB', brand='LS', poles=2,
                                             quantity=3, in_a=16, icu_ka=6))
        self.assertTrue(result['cad']['asset_id'].startswith('tb:'))
        self.assertFalse(result['cad']['requires_selection'])
        self.assertTrue(all(result['dimensions'][k] > 0 for k in ('w', 'h', 'd')))

    def test_does_not_substitute_wrong_rating_to_unblock_design(self):
        result = select_device_geometry(dict(category='MCB', brand='LS', poles=3,
                                             quantity=1, in_a=20, icu_ka=10))
        self.assertNotIn('asset_id', result['cad'])
        self.assertEqual(len(result['cad']['automatic_selection']['rejected']), 2)

    def test_explicit_unknown_model_is_not_replaced_with_generic_family(self):
        result = select_device_geometry(dict(category='MCB', brand='LS', poles=2,
                                             quantity=1, part_number='DOES-NOT-EXIST'))
        self.assertNotIn('asset_id', result['cad'])

    def test_default_brand_can_fall_back_to_documented_geometry_proposal(self):
        result = select_device_geometry(dict(category='MCB', brand='LS', poles=3,
            quantity=1, in_a=20, icu_ka=10, selection_source='default_brand'))
        self.assertEqual(result['brand'], 'Schneider Electric')
        self.assertEqual(result['cad']['electrical_selection_proposals'][0]['model'], 'A9F84320')
        self.assertFalse(result['cad']['exact_model'])
        self.assertFalse(result['cad']['electrical_selection_proposals'][0]['geometry_exact_model_verified'])


if __name__ == '__main__':
    unittest.main()
