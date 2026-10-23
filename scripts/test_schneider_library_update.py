import json,unittest
from pathlib import Path
import ezdxf
from app.services.catalog_view_health import targeted,displayable,quarantined
from app.services.cad.ls_view_coverage import view_coverage
from scripts.correct_schneider_mcb_pricebook import extract
ROOT=Path(__file__).resolve().parents[1]

class SchneiderUpdateTests(unittest.TestCase):
 def test_schneider_unknown_and_defective_views_are_blocked(self):
  self.assertTrue(targeted('Schneider'));self.assertTrue(targeted('Schneider Electric'))
  self.assertFalse(displayable({'face':'Chưa xác nhận hướng nhìn'}))
  self.assertFalse(displayable({'face':'Mặt trước','linework_review':{'status':'unresolved_visible_geometry_defect'}}))
 def test_mcb_pdf_columns_keep_poles_and_voltage_separate(self):
  rows=extract(ROOT/'tmp/folder-web-review/schneider-2026.pdf')
  self.assertEqual(len(rows),72)
  self.assertEqual(rows['A9F74150'],{'family':'iC60N','poles':'1P','current':'50','voltage':'230','category':'MCB'})
  self.assertEqual(rows['A9F74316']['poles'],'3P');self.assertEqual(rows['A9F74316']['voltage'],'400')
 def test_new_profiles_have_six_valid_same_variant_views(self):
  changes=json.loads((ROOT/'docs/schneider-update-2026-10-21/changes.json').read_text(encoding='utf8'))
  for row in changes['added_families']:
   p=ROOT/'data/CatalogTB'/row['profile'];raw=json.loads(p.read_text(encoding='utf8'))
   self.assertEqual(raw['hang_xac_nhan'],'Schneider Electric');self.assertNotIn('CHINT',raw['tu_khoa_tim_kiem'])
   self.assertEqual(len(raw['cad_don']),6);self.assertTrue(view_coverage(raw['cad_don'])['complete'])
   for v in raw['cad_don']:
    doc=ezdxf.readfile(p.parent/v['duong_dan']);a=doc.audit();self.assertEqual(doc.units,4);self.assertFalse(a.errors);self.assertFalse(a.fixes)
 def test_category_corrections_do_not_change_prices(self):
  old=json.loads((ROOT/'docs/schneider-update-2026-10-21/supplier-pricebooks.before.json').read_text(encoding='utf8'))['items']
  new=json.loads((ROOT/'app/data/supplier_pricebooks.json').read_text(encoding='utf8'))['items']
  self.assertEqual({r['id']:r.get('price') for r in old},{r['id']:r.get('price') for r in new})
  codes=extract(ROOT/'tmp/folder-web-review/schneider-2026.pdf')
  for row in new:
   if row['brand']=='Schneider Electric' and row['sku'] in codes:self.assertEqual(row['category'],'MCB')
 def test_known_ezs400_defect_cannot_be_downloaded_through_old_id(self):
  self.assertTrue(quarantined('TB-8c17af72f7294f70','SCH-D01-C6-I05-STATE-4P-FRONT-VIEW'))

if __name__=='__main__':unittest.main()
