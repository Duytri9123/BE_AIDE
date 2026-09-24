import io
import unittest
from collections import Counter

import ezdxf
from ezdxf.disassemble import recursive_decompose

from app.services.cad.cabinet_templates import candidates, generate, inventory, resolve, source_path


def texts(doc):
    return [e.text if e.dxftype() == 'MTEXT' else e.dxf.text
            for e in recursive_decompose(doc.modelspace()) if e.dxftype() in ('TEXT', 'MTEXT', 'ATTRIB')]


def types(entities):
    # Standalone attributes become visible TEXT for portable insertion.
    return Counter('TEXT' if e.dxftype() == 'ATTRIB' else e.dxftype() for e in entities)


class CabinetSourceTests(unittest.TestCase):
    def test_inventory_keeps_unclassified_and_incomplete_sheets(self):
        items = inventory()
        self.assertGreaterEqual(len(items), 339)
        self.assertTrue(any(i['kind'] == 'unknown' for i in items))
        self.assertTrue(any(i['dimensions'] is None for i in items))
        self.assertTrue(all(source_path(i).is_file() for i in items))

    def test_nearest_selection_never_crosses_type(self):
        rows = candidates(dict(height=1500, width=1400, depth=450), 'outdoor')
        self.assertTrue(rows)
        self.assertTrue(all(i['kind'] == 'outdoor' for i in rows))
        distances = [i['distance'] for i in rows if i['distance'] is not None]
        self.assertEqual(distances, sorted(distances))

    def test_original_example_resizes_geometry_and_dimension_labels(self):
        original = ezdxf.readfile(source_path(resolve('formtu-10a15b')))
        before = list(recursive_decompose(original.modelspace()))
        result = ezdxf.read(io.StringIO(generate('formtu-10a15b', dict(height=1500, width=1400, depth=450), 'MSB-01')))
        after = list(result.modelspace())
        self.assertEqual(types(before), types(after))
        self.assertEqual(sorted(round(e.dxf.radius, 6) for e in before if e.dxftype() == 'CIRCLE'),
                         sorted(round(e.dxf.radius, 6) for e in after if e.dxftype() == 'CIRCLE'))
        labels = texts(result)
        self.assertIn('MSB-01', labels)
        self.assertIn('1500x1400x450', labels)
        self.assertGreaterEqual(sum('1500' == text for text in labels), 4)
        self.assertNotIn('1600', labels)
        # Front and inner face outlines retain the exact 1400 mm width.
        outlines = []
        for e in result.modelspace().query('LWPOLYLINE'):
            points = list(e.get_points('xy'))
            if len(points) == 4:
                outlines.append((max(p[0] for p in points)-min(p[0] for p in points),
                                 max(p[1] for p in points)-min(p[1] for p in points)))
        self.assertGreaterEqual(sum(abs(w-1400)<.01 and abs(h-1500)<.01 for w,h in outlines), 2)
        self.assertFalse(result.audit().errors)

    def test_outdoor_source_preserves_all_detail_and_optional_blank_name(self):
        original = ezdxf.readfile(source_path(resolve('formtu-2ce34e')))
        result = ezdxf.read(io.StringIO(generate('formtu-2ce34e', dict(height=1000, width=600, depth=350))))
        self.assertEqual(types(recursive_decompose(original.modelspace())), types(result.modelspace()))
        labels = texts(result)
        self.assertFalse(any('VÕ TỦ' in text or 'VỎ TỦ' in text for text in labels))
        self.assertTrue(any('NGOÀI TRỜI' in text for text in labels))
        self.assertIn('1000', labels)
        self.assertGreater(len(result.modelspace()), 1500)

    def test_unsupported_resize_does_not_return_mislabelled_cad(self):
        with self.assertRaises(ValueError):
            generate('formtu-10a15b', dict(height=3500, width=1400, depth=450))


if __name__ == '__main__':
    unittest.main()
