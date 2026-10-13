import unittest,json,hashlib,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'BE_AIDE'))
from app.services.device_catalog_engine import DeviceCatalogEngine
from app.services.cad import catalogtb_assets as ca
class Evidence(unittest.TestCase):
 def test_complete_image_extraction(self):
  rows=json.loads((ROOT/'outputs/catalogtb-84-evidence/evidence.json').read_text(encoding='utf8'));self.assertEqual(len(rows),84)
  for row in rows:
   for view in row['views']:
    self.assertIsNone(view['render_error']);self.assertTrue((ROOT/'outputs/catalogtb-84-evidence'/view['image']).is_file())
 def test_all_decisions_loaded_without_auto_insertion(self):
  engine=DeviceCatalogEngine.get_instance();rows=json.loads((ROOT/'outputs/catalogtb-84-evidence/decisions.json').read_text(encoding='utf8'))
  for row in rows:
   self.assertTrue(any(r['reference_path']==row['profile'] for r in engine.search_references(row['category_code'],query=row['name'],limit=835)))
   profile=json.loads((ca.ROOT/row['profile']).read_text(encoding='utf8'));self.assertFalse(profile['auto_select'])
   self.assertTrue(all(not v['bo_tri_trong_tu']['cho_phep_chen'] for v in profile['cad_don']))
 def test_original_cad_hashes_unchanged(self):
  m=json.loads((ca.ROOT/'ai_library_manifest.json').read_text(encoding='utf8'));paths={v['path'] for r in json.loads((ROOT/'outputs/catalogtb-84-evidence/evidence.json').read_text(encoding='utf8')) for v in r['views']}
  for item in m['physical_cad_file_inventory']:
   path=item.get('path');expected=item.get('sha256')
   if path in paths and expected:self.assertEqual(hashlib.sha256((ca.ROOT/path).read_bytes()).hexdigest(),expected)
if __name__=='__main__':unittest.main(verbosity=2)
