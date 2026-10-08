import unittest
from unittest.mock import patch
from app.services.ai.auxiliary_devices import expand_devices


class AuxiliaryDevicesTests(unittest.TestCase):
    def parent(self, accessories):
        return {'name': 'MCCB', 'category': 'MCCB', 'panel_code': 'TĐT',
                'accompanying_accessories': accessories}

    @patch('app.services.ai.auxiliary_devices.candidates', return_value=[])
    def test_evidenced_selector_survives_meter_already_being_a_standalone_row(self, _):
        rows = expand_devices([{'category': 'METER', 'name': 'Vôn kế', 'quantity': 1,
                                'quantity_basis': '0–500V kèm chuyển mạch', 'panel_code': 'TĐT'}])
        self.assertEqual([r['category'] for r in rows], ['METER', 'SELECTOR'])
        self.assertEqual(expand_devices(rows), rows)

    @patch('app.services.ai.auxiliary_devices.candidates', return_value=[])
    def test_three_fuses_are_preserved_and_expansion_is_idempotent(self, _):
        rows = expand_devices([self.parent([{'name': 'Cầu chì', 'quantity': 3,
                                              'evidence': '3 cầu chì R S T'}])])
        self.assertEqual(rows[1]['quantity'], 3)
        self.assertEqual(expand_devices(rows), rows)
        self.assertEqual(rows[0]['accompanying_accessories'], [])

    @patch('app.services.ai.auxiliary_devices.candidates', return_value=[])
    def test_unknown_count_or_unevidenced_accessory_stays_pending(self, _):
        accessories = [{'name': 'Cầu chì', 'evidence': 'Fuse'},
                       {'name': 'Đèn báo', 'quantity': 3}, 'unknown']
        rows = expand_devices([self.parent(accessories)])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['accompanying_accessories'], accessories)

    @patch('app.services.ai.auxiliary_devices.candidates', return_value=[])
    def test_different_lamp_groups_are_not_deduplicated_by_category(self, _):
        rows = expand_devices([{'category': 'LIGHT', 'name': 'Đèn báo nguồn', 'panel_code': 'TĐT'},
                               self.parent([{'name': 'Đèn báo pha', 'quantity': 3,
                                             'evidence': 'R Y B'}])])
        self.assertEqual(len(rows), 3)

    @patch('app.services.ai.auxiliary_devices.candidates')
    def test_single_fuse_does_not_select_three_or_five_unit_cad(self, mocked):
        mocked.return_value = [dict(id=str(q), name='Fuse', face='front', profile_path='f',
                                    status='reference_geometry', components_per_asset=q)
                               for q in (1, 3, 5)]
        row = expand_devices([self.parent([{'name': 'Cầu chì', 'quantity': 1,
                                             'evidence': '1x6A'}])])[1]
        self.assertEqual([r['id'] for r in row['cad']['reference_candidates']], ['1'])


if __name__ == '__main__':
    unittest.main()
