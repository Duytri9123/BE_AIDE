import unittest
import xml.etree.ElementTree as ET
from app.services.cad.device_preview import device_views

class DeviceViewsTests(unittest.TestCase):
    def test_orthographic_dimensions_and_escape(self):
        result = device_views('A<&', {'w':18,'h':86,'d':69})
        self.assertFalse(result['manufacturer_drawing'])
        self.assertEqual([(v['width_mm'],v['height_mm']) for v in result['views']], [(18,86),(69,86),(18,69)])
        for view in result['views']:
            root = ET.fromstring(view['svg'])
            self.assertIn('A<&', ''.join(root.itertext()))

    def test_missing_dimensions_are_not_invented(self):
        for invalid in (None, 0, -1, float('inf'), 'bad'):
            result = device_views('test', {'w':18,'h':86,'d':invalid})
            self.assertIsNotNone(result['views'][0]['svg'])
            self.assertIsNone(result['views'][1]['svg'])
            self.assertIsNone(result['views'][2]['svg'])

if __name__ == '__main__':
    unittest.main()
