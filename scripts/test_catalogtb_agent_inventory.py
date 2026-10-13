from pathlib import Path
import sys,json,hashlib,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from app.services.cad import catalogtb_assets as ca

class AgentInventory(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.manifest=json.loads((ca.ROOT/'ai_library_manifest.json').read_text(encoding='utf8'));cls.assets=ca.assets(refresh=True)
 def test_all_profiles_are_discoverable(self):
  disk={p.relative_to(ca.ROOT).as_posix() for p in ca.ROOT.rglob('thong_tin_thiet_bi.json')}
  self.assertEqual(disk,{r['profile'] for r in self.manifest['items']})
  self.assertEqual(disk,{r['profile_path'] for r in self.assets})
 def test_all_existing_views_are_exposed(self):
  expected=sum(v['file_exists'] for r in self.manifest['items'] for v in r['views'])
  self.assertEqual(expected,len(self.assets))
 def test_profile_contents_unchanged(self):
  for r in self.manifest['items']:self.assertEqual(hashlib.sha256((ca.ROOT/r['profile']).read_bytes()).hexdigest(),r['sha256'])
 def test_fuse_search_preserves_holder_subtype(self):
  choices=ca.candidates('FUSE');self.assertTrue(choices)
  self.assertTrue(any(r['category']=='FUSE_HOLDER' for r in choices))
  self.assertTrue(all(not r['exact_model'] for r in choices))
 def test_terminals_are_not_lost_by_wiring_face(self):
  choices=ca.candidates('TERMINAL');self.assertEqual(len(choices),37)
  self.assertTrue(any(r['face']=='wiring' for r in choices))
 def test_unclassified_is_present_and_blocked_for_insertion(self):
  from unittest.mock import patch
  with patch.object(ca,'assets',return_value=[dict(id='unknown-test',category='UNCLASSIFIED')]):
   with self.assertRaisesRegex(ValueError,'chưa xác định'):ca.resolve('unknown-test')
 def test_supply_is_pending_not_absent(self):
  row=self.manifest['order_457_requirements']['POWER_SUPPLY']
  self.assertGreater(row['discoverable_profiles'],0)
  self.assertEqual(row['status'],'present_but_view_or_permission_pending')

if __name__=='__main__':unittest.main(verbosity=2)
