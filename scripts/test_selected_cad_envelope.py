import unittest
from unittest.mock import patch
from app.services.cad.catalogtb_assets import candidates
from app.services.cad.device_envelope import selected_envelope
from app.services.cad.physical_layout_engine import PhysicalLayoutEngine

class SelectedEnvelopeTests(unittest.TestCase):
    def test_bkn_mounting_envelope_uses_metadata_not_drawing_annotations(self):
        asset=next(a for a in candidates('MCB',poles=2) if a['profile_path']=='LS/ThietBi/BKN_2P/thong_tin_thiet_bi.json')
        device={'category':'MCB','name':'BKN','cad':{'asset_id':asset['id']}}
        dimensions=selected_envelope(device)
        self.assertAlmostEqual(dimensions[0],36)
        self.assertAlmostEqual(dimensions[1],82)
        self.assertGreater(dimensions[2],70)
        with self.assertRaisesRegex(ValueError,'LS cần bổ sung CAD'):
            PhysicalLayoutEngine.get_component_dimensions({**device,'brand':'LS'})

    def test_missing_side_does_not_invent_depth(self):
        meter=candidates('METER')[0]
        with self.assertRaisesRegex(ValueError,'mặt bên'):
            selected_envelope({'cad':{'asset_id':meter['id']}})

    def test_side_must_match_the_selected_geometry_variant(self):
        front={'id':'tb:front','family_id':'family','variant_id':'fixed','face':'front'}
        sides=[{'id':'tb:side','family_id':'family','variant_id':'fixed','face':'side','placement':{}}, {'id':'tb:other','family_id':'family','variant_id':'withdrawable','face':'side','placement':{}}]
        with patch('app.services.cad.catalogtb_assets.resolve',return_value=front), patch('app.services.cad.catalogtb_assets.assets',return_value=[front,*sides]), patch('app.services.cad.device_envelope._bounds',side_effect=[(100,180),(90,180)]):
            self.assertEqual(selected_envelope({'cad':{'asset_id':'tb:front'}}),(100,180,90))

    def test_unselected_device_does_not_choose_an_asset(self):
        self.assertIsNone(selected_envelope({'category':'MCB'}))

if __name__=='__main__':unittest.main()
