import unittest
from app.services.cad.design_labels import effective_spec, rating_text
from app.services.ai.procurement_review import build_quotation_rows


class DesignLabelTests(unittest.TestCase):
    def test_selected_analysis_rating_overrides_original_rating_field(self):
        device = dict(category='MCCB', spec='3P 250A 85kA', in_a=200, original_spec='3P 200A 85kA')
        self.assertEqual(rating_text(device), '250A')

    def test_frame_name_does_not_change_current_rating(self):
        device = dict(spec='3P 200A 85kA', in_a=200, cad={'name': 'ABN250AF'})
        self.assertEqual(rating_text(device), '200A')

    def test_verified_applied_replacement_labels_and_quote_use_new_spec(self):
        device = dict(category='MCCB', name='MCCB tổng', panel_code='TĐT', quantity=1,
                      spec='3P 200A 85kA', in_a=200, part_number='OLD200',
                      unit_price=100, price_source='catalog',
                      compatible_proposal=dict(proposed_spec='3P 250A 85kA',
                                               applied=True, compatibility_verified=True))
        self.assertEqual(rating_text(device), '250A')
        row = next(r for r in build_quotation_rows([device], {'OLD200': 100}) if r['row_type'] == 'item')
        self.assertEqual(row['spec'], '3P 250A 85kA')
        self.assertEqual(row['original_spec'], '3P 200A 85kA')
        self.assertIsNone(row['unit_price'])
        self.assertNotEqual(row['sku'], 'OLD200')

    def test_unverified_proposal_is_not_applied(self):
        device = dict(spec='3P 200A 85kA', compatible_proposal=dict(proposed_spec='3P 250A 85kA'))
        self.assertEqual(effective_spec(device), '3P 200A 85kA')


if __name__ == '__main__':
    unittest.main()
