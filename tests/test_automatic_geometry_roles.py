import unittest
from unittest.mock import patch
from app.services.cad.automatic_selection import select_device_geometry


class GeometryRoleTests(unittest.TestCase):
    @patch('app.services.cad.automatic_selection.candidates', return_value=[])
    def test_legacy_asia_is_not_used_as_manufacturer_filter(self, candidates):
        row = select_device_geometry({'category': 'RELAY', 'brand': 'Asia'})
        candidates.assert_called_once_with('RELAY', None, None, measurement_function=None)
        self.assertEqual(row['brand'], 'Asian')
        self.assertEqual(row['source_brand_label'], 'Asia')
        self.assertTrue(row['cad']['requires_selection'])

    def asset(self, identifier='tb:1'):
        return {'id': identifier, 'brand': 'LS', 'specifications': {}, 'electrical_variants': []}

    @patch('app.services.cad.automatic_selection.instance_count')
    @patch('app.services.cad.automatic_selection.selected_envelope', return_value=(40, 60, 30))
    @patch('app.services.cad.automatic_selection.candidates')
    def test_voltmeter_and_selector_search_the_correct_function(self, candidates, envelope, count):
        candidates.return_value = [self.asset()]
        row = select_device_geometry({'category': 'SWITCH', 'name': 'Công tắc chọn điện áp vôn kế',
                                      'brand': 'Asian', 'selection_source': 'unspecified_brand'})
        candidates.assert_called_once_with('SELECTOR', None, None, measurement_function='voltage')
        self.assertEqual(row['category'], 'SELECTOR')
        self.assertEqual(row['source_category'], 'SWITCH')
        self.assertEqual(row['brand'], 'Asian')
        self.assertEqual(row['cad']['geometry_brand'], 'LS')

    @patch('app.services.cad.automatic_selection.instance_count')
    @patch('app.services.cad.automatic_selection.selected_envelope', return_value=(40, 60, 30))
    @patch('app.services.cad.automatic_selection.candidates')
    def test_unspecified_brand_can_select_a_compatible_reference(self, candidates, envelope, count):
        candidates.return_value = [self.asset(), self.asset('tb:2')]
        row = select_device_geometry({'category': 'LIGHT', 'brand': 'Asian',
                                      'selection_source': 'unspecified_brand'})
        self.assertFalse(row['cad']['requires_selection'])
        self.assertFalse(row['cad']['exact_model'])

    @patch('app.services.cad.automatic_selection.candidates')
    def test_breaker_without_ka_evidence_is_not_selected(self, candidates):
        candidates.return_value = [{**self.asset(), 'specifications': {'dong_dinh_muc': '200'}}]
        row = select_device_geometry({'category': 'MCCB', 'in_a': 200, 'icu_ka': 85,
                                      'brand': 'Asian', 'selection_source': 'unspecified_brand'})
        self.assertTrue(row['cad']['requires_selection'])
        self.assertIn('khả năng cắt', row['cad']['automatic_selection']['rejected'][0]['reason'])

    @patch('app.services.cad.automatic_selection.instance_count')
    @patch('app.services.cad.automatic_selection.selected_envelope', side_effect=ValueError('Missing side view'))
    @patch('app.services.cad.automatic_selection.candidates')
    def test_existing_cad_is_not_reported_absent_when_side_view_is_missing(self,candidates,envelope,count):
        candidates.return_value=[self.asset()]
        row=select_device_geometry({'category':'TIMER','brand':'Asian'})
        self.assertEqual(row['cad']['asset_id'],'tb:1')
        self.assertEqual(row['cad']['automatic_selection']['reason'],'matched_cad_missing_envelope')
        self.assertNotIn('dimensions',row)

    @patch('app.services.cad.automatic_selection.instance_count')
    @patch('app.services.cad.automatic_selection.selected_envelope', side_effect=ValueError('Missing side view'))
    @patch('app.services.cad.automatic_selection.candidates')
    def test_multiple_existing_views_keep_missing_envelope_diagnostic(self,candidates,envelope,count):
        candidates.return_value=[self.asset(),self.asset('tb:2')]
        row=select_device_geometry({'category':'RELAY','brand':'Asia'})
        self.assertEqual(row['cad']['automatic_selection']['reason'],'matched_cad_missing_envelope')
        self.assertEqual(row['cad']['automatic_selection']['matched_asset_ids'],['tb:1','tb:2'])
        self.assertNotIn('asset_id',row['cad'])
