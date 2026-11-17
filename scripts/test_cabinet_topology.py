"""Source regression tests for bay layout and projected roof hardware."""
import math
import unittest

from app.services.cad.cabinet_topology import closed_loops, panel_layout, bounds
from app.services.cad.cabinet_preview_3d import preview


def face(key, x, y, w, h):
    return dict(id=key, kind='mounting_plate', label='EQUIPMENT VIEW',
                width=w, height=h, bounds=[x, y, x+w, y+h])


class TopologyRules(unittest.TestCase):
    def test_adjacent_bays_are_kept(self):
        layout = panel_layout([face('left', 100, 0, 900, 1900),
                               face('right', 1000, 0, 900, 1900)], 1800, 1900)
        self.assertEqual([p['x_mm'] for p in layout], [0, 900])
        self.assertTrue(all(p['physical'] for p in layout))

    def test_full_width_projections_do_not_become_extra_bays(self):
        layout = panel_layout([face('first', 0, 0, 800, 1500),
                               face('reference', 2500, 0, 800, 1500)], 800, 1500)
        self.assertEqual(sum(p['physical'] for p in layout), 1)
        self.assertTrue(all(p['basis'] == 'alternate_source_projection' for p in layout))

    def test_separated_half_views_remain_unresolved(self):
        layout = panel_layout([face('first', 0, 0, 400, 1200),
                               face('other', 2000, 0, 400, 1200)], 800, 1200)
        self.assertTrue(all(p['basis'] == 'source_panel_layout_unresolved' for p in layout))

    def test_vertical_slots_keep_heights_and_origins(self):
        layout = panel_layout([face('bottom', 0, 100, 800, 500),
                               face('top', 0, 600, 800, 700)], 800, 1200)
        self.assertEqual([p['y_mm'] for p in layout], [0, 500])
        self.assertTrue(all(p['basis'] == 'adjacent_source_bays_y' for p in layout))

    def test_connected_arc_and_lines_form_eye_outline(self):
        arc = [[math.cos(t)*10, math.sin(t)*10] for t in
               [math.pi*i/32 for i in range(33)]]
        paths = [arc, [[-10, 0], [-10, -4]], [[-10, -4], [10, -4]], [[10, -4], [10, 0]]]
        loops = closed_loops(paths)
        self.assertEqual(len(loops), 1)
        self.assertEqual(bounds(loops[0]), [-10, -4, 10, 10])
        self.assertGreater(len(loops[0]), 33)

    def test_missing_segment_is_not_invented(self):
        paths = [[[0, 0], [10, 0]], [[10, 0], [10, 10]], [[10, 10], [0, 10]]]
        self.assertEqual(closed_loops(paths), [])


class SourceRegressions(unittest.TestCase):
    def test_repeated_front_inner_plate_eyes_become_two(self):
        model = preview('e79c778a6f433004-10D9925')
        eyes = model['assembly']['lifting_eyes']
        self.assertEqual(len(eyes), 2)
        self.assertEqual(sorted(e['x_mm'] for e in eyes), [-380, 380])
        for eye in eyes:
            self.assertFalse(eye['projection_conflict'])
            self.assertEqual(eye['thickness_mm'], 12)
            self.assertEqual(eye['stem_diameter_mm'], 12)
            self.assertTrue(eye['holes'])
            hole = bounds(eye['holes'][0])
            self.assertAlmostEqual(hole[2]-hole[0], 27, places=2)

    def test_four_top_eyes_not_two_front_or_eight_total(self):
        eyes = preview('9f5252c1bf56526c-F8DC')['assembly']['lifting_eyes']
        self.assertEqual(len(eyes), 4)
        self.assertEqual(len({(e['x_mm'], e['z_mm']) for e in eyes}), 4)
        self.assertTrue(all(e['basis'] == 'front_top_side_projection_match' for e in eyes))
        self.assertEqual(sorted({e['x_mm'] for e in eyes}), [-525, 525])
        self.assertTrue(all(e['projection_delta_mm'] < .01 for e in eyes))

    def test_two_bay_source_and_projection_conflict_are_explicit(self):
        model = preview('142a10f4b2c12273-1120763')
        assembly = model['assembly']
        self.assertEqual(assembly['compartments']['count'], 2)
        self.assertEqual([p['width_mm'] for p in assembly['compartments']['slots']], [900, 900])
        self.assertTrue(assembly['compartments']['partition_depth_from_top_views'])
        self.assertEqual(len(assembly['lifting_eyes']), 4)
        self.assertIn('lifting_eye_projection_conflict', assembly['review_issues'])
        self.assertIn('front_outline_missing', model['warnings'])

    def test_wall_tabs_not_repeated_for_every_projection(self):
        assembly = preview('f68048edf3b28c83-1B3D3')['assembly']
        self.assertEqual(len(assembly['mounting_lugs']), 4)
        self.assertEqual(len(assembly['lifting_eyes']), 0)
        self.assertTrue(all(lug['holes'] for lug in assembly['mounting_lugs']))

    def test_inset_outer_leaf_frame_is_not_an_extra_leaf_or_bay(self):
        model = preview('f68048edf3b28c83-1B3D3')
        assembly = model['assembly']
        detail = assembly['door_perimeter_details'][0]
        self.assertEqual(detail['side'], 'inner')
        self.assertFalse(detail['section_verified'])
        self.assertEqual(assembly['compartments']['count'], 1)
        outer = [p for p in assembly['panel_layout'] if p['kind'] == 'outer_door' and p['physical']]
        self.assertEqual(len(outer), 1)
        self.assertEqual(outer[0]['face_id'], detail['owner_face_id'])

    def test_alternate_equipment_view_is_not_second_compartment(self):
        assembly = preview('142a10f4b2c12273-108CDD4')['assembly']
        self.assertEqual(assembly['compartments']['count'], 1)
        self.assertEqual(sum(p['physical'] for p in assembly['panel_layout']
                             if p['kind'] == 'mounting_plate'), 1)
        self.assertEqual(assembly['base']['height_mm'], 100)


if __name__ == '__main__':
    unittest.main()
