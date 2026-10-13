import base64
import io
import unittest

import ezdxf

from app.services.cad.cabinet_templates import candidates, generate, inventory, centered_lock_offset


class OriginalFormSelectionTests(unittest.TestCase):
    def test_lock_stays_centered_without_stretching_or_moving_hinge(self):
        from ezdxf import bbox
        from ezdxf.math import Vec3
        doc = ezdxf.new()
        block = doc.blocks.new('AB301-2-1.2')
        block.add_lwpolyline([(0, 0), (20, 0), (20, 60), (0, 60)], close=True)
        lock = doc.modelspace().add_blockref(block.name, (40, 325))
        box = bbox.extents([lock], fast=True)
        axes = [[dict(start=0, end=500, dimension='width')],
                [dict(start=0, end=700, dimension='height')]]
        for height in (550, 700, 850):
            offset = centered_lock_offset(lock, box, axes, dict(height=height-700, width=50))
            center = (box.extmin + box.extmax) / 2 + offset
            self.assertAlmostEqual(center.y, height / 2)
            self.assertAlmostEqual(center.x, 50)
            copy = lock.copy()
            copy.translate(*offset)
            self.assertTrue(bbox.extents([copy], fast=True).size.isclose(box.size))
        hinge = doc.modelspace().add_blockref('HL036-1 Front', (40, 325))
        self.assertIsNone(centered_lock_offset(hinge, box, axes, dict(height=150, width=50)))
        with self.assertRaises(ValueError):
            centered_lock_offset(lock, box, [axes[0], []], dict(height=150, width=50))

    def test_original_size_available_without_resize_approval(self):
        item = next(i for i in inventory() if i['dimensions'])
        dimensions = item['dimensions']
        self.assertTrue(candidates(dimensions, items=[item])[0]['can_generate'])
        changed = {**dimensions, 'height': dimensions['height'] + 50}
        supported = 'height' in item.get('stretch_dimensions', [])
        self.assertEqual(candidates(changed, items=[item])[0]['can_generate'], supported)
        if supported:
            self.assertTrue(generate(item['id'], changed))
        else:
            with self.assertRaises(ValueError): generate(item['id'], changed)

    def test_original_source_produces_readable_dxf(self):
        item = next(i for i in inventory() if i['dimensions'])
        content = generate(item['id'], item['dimensions'], 'TEST SOURCE')
        doc = ezdxf.read(io.StringIO(content.decode('utf-8') if isinstance(content, bytes) else content))
        self.assertGreater(len(doc.modelspace()), 0)

    def test_optional_title_fields_and_portable_logo(self):
        from PIL import Image
        item = next(i for i in inventory() if i['source_handle'] == '1B3E8')
        stream = io.BytesIO()
        Image.new('RGBA', (10, 6), (0, 120, 220, 255)).save(stream, format='PNG')
        info = dict(company_name='ACME', customer_name='CLIENT',
                    designer_name='DESIGNER TEST', drawing_date='11/10/2026',
                    logo_data='data:image/png;base64,' + base64.b64encode(stream.getvalue()).decode())
        doc = ezdxf.read(io.StringIO(generate(item['id'], item['dimensions'], 'CABINET TEST', info)))
        texts = [e.plain_text() for e in doc.modelspace().query('MTEXT')]
        for value in ('ACME', 'CLIENT', 'DESIGNER TEST', '11/10/2026', 'CABINET TEST'):
            self.assertIn(value, texts)
        self.assertTrue(any(e.dxf.get('true_color') == 0x0078dc for e in doc.modelspace().query('SOLID')))
        self.assertEqual(len(doc.modelspace().query('IMAGE')), 0)
        self.assertFalse(doc.audit().has_errors)
        with self.assertRaises(ValueError):
            generate(item['id'], item['dimensions'], title_info={'logo_data': 'bad'})

    def test_reported_470_width_changes_geometry_and_dimensions(self):
        from collections import Counter
        item = next(i for i in inventory() if i['source_handle'] == '11649A5')
        requested = dict(height=700, width=470, depth=250)
        self.assertTrue(candidates(requested, items=[item])[0]['can_generate'])
        before = ezdxf.read(io.StringIO(generate(item['id'], item['dimensions'])))
        after = ezdxf.read(io.StringIO(generate(item['id'], requested)))
        radii = lambda doc: Counter(round(e.dxf.radius, 5) for e in doc.modelspace().query('CIRCLE ARC'))
        self.assertEqual(radii(before), radii(after))
        texts = [e.plain_text() for e in after.modelspace().query('MTEXT')]
        texts += [e.dxf.text for e in after.modelspace().query('TEXT')]
        self.assertIn('470', texts)
        self.assertIn('C700xR470xS250', texts)
        self.assertNotIn('500', texts)
        from ezdxf import bbox
        outlines = [bbox.extents([e], fast=True) for e in after.modelspace().query('LWPOLYLINE POLYLINE')]
        self.assertTrue(any(b.has_data and abs(b.size.x-470) < .01 and abs(b.size.y-700) < .01 for b in outlines))
        self.assertFalse(after.audit().has_errors)
        self.assertFalse(candidates(dict(height=700,width=300,depth=250), items=[item])[0]['can_generate'])
        with self.assertRaises(ValueError): generate(item['id'], dict(height=700,width=300,depth=250))

    def test_missing_dimensions_remain_unavailable(self):
        item = dict(id='missing', kind='indoor', dimensions=None, status='needs_review')
        self.assertFalse(candidates(dict(height=700, width=500, depth=250), items=[item])[0]['can_generate'])


if __name__ == '__main__':
    unittest.main()
