import sys, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.api.v1.endpoints import equipment_library as api

class PreviewCache(unittest.TestCase):
 def test_same_path_with_repaired_content_returns_new_pixels(self):
  def svg(color):return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><path fill="'+color+'" d="M0 0H10V10H0Z"/></svg>').encode()
  api._raster_preview_source.cache_clear()
  with patch.object(api,'asset_bytes',side_effect=[svg('red'),svg('blue'),svg('blue')]):
   old=api._raster_preview('same.svg');new=api._raster_preview('same.svg')
   self.assertNotEqual(old,new)
   self.assertEqual(new,api._raster_preview('same.svg'))
  self.assertEqual(api._raster_preview_source.cache_info().hits,1)

if __name__=='__main__':unittest.main()
