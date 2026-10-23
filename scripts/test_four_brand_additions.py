import json,re,unittest
from pathlib import Path
import ezdxf
from app.services.cad.ls_view_coverage import view_coverage
ROOT=Path(__file__).resolve().parents[1];CAT=ROOT/'data/CatalogTB';OUT=ROOT/'docs/four-brands-additions-2026-10-22'
class ReviewedAdditionsTests(unittest.TestCase):
 def test_independent_same_variant_faces_and_geometry_health(self):
  paths=[p for maker in ['abb','ls'] for p in json.loads((OUT/(maker+'-profiles.json')).read_text(encoding='utf8'))]
  self.assertEqual(len(paths),10)
  for relative in paths:
   p=CAT/relative;raw=json.loads(p.read_text(encoding='utf8'))
   self.assertEqual(len(raw['cad_don']),6);self.assertTrue(view_coverage(raw['cad_don'])['complete']);self.assertFalse(raw['auto_select'])
   for v in raw['cad_don']:
    d=ezdxf.readfile(p.parent/v['duong_dan']);a=d.audit();self.assertEqual(d.units,4);self.assertFalse(a.errors);self.assertFalse(a.fixes);self.assertGreater(len(d.modelspace()),5)
 def test_abb_price_scope_does_not_include_high_current_or_wrong_poles(self):
  for relative in json.loads((OUT/'abb-profiles.json').read_text(encoding='utf8')):
   raw=json.loads((CAT/relative).read_text(encoding='utf8'));pole=raw['thong_so']['so_cuc'];opts=raw['catalog_tham_khao']['options']
   self.assertEqual(len(opts),9)
   for o in opts:
    self.assertIn('S20'+pole[0]+'M-',o['specifications']['Tên hàng']);self.assertLessEqual(float(o['specifications']['In (A)']),63);self.assertFalse(o['exact_cad_match'])
 def test_ls_hd_is_not_substituted_for_h_n_or_l_in_pricebook(self):
  poles=set()
  for relative in json.loads((OUT/'ls-profiles.json').read_text(encoding='utf8')):
   raw=json.loads((CAT/relative).read_text(encoding='utf8'));self.assertEqual(raw['catalog_tham_khao']['options'],[]);self.assertEqual(raw['ma_dong_san_pham'],'LA63Hd');poles.add(raw['thong_so']['so_cuc'])
  self.assertEqual(poles,{'1P','1P+N','2P','3P','3P+N','4P'})
 def test_lrd14_uses_shared_cad_without_reusing_lrd21_current(self):
  p=CAT/'Schneider/ThietBi/OFFICIAL-MCADPD0004675-LRD21/thong_tin_thiet_bi.json';raw=json.loads(p.read_text(encoding='utf8'));opts={o['model']:o for o in raw['catalog_tham_khao']['options']}
  self.assertEqual(opts['LRD14']['specifications']['Dải chỉnh định (A)'],'7–10');self.assertEqual(opts['LRD21']['specifications']['Dải chỉnh định (A)'],'12–18');self.assertEqual(len(raw['cad_don']),6)
 def test_inconsistent_chint_sources_are_held_outside_visible_profiles(self):
  for name in ['NXB-63-3P','NB1-63H-1P','NDK-100']:
   raw=json.loads((CAT/'Chint/NguonBenNgoai'/name/'review.json').read_text(encoding='utf8'));self.assertEqual(raw['status'],'held_not_published');self.assertFalse((CAT/'Chint/ThietBi'/('OFFICIAL-'+name)).exists())
 def test_timer_faces_match_specific_mounting_variant(self):
  from app.services.catalog_view_health import quarantined
  for relative in json.loads((OUT/'chint-profiles.json').read_text(encoding='utf8')):
   p=CAT/relative;raw=json.loads(p.read_text(encoding='utf8'));self.assertEqual(len(raw['cad_don']),6);self.assertTrue(view_coverage(raw['cad_don'])['complete'])
   for v in raw['cad_don']:
    d=ezdxf.readfile(p.parent/v['duong_dan']);a=d.audit();self.assertEqual(d.units,4);self.assertFalse(a.errors);self.assertFalse(a.fixes)
   if raw['ma_dong_san_pham']=='KG316T':
    self.assertEqual(raw['thong_so']['Kiểu lắp'],'Gá vít');self.assertEqual(raw['catalog_tham_khao']['options'][0]['specifications']['Mã hàng'],'309010')
  self.assertTrue(quarantined('TB-faac1fd5308bee1e','B_ce1fd0282461'))
if __name__=='__main__':unittest.main()
