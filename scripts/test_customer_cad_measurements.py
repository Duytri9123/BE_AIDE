import hashlib, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import ezdxf
from scripts import measure_customer_cad_views as measurements

class CadMeasurementsTests(unittest.TestCase):
    def test_annotation_scan_handles_dxf_line_endings(self):
        self.assertTrue(measurements.has_annotation_entities(b'  0\r\nDIMENSION\r\n  5\r\nA\r\n'))
        self.assertTrue(measurements.has_annotation_entities(b'  0\nLEADER\n  5\nA\n'))
        self.assertFalse(measurements.has_annotation_entities(b'  0\nTEXT\n  1\nDIMENSION\n'))
    def test_nested_geometry_is_measured_without_remote_text(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'front.dxf'
            doc = ezdxf.new(); doc.units = 4
            block = doc.blocks.new('body')
            block.add_lwpolyline([(0, 0), (90, 0), (90, 155), (0, 155)], close=True)
            block.add_text('not geometry', dxfattribs={'insert': (1000, 1000)})
            doc.modelspace().add_blockref('body', (0, 0)); doc.saveas(path)
            self.assertEqual(measurements.measure(path), '90 × 155')

    def test_non_mm_and_dimension_annotations_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'front.dxf'
            doc = ezdxf.new(); doc.units = 1
            doc.modelspace().add_circle((0, 0), 10); doc.saveas(path)
            with self.assertRaises(ValueError): measurements.measure(path)
            doc.units = 4
            doc.modelspace().add_linear_dim(base=(0, 20), p1=(0, 0), p2=(10, 0))
            doc.saveas(path)
            with self.assertRaises(ValueError): measurements.measure(path)

    def test_changed_source_cannot_reuse_measurements(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'front.dxf'; path.write_bytes(b'original')
            cache = {'front': {'path': 'front.dxf', 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'value': '90 × 155'}}
            with patch.object(measurements, 'CAT', Path(folder)):
                self.assertIn('front', measurements.cached_view_facts(['front'], cache))
                path.write_bytes(b'changed')
                self.assertEqual(measurements.cached_view_facts(['front'], cache), {})

    def test_reused_front_identifiers_stay_in_their_own_device(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'front.dxf'; path.write_bytes(b'source')
            base = {'path': 'front.dxf', 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
            cache = {'first:front': {**base, 'value': '90 × 155'}, 'second:front': {**base, 'value': '120 × 155'}}
            with patch.object(measurements, 'CAT', Path(folder)):
                self.assertEqual(measurements.cached_view_facts(['front'], cache, 'first')['front'][measurements.KEY], '90 × 155')
                self.assertEqual(measurements.cached_view_facts(['front'], cache, 'second')['front'][measurements.KEY], '120 × 155')

if __name__ == '__main__': unittest.main()
