import unittest
from app.api.v1.endpoints.cad_library import manifest
from app.services.cad.device_families import build_families
from app.services.cad.library_assets import requested_asset

class RecognitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.items=manifest()['items'];cls.by_id={a['id']:a for a in cls.items};cls.families=build_families(cls.items)
    def test_source_filename_is_not_brand(self):
        a=self.by_id['c12ecbaac6ff4dc89675']
        self.assertEqual(a['brand'],'RISESUN')
        self.assertIn('RT18-32',a['recognition']['name'])
    def test_robot_is_a_stabilizer_not_cabinet(self):
        r=self.by_id['c265e45d48a3890e9520']['recognition']
        self.assertEqual(r['brand'],'ROBOT');self.assertIn('350 VA',r['name']);self.assertEqual(r['face'],'front')
    def test_emic_faces_share_identity_and_brand(self):
        f=next(f for f in self.families if f['id']=='emic:EM4H06')
        self.assertEqual(f['brand'],'EMIC');self.assertEqual({v['face'] for v in f['views']},{'front','side','top'})
    def test_fuse_assembly_is_not_three_views(self):
        families=[f for f in self.families if f['id'].startswith('fuse:risesun:')]
        self.assertEqual(len(families),2)
        self.assertTrue(all(len(f['views'])==1 for f in families))
    def test_power_supply_is_not_transformer(self):
        self.assertEqual(self.by_id['25311ebe598e146d593e']['group'],'Bộ nguồn DC')
    def test_hinge_sections_not_lost(self):
        f=next(f for f in self.families if f['id']=='hinge:HL003-2')
        self.assertEqual(len([v for v in f['views'] if v['face']=='section']),2)
    def test_unknown_view_cannot_be_used_as_front(self):
        unknown=next(f for f in self.families if all(v['face']=='unknown' for v in f['views']))
        with self.assertRaisesRegex(ValueError,'mặt trước'):
            requested_asset({'cad':{'asset_id':unknown['thumbnail_id']}})
    def test_dimensions_read_from_source_not_verified_for_installation(self):
        a=next(a for a in self.items if a['name']=='06 - N - SC MCCB EZC100 3 PHASE')
        self.assertEqual(a['recognition']['dimensions_from_text'],{'w':75.0,'h':130.0,'d':60.0})
        self.assertFalse(a['recognition']['ai_auto_select'])
if __name__=='__main__':unittest.main()
