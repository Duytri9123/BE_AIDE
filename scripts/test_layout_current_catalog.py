"""Exercise real CatalogTB geometry with mixed breaker sizes and missing data."""
import tempfile
import unittest
from pathlib import Path
import ezdxf
from app.services.cad.catalogtb_assets import candidates
from app.services.cad.reference_panel_layout import generate


class CurrentCatalogLayoutTests(unittest.TestCase):
    def devices(self):
        main = candidates('MCCB', 'LS', 3)[0]
        rows = [dict(category='MCCB', tag='Q0', name='MCCB', quantity=1,
                     cad=dict(asset_id=main['id'], branch_arrangement='two_vertical_banks',
                              distribution_method='fabricated_fishbone'))]
        for i, (poles, amps) in enumerate([(2, 32), (3, 20), (3, 30), (2, 10)]):
            asset = candidates('MCB', 'LS', poles)[0]
            rows.append(dict(category='MCB', tag=f'L{i + 1}', name='MCB', quantity=1,
                             poles=poles, in_a=amps, cad={'asset_id': asset['id']}))
        return rows

    def test_real_geometry_rotates_and_large_breakers_are_above_small(self):
        with tempfile.TemporaryDirectory() as directory:
            result = generate(self.devices(), (1000, 600, 300), directory)
            self.assertTrue(Path(result['dxf']).is_file())
            self.assertFalse(ezdxf.readfile(result['dxf']).audit().has_errors)
            self.assertIsNotNone(result['enclosure_source'])
            self.assertEqual(result['enclosure_source']['scale'], 1)
            doc = ezdxf.readfile(result['dxf'])
            self.assertEqual(len([e for e in doc.modelspace().query('INSERT')
                                  if e.dxf.name.startswith('CABINET_SOURCE_')]), 1)
            self.assertTrue(result['enclosure_source']['complete_source_sheet'])
            self.assertIn('side', result['enclosure_source']['faces'])
            source_block = next(b for b in doc.blocks if b.name.startswith('CABINET_SOURCE_'))
            self.assertEqual(len(source_block), result['enclosure_source']['source_entity_count'])
            labels = [e.dxf.text for e in doc.modelspace().query('TEXT')]
            self.assertFalse(any('CHUA' in text or 'SO DO PHAN PHA' in text for text in labels))
            self.assertFalse(any(text.startswith(('L1 ', 'L2 ', 'L3 ', 'L4 ')) for text in labels))
            branches = [p for p in result['placements'] if p['tag'].startswith('L')]
            self.assertEqual(len(branches), 4)
            self.assertTrue(all(p['rotation'] in (90, 270) and p['scale'] == 1 for p in branches))
            large = [p for p in branches if p['tag'] in ('L2', 'L3')]
            small = [p for p in branches if p['tag'] in ('L1', 'L4')]
            self.assertGreater(min(p['y'] for p in large), max(p['y'] for p in small))
            self.assertFalse(result['release_ready'])
            self.assertTrue(result['completion_checks']['neutral_bar_placed'])
            main = next(p for p in result['placements'] if p['tag'] == 'Q0')
            neutral = next(p for p in result['placements'] if p['tag'] == 'N')
            self.assertLessEqual(neutral['y']+neutral['h'],main['y']-30)
            self.assertEqual(neutral['y'], 165)
            self.assertEqual(result['spacing_review']['spine_pitch_mm'], 30)
            self.assertEqual(result['spacing_review']['clearance_compliance'], 'unverified')
            self.assertTrue(doc.modelspace().query('LINE[layer=="PLAN_N"]'))
            self.assertIsNone(neutral['asset_id'])

    def test_neutral_routes_do_not_use_three_pole_breaker(self):
        devices=self.devices()
        devices[1]['tag']='L1/R'
        with tempfile.TemporaryDirectory() as directory:
            result=generate(devices,(1000,600,300),directory)
            import json
            distribution=json.loads((Path(directory)/'Phuong_an_phan_phoi_nguon.json').read_text(encoding='utf8'))
            neutral={r['tag'] for r in distribution['routing_preview'] if r['phase']=='N'}
            self.assertEqual(neutral, {'L1/R','L4'})
            self.assertFalse(result['completion_checks']['terminals_verified'])

    def test_door_face_mapping_uses_source_json_and_explicit_override(self):
        devices=self.devices()
        light=candidates('LIGHT')[0]
        devices.append(dict(category='LIGHT',tag='R',name='Lamp',quantity=1,cad={'asset_id':light['id']}))
        with tempfile.TemporaryDirectory() as directory:
            result=generate(devices,(1000,600,300),directory)
            lamp=next(p for p in result['placements'] if p['tag']=='R')
            self.assertEqual(lamp['source_face_label'],'1st DOOR VIEW')
            self.assertEqual(lamp['mounting_face'],'outer_door')
            self.assertGreater(lamp['x'],900)
            self.assertEqual(result['enclosure_source']['side_view_review']['status'],'source_only_depth_not_verified')
            devices[-1]['cad']['mounting_face']='inner_door'
            result=generate(devices,(1000,600,300),directory)
            lamp=next(p for p in result['placements'] if p['tag']=='R')
            self.assertEqual(lamp['source_face_label'],'2nd DOOR VIEW')
            self.assertLess(lamp['x'],600)

    def test_stale_asset_does_not_silently_become_a_different_product(self):
        devices = self.devices()
        devices[1]['cad']['asset_id'] = 'tb:deleted-source'
        with tempfile.TemporaryDirectory() as directory, self.assertRaises(ValueError):
            generate(devices, (1000, 600, 300), directory)

    def test_other_panel_does_not_reuse_tdt_layout(self):
        with tempfile.TemporaryDirectory() as directory, self.assertRaises(ValueError):
            generate(self.devices(), (350, 450, 150), directory, panel_code='TĐ-BTA')


if __name__ == '__main__':
    unittest.main()
