import io
import unittest

import ezdxf

from app.services.cad.cabinet_templates import candidates, generate, inventory


class OriginalFormSelectionTests(unittest.TestCase):
    def test_original_size_available_without_resize_approval(self):
        item = next(i for i in inventory() if i['dimensions'])
        dimensions = item['dimensions']
        self.assertTrue(candidates(dimensions, items=[item])[0]['can_generate'])
        changed = {**dimensions, 'height': dimensions['height'] + 50}
        self.assertFalse(candidates(changed, items=[item])[0]['can_generate'])
        with self.assertRaises(ValueError):
            generate(item['id'], changed)

    def test_original_source_produces_readable_dxf(self):
        item = next(i for i in inventory() if i['dimensions'])
        content = generate(item['id'], item['dimensions'], 'TEST SOURCE')
        doc = ezdxf.read(io.StringIO(content.decode('utf-8') if isinstance(content, bytes) else content))
        self.assertGreater(len(doc.modelspace()), 0)

    def test_missing_dimensions_remain_unavailable(self):
        item = dict(id='missing', kind='indoor', dimensions=None, status='needs_review')
        self.assertFalse(candidates(dict(height=700, width=500, depth=250), items=[item])[0]['can_generate'])


if __name__ == '__main__':
    unittest.main()
