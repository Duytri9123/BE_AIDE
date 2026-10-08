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
            self.assertEqual(neutral['h'], main['h'] + 40)
            self.assertEqual(neutral['y'], main['y'] - 20)
            self.assertGreater(neutral['x'], main['x'] + main['w'])
            self.assertIsNone(neutral['asset_id'])

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
