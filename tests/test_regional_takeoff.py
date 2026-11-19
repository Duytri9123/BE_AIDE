import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from PIL import Image
from app.services.ai.regional_takeoff import extract_regions, map_box, deduplicate_parts
from app.services.ai.motor_starter_context import enrich_motor_starters


async def keep_disputes(image, regions, parts, issues, call_image, **kwargs):
    return issues, []


class RegionalTests(unittest.IsolatedAsyncioTestCase):
    async def test_provider_outage_keeps_read_regions_and_skips_further_ai_calls(self):
        from app.core.exceptions import AITimeoutError
        call=AsyncMock(side_effect=[json.dumps({'regions':[
            {'box_2d':[0,0,500,1000]}, {'box_2d':[500,0,1000,1000]}]}),
            json.dumps({'devices':[{'name':'MCB','quantity':1}]}),AITimeoutError('provider timeout')])
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'source.png';Image.new('RGB',(1000,1000)).save(path)
            result=await extract_regions(path,'Read',call,concurrency=2)
        self.assertEqual(call.await_count,3)
        self.assertTrue(result['processing_interrupted'])
        self.assertEqual(len(result['devices']),1)
        review=result['devices'][0]['source_observations']['coverage_review']
        self.assertEqual(review['status'],'needs_review')
        self.assertTrue(review['read_failed'])
        self.assertIn('Máy chủ AI',review['issues'][0]['reason'])

    async def test_provider_outage_during_review_preserves_inventory_without_retry(self):
        from app.core.exceptions import AIVisionError
        call=AsyncMock(side_effect=[json.dumps({'regions':[]}),
            json.dumps({'devices':[{'name':'MCB','quantity':1}]}),AIVisionError('provider disconnected')])
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'source.png';Image.new('RGB',(1000,1000)).save(path)
            result=await extract_regions(path,'Read',call)
        self.assertEqual(call.await_count,3)
        self.assertTrue(result['processing_interrupted'])
        self.assertEqual(result['devices'][0]['source_observations']['coverage_review']['status'],'needs_review')

    def test_overlap_read_without_tag_is_merged_only_at_same_source_geometry(self):
        parts=[{'devices':[{'name':'Contactor','category':'CONTACTOR','spec':'2P16A','tag':'P1','quantity':1}],
                'boxes':[{'device_id':'0','symbol_box_2d':[100,100,150,140]}]},
               {'devices':[{'name':'Khởi động từ','category':'Điều khiển','spec':'2P16A','tag':None,'quantity':1},
                           {'name':'Contactor','category':'CONTACTOR','spec':'2P16A','quantity':1}],
                'boxes':[{'device_id':'0','symbol_box_2d':[101,100,151,140]},
                         {'device_id':'1','symbol_box_2d':[200,100,250,140]}]}]
        deduplicate_parts(parts)
        self.assertEqual(sum(len(p['devices']) for p in parts),2)
        self.assertEqual(parts[1]['boxes'][0]['symbol_box_2d'],[200,100,250,140])

    def test_coverage_retains_source_claims_without_repeated_images_or_diagnostics(self):
        from app.services.ai.regional_takeoff import coverage_claim
        row={'name':'MCB','tag':'P1','spec':'16A','quantity':1,'connected_load':'Bơm',
             'evidence_image':'data:image/png;base64,large','technical_analysis':'repeated explanation',
             'source_observations':{'panel_notes':['repeated note']*100,'circuit':{'power_w':100},
                 'source_checks':[{'field':'quantity','value':1,'observed_text':'1 cái',
                     'verification_status':'verified','evidence_image':'large','reason':'diagnostic'}]}}
        result=coverage_claim(row)
        for key in ('name','tag','spec','quantity','connected_load'):self.assertEqual(result[key],row[key])
        self.assertEqual(result['source_observations']['source_checks'][0]['observed_text'],'1 cái')
        self.assertNotIn('base64',json.dumps(result))
        self.assertNotIn('panel_notes',json.dumps(result))
        self.assertNotIn('technical_analysis',result)

    async def test_overlapping_table_bands_read_full_symbol_but_count_it_once(self):
        import numpy as np
        scan={'layout_kind':'horizontal_circuit_table','regions':[
            {'box_2d':[0,0,500,500]},{'box_2d':[500,0,1000,500]},
            {'box_2d':[0,500,500,1000]}]}
        reads=[]
        async def call(path,prompt):
            if 'Nhận diện vùng trước' in prompt:return json.dumps(scan)
            if 'Kiểm kê ĐỘC LẬP' in prompt:return json.dumps({'issues':[]})
            with Image.open(path) as crop:
                ink=np.asarray(crop)[:,:,0]<100
                ys,xs=np.where(ink)
                if not len(xs):return json.dumps({'devices':[]})
                reads.append((int(ys.max()-ys.min()+1),crop.height))
                box=[int(ys.min()/crop.height*1000),int(xs.min()/crop.width*1000),
                     round((ys.max()+1)/crop.height*1000),round((xs.max()+1)/crop.width*1000)]
            return json.dumps({'devices':[{'name':'MCB','tag':'P1','category':'MCB','spec':'16A','quantity':1}],
                'boxes':[{'device_id':'0','symbol_box_2d':box,'text_box_2d':box}]})
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'source.png';image=Image.new('RGB',(1000,1000),'white')
            image.paste('black',(200,225,220,235));image.save(path)
            result=await extract_regions(path,'Read',call,concurrency=6)
        self.assertGreaterEqual(len(reads),2)
        self.assertTrue(all(height==10 for height,_ in reads))
        self.assertEqual(len(result['devices']),1)
        self.assertEqual(result['devices'][0]['tag'],'P1')

    async def test_dense_table_columns_become_bounded_horizontal_bands(self):
        scan={'layout_kind':'horizontal_circuit_table','regions':[
            {'box_2d':box} for box in ([50,40,350,400],[360,200,650,430],[650,220,950,430],[100,520,370,998])],
            'inventory':[{'quantity':37}]}
        sizes=[]
        async def call(path,prompt):
            with Image.open(path) as source:sizes.append(source.size)
            return json.dumps(scan if len(sizes)==1 else {'issues':[]} if 'Kiểm kê ĐỘC LẬP' in prompt else {'devices':[]})
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'source.png';Image.new('RGB',(1000,1000)).save(path)
            await extract_regions(path,'Read',call,concurrency=6)
        self.assertEqual(len(sizes),8)  # Scan, six bounded bands, independent coverage.
        self.assertTrue(all(w==1000 and h<=270 for w,h in sizes[1:-1]))
        self.assertGreaterEqual(sum(h for _,h in sizes[1:-1]),1000)

    async def test_rotated_table_keeps_source_rows_along_the_rotated_axis(self):
        sizes=[]
        async def call(path,prompt):
            with Image.open(path) as source:sizes.append(source.size)
            return json.dumps({'layout_kind':'horizontal_circuit_table','regions':[
                {'box_2d':[100,200,500,300],'rotation_degrees':90}]} if len(sizes)==1
                else {'issues':[]} if 'Kiểm kê ĐỘC LẬP' in prompt else {'devices':[]})
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'source.png';Image.new('RGB',(1000,1000)).save(path)
            await extract_regions(path,'Read',call)
        self.assertEqual(sizes[1],(1000,116))

    async def test_native_schedule_partition_skips_model_discovery_and_keeps_whole_canvas(self):
        labels=[];rows=[]
        for i,y in enumerate(range(800,0,-100)):
            labels.extend([{'id':f't{i}','text':f'L{i}','x':500,'y':y,'height':10},
                           {'id':f'r{i}','text':'MCB-1P-10A-6kA','x':200,'y':y,'height':10}])
            rows.append({'id':f't{i}','rating_id':f'r{i}','tag':f'L{i}','rating':'MCB-1P-10A-6kA'})
        native={'view_bounds':[0,0,1000,1000],'labels':labels,'rows':rows}
        captured=[]
        async def call(path,prompt):
            with Image.open(path) as source:captured.append(source.size)
            return json.dumps({'issues':[]} if 'Kiểm kê ĐỘC LẬP' in prompt else {'devices':[]})
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'source.png';Image.new('RGB',(1000,1000)).save(path)
            await extract_regions(path,'Read',call,preserve_row_context=True,native_evidence=native)
        self.assertEqual(len(captured),3)  # Two source bands plus independent coverage.
        self.assertEqual(captured[-1],(1000,1000))
        self.assertEqual(captured[0][0],1000)
        self.assertGreaterEqual(captured[0][1]+captured[1][1],1000)

    async def test_circuit_table_regions_keep_tag_and_load_columns_in_source_frame(self):
        calls = []
        async def call(path, prompt):
            with Image.open(path) as source:
                calls.append(source.size)
            return json.dumps(({'layout_kind':'horizontal_circuit_table','regions':[{'box_2d':[200,150,400,330]}]},
                {'devices':[{'name':'MCB','tag':'L1'}], 'boxes':[
                    {'device_id':'0','symbol_box_2d':[100,200,200,300]}]},
                {'issues':[]})[len(calls)-1])
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'source.png'
            Image.new('RGB',(1000,1000),'white').save(path)
            result=await extract_regions(path,'Read',call)
        self.assertEqual(calls[1],(1000,1000))
        self.assertEqual(result['boxes'][0]['symbol_box_2d'],[100,200,200,300])

    def test_explicit_source_type_survives_a_vietnamese_breaker_category(self):
        from app.services.ai.scoped_takeoff import normalize_scoped_row
        row = normalize_scoped_row({'category': 'Aptomat chống dòng rò', 'name': 'Aptomat',
                                   'spec': '2P 20A 6kA', 'observed_text': 'RCBO 2P 20A 6KA'})
        self.assertEqual(row['category'], 'RCBO')

    async def test_dol_assembly_is_retained_when_provider_calls_it_a_functional_block(self):
        call = AsyncMock(side_effect=[json.dumps(v) for v in (
            {'regions': []}, {'devices': [{'name': 'DOL', 'spec': 'DOL', 'observed_text': 'DOL',
                'record_kind': 'functional_block', 'quantity': 1}]}, {'issues': []})])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'source.png'; Image.new('RGB', (100, 100)).save(path)
            result = await extract_regions(path, 'Read', call)
        self.assertEqual(result['devices'][0]['record_kind'], 'assembly')
        self.assertEqual(result['devices'][0]['quantity'], 1)

    def test_inverse_quarter_turn_and_crop_mapping(self):
        self.assertEqual(map_box([100, 200, 300, 400], [200, 400, 800, 1000]), [260, 520, 380, 640])
        self.assertEqual(map_box([100, 200, 300, 400], [0, 0, 1000, 1000], 90), [600, 100, 800, 300])
        original = [100, 200, 300, 400]
        for angle in (90, 180, 270):
            rotated = map_box(original, [0, 0, 1000, 1000], angle)
            self.assertEqual(map_box(rotated, [0, 0, 1000, 1000], 360-angle), original)

    @patch('app.services.ai.source_issue_review.adjudicate_issues', new=keep_disputes)
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

    @patch('app.services.ai.source_issue_review.adjudicate_issues', new=keep_disputes)
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
