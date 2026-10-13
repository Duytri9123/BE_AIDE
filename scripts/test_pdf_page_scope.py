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
if __name__=='__main__':unittest.main(verbosity=2)
