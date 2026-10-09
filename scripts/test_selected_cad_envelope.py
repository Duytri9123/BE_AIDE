import unittest
from app.services.cad.catalogtb_assets import candidates
from app.services.cad.device_envelope import selected_envelope
from app.services.cad.physical_layout_engine import PhysicalLayoutEngine


class SelectedEnvelopeTests(unittest.TestCase):
    def test_bkn_mounting_envelope_uses_metadata_not_drawing_annotations(self):
        asset = next(a for a in candidates('MCB',poles=2) if 'BKN' in a['name'])
        device = {'category':'MCB','name':'BKN','cad':{'asset_id':asset['id']}}
        dimensions = selected_envelope(device)
        self.assertAlmostEqual(dimensions[0],36)
        self.assertAlmostEqual(dimensions[1],82)
        self.assertGreater(dimensions[2],70)
        self.assertEqual(PhysicalLayoutEngine.get_component_dimensions(device),dimensions)

    def test_missing_side_does_not_invent_depth(self):
        meter = candidates('METER')[0]
        with self.assertRaisesRegex(ValueError,'mặt bên'):
            selected_envelope({'cad':{'asset_id':meter['id']}})

    def test_unselected_device_does_not_choose_an_asset(self):
        self.assertIsNone(selected_envelope({'category':'MCB'}))


if __name__ == '__main__':
    unittest.main()
