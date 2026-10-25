import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.services.ai.pdf_page_scope import requested_pdf_pages as pages
class PageScope(unittest.TestCase):
 def test_both_pages(self):self.assertEqual(pages('Bóc tách cả hai trang PDF Đơn 457 PX1 và PX2',2),[1,2])
 def test_all_pages_overrides_viewer(self):self.assertEqual(pages('toàn bộ trang',2,2),[1,2])
 def test_no_panel_tag_is_page(self):self.assertEqual(pages('tủ PX2 và contactor P2',2),[])
 def test_range(self):self.assertEqual(pages('trang 1-2',2),[1,2])
 def test_list(self):self.assertEqual(pages('trang 1 và 3',3),[1,3])
 def test_single(self):self.assertEqual(pages('trang số 2',3),[2])
 def test_explicit_page_overrides_current_viewer(self):self.assertEqual(pages('Chỉ trang 2',2,1),[2])
 def test_skip_clause_is_not_an_inclusion(self):self.assertEqual(pages('Chỉ bóc tách trang 2, bỏ qua trang 1 trống',2,1),[2])
 def test_all_except_cover(self):self.assertEqual(pages('Tất cả trang, trừ trang 1',3,1),[2,3])
 def test_exclusion_only(self):self.assertEqual(pages('Bỏ qua trang 1',3,1),[2,3])
 def test_invalid_explicit_page_does_not_fall_back(self):
  with self.assertRaises(ValueError):pages('Chỉ trang 9',2,1)
 def test_exclusion_range(self):self.assertEqual(pages('toàn bộ trang; không bóc tách trang 1-2',4),[3,4])
if __name__=='__main__':unittest.main(verbosity=2)
