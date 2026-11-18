import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock

from PIL import Image
from app.services.ai.regional_takeoff import extract_regions, map_box, deduplicate_parts
from app.services.ai.motor_starter_context import enrich_motor_starters


class RegionalTests(unittest.IsolatedAsyncioTestCase):
    def test_inverse_quarter_turn_and_crop_mapping(self):
        self.assertEqual(map_box([100, 200, 300, 400], [200, 400, 800, 1000]), [260, 520, 380, 640])
        self.assertEqual(map_box([100, 200, 300, 400], [0, 0, 1000, 1000], 90), [600, 100, 800, 300])
        original = [100, 200, 300, 400]
        for angle in (90, 180, 270):
            rotated = map_box(original, [0, 0, 1000, 1000], angle)
            self.assertEqual(map_box(rotated, [0, 0, 1000, 1000], 360-angle), original)

    async def test_quantity_recovery_preserves_notes_and_maps_ids(self):
        scan = {'regions': [{'box_2d': [500, 0, 1000, 1000]}], 'inventory': [{'name': 'PSU', 'quantity': 6}]}
        first = {'devices': [{'name': 'PSU', 'quantity': 1}, {'name': 'BMS', 'record_kind': 'external_interface'}, {'name': 'Vỏ tủ điện', 'category': 'ENCLOSURE'}],
                 'boxes': [{'device_id': '0', 'symbol_box_2d': [100, 100, 200, 200]}]}
        corrected = {'devices': [{'name': 'PSU', 'quantity': 6}, {'name': 'BMS', 'record_kind': 'external_interface'}, {'name': 'Vỏ tủ điện', 'category': 'ENCLOSURE'}],
                     'boxes': [{'device_id': '0', 'symbol_box_2d': [100, 100, 200, 200]}]}
        call = AsyncMock(side_effect=[json.dumps(v) for v in (scan, first,
            {'issues': [{'region_id': '0', 'reason': '6 PSU symbols, not 1'}]}, corrected, {'issues': []})])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'source.png'
            Image.new('RGB', (1000, 1000), 'white').save(path)
            result = await extract_regions(path, 'Read', call)
        self.assertEqual(len(result['devices']), 1)
        self.assertEqual(result['devices'][0]['quantity'], 6)
        self.assertEqual(result['boxes'][0]['symbol_box_2d'], [543, 100, 594, 200])
        obs = result['devices'][0]['source_observations']
        self.assertEqual(obs['coverage_review']['status'], 'passed')
        self.assertEqual(obs['panel_notes'][0]['name'], 'BMS')
        self.assertEqual(call.await_count, 5)

    async def test_failed_repair_retains_read_rows_and_unresolved_state(self):
        call = AsyncMock(side_effect=[json.dumps(v) for v in (
            {'regions': []}, {'devices': [{'name': 'DOL', 'quantity': 1}]},
            {'issues': [{'region_id': '0', 'reason': 'Missing timer'}]}, {},
            {'issues': [{'region_id': '0', 'reason': 'Still missing timer'}]})])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'source.png'; Image.new('RGB', (100, 100)).save(path)
            result = await extract_regions(path, 'Read', call)
        self.assertEqual(result['devices'][0]['name'], 'DOL')
        self.assertEqual(result['devices'][0]['source_observations']['coverage_review']['status'], 'needs_review')

    def test_dol_per_branch_never_sizes_overload_from_breaker(self):
        scope = {'source_file_id': 1, 'source_page': 1, 'panel_code': 'MDB'}
        devices = [{**scope, 'category': 'MCB', 'name': 'MCB', 'tag': 'Q1', 'spec': 'MCB3P25A6kA', 'in_a': 25},
                   {**scope, 'category': 'MCB', 'name': 'MCB', 'tag': 'Q2', 'spec': 'MCB3P20A6kA', 'in_a': 20},
                   {**scope, 'name': 'DOL', 'upstream_device': 'Q1', 'connected_load': 'Quạt hút'},
                   {**scope, 'name': 'Khởi động trực tiếp', 'upstream_device': 'Q2', 'connected_load': 'Quạt gió tươi'}]
        enrich_motor_starters(devices)
        first, second = [d['source_observations']['motor_starter'] for d in devices[2:]]
        self.assertEqual(first['upstream']['in_a'], 25)
        self.assertEqual(second['upstream']['in_a'], 20)
        self.assertEqual(len(first['missing_inputs']), 4)
        self.assertTrue(all(c['spec'] is None and c['included_in_total'] is False for c in first['components']))
        self.assertNotIn('MCB', [c['category'] for c in first['components']])
        devices[2]['upstream_device'] = 'missing'
        enrich_motor_starters(devices)
        self.assertIsNone(devices[2]['source_observations']['motor_starter']['upstream'])
        devices[2].pop('upstream_device')
        devices[0]['connected_load'] = 'Quạt hút'
        enrich_motor_starters(devices)
        self.assertEqual(devices[2]['source_observations']['motor_starter']['upstream_status'], 'candidate')
        devices[2]['evidence_region'] = devices[0]['evidence_region'] = {'load_verified': True}
        enrich_motor_starters(devices)
        self.assertEqual(devices[2]['source_observations']['motor_starter']['upstream_status'], 'verified')

    def test_dor_is_not_a_global_alias_and_explicit_motor_input_survives(self):
        devices = [{'name': 'DOR', 'spec': ''}, {'name': 'DOL', 'source_observations': {'circuit': {'motor_rated_current_a': 12}}}]
        enrich_motor_starters(devices)
        self.assertNotIn('source_observations', devices[0])
        self.assertEqual(len(devices[1]['source_observations']['motor_starter']['missing_inputs']), 3)

    def test_overlapping_regions_do_not_merge_repeated_tags_at_distinct_positions(self):
        row = {'category': 'MCB', 'name': 'MCB', 'tag': 'L4', 'spec': '20A', 'quantity': 1}
        parts = [{'devices': [dict(row)], 'boxes': [{'device_id': '0', 'symbol_box_2d': [100, 100, 200, 200]}]},
                 {'devices': [{**row, 'name': 'Aptomat tép', 'category': 'Aptomat tép', 'spec': 'MCB 20A'}, dict(row)], 'boxes': [
                     {'device_id': '0', 'symbol_box_2d': [101, 101, 201, 201]},
                     {'device_id': '1', 'symbol_box_2d': [100, 300, 200, 400]}]}]
        deduplicate_parts(parts)
        self.assertEqual([len(p['devices']) for p in parts], [1, 1])
        self.assertEqual(parts[1]['boxes'][0]['device_id'], '0')
        self.assertEqual(parts[1]['boxes'][0]['symbol_box_2d'], [100, 300, 200, 400])

    async def test_shared_header_requires_independent_relationship_confirmation(self):
        from app.services.ai.device_crop_audit import audit_device_previews
        from app.services.ai.evidence_crops import apply_verified_boxes
        from app.schemas.ai import ExtractedDeviceSchema
        d = ExtractedDeviceSchema(name='MCB', category='MCB', spec='1P20A')
        proposal = {'device_id': '0', 'verified': True, 'symbol_verified': True,
                    'symbol_box_2d': [100, 600, 200, 700], 'text_box_2d': [100, 100, 200, 200],
                    'shared_label': True, 'relationship_evidence': 'Header applies along shared rail'}
        for confirmed in (False, True):
            call = AsyncMock(return_value=json.dumps({'checks': [{'device_id': '0', 'matches': True,
                'symbol_complete': True, 'label_complete': True, 'isolated': True,
                'shared_label_matches': confirmed, 'reason': 'Shared header relation'}]}))
            checked = await audit_device_previews(Image.new('RGB', (1000, 1000), 'white'), call, [d], {'boxes': [proposal]})
            apply_verified_boxes([d], checked, require_symbols=True)
            self.assertEqual(d.evidence_region['status'], 'verified' if confirmed else 'unverified')
            if not confirmed:
                self.assertEqual(d.evidence_region['candidate_region']['symbol_box_2d'], proposal['symbol_box_2d'])
                self.assertIsNone(d.box_2d)

    def test_true_quantity_error_blocks_but_group_representation_does_not(self):
        from app.services.ai.takeoff_verifier import engineering_review
        self.assertFalse(engineering_review({'issues': [{'code': 'wrong_quantity', 'detail': 'Six PSU symbols, not one'}]})['passed'])
        self.assertTrue(engineering_review({'issues': [{'code': 'quantity_representation'}]})['passed'])

    async def test_omitted_shared_header_flag_cannot_bypass_relationship_audit(self):
        from app.services.ai.device_crop_audit import audit_device_previews
        from app.schemas.ai import ExtractedDeviceSchema
        devices = [ExtractedDeviceSchema(name='RCBO', category='RCBO', spec='2P20A') for _ in range(2)]
        boxes = [{'device_id': str(i), 'verified': True, 'symbol_verified': True,
                  'symbol_box_2d': [100, 400+i*100, 200, 450+i*100],
                  'text_box_2d': [100, 100, 200, 200], 'relationship_evidence': 'Same header group'} for i in range(2)]
        call = AsyncMock(return_value=json.dumps({'checks': [{'device_id': str(i), 'matches': True,
            'symbol_complete': True, 'label_complete': True, 'isolated': True} for i in range(2)]}))
        result = await audit_device_previews(Image.new('RGB', (1000, 1000), 'white'), call, devices, {'boxes': boxes})
        self.assertTrue(all(b['shared_label'] for b in result['boxes']))
        self.assertTrue(all(b['verified'] is False for b in result['boxes']))

    def test_quotation_keeps_dol_as_one_set_and_does_not_price_unknown_quantity(self):
        from app.services.ai.procurement_review import build_quotation_rows
        rows = build_quotation_rows([
            {'category': 'DOL', 'name': 'DOL', 'spec': '', 'unit': 'Bộ', 'quantity': 1, 'panel_code': 'MDB'},
            {'category': 'CT', 'name': 'CT', 'spec': '', 'quantity': 1, 'unit': 'Cụm', 'panel_code': 'MDB',
             'quantity_review': {'status': 'needs_review', 'blocking': True}}], [], refresh_prices=False)
        dol = next(r for r in rows if r.get('category') == 'DOL')
        self.assertEqual((dol['quantity'], dol['unit']), (1, 'Bộ'))
        self.assertEqual(dol['source_observations']['motor_starter']['pricing_basis'], 'assembly_only')
        self.assertFalse(any(r.get('category') in {'CONTACTOR', 'OVERLOAD_PROTECTION'} for r in rows))
        ct = next(r for r in rows if r.get('category') == 'CT')
        self.assertIsNone(ct['quantity'])
        self.assertIsNone(ct['line_total'])


if __name__ == '__main__':
    unittest.main()
