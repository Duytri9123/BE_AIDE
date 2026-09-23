import unittest
from scripts.export_device_layouts import block_brand
from scripts.build_cad_component_catalog import component_type
from app.services.cad.device_preview import device_views
from app.api.v1.endpoints.cad_library import manifest,download_layout,render_layout_svg
import xml.etree.ElementTree as ET

class MultiBrandTests(unittest.TestCase):
 def test_mixed_brand_library(self):
  self.assertEqual(block_brand('HYUNDAI MCCB HGM100E- 3P','Chint'),'Hyundai')
  self.assertEqual(block_brand('Den DO','Chint'),'Chưa xác định hãng')
  self.assertEqual(block_brand('nxm-125-1','Schneider Electric'),'Chint')
 def test_accessory_categories(self):
  self.assertEqual(component_type('Banlela-1'),'Bản lề')
  self.assertEqual(component_type('Ampere-Meter-front'),'Đồng hồ')
  self.assertIsNone(component_type('3234t4etgewtew'))
 def test_round_lamp_and_unknown_depth(self):
  views=device_views('lamp',{}, {'outer_dia_mm':29})['views']
  self.assertIn('<circle',views[0]['svg'])
  self.assertIsNone(views[1]['svg'])
 def test_manifest_unique_and_units_preserved(self):
  items=manifest()['items']
  self.assertEqual(len(items),len({i['id'] for i in items}))
  for source in ('chint','combined','schneider'):
   item=next(i for i in items if i['library']==source)
   self.assertTrue(download_layout(item['id']).path.is_file())
   if source!='combined': self.assertIsNone(item['width_mm'])
 def test_actual_hinge_svg(self):
  item=next(i for i in manifest()['items'] if i['name']=='Banlela-1')
  root=ET.fromstring(render_layout_svg(item['id']))
  self.assertTrue(root.tag.endswith('svg'))

if __name__=='__main__': unittest.main()
