import base64
import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import ezdxf
from PIL import Image
from app.services.ai.scoped_takeoff import extract_confirmed_panels, render_panel
from app.services.ingestion.cad_source_evidence import cad_evidence, region_normalized
from app.services.ai.takeoff_verifier import engineering_review


class ScopedTakeoffTests(unittest.IsolatedAsyncioTestCase):
    def test_literal_fuse_group_phase_marking_and_timer_alias(self):
        from app.services.ai.scoped_takeoff import normalize_scoped_row
        fuse = normalize_scoped_row({'category': 'FUSE', 'name': 'Cầu chì', 'quantity': 1, 'unit': 'Bộ',
                                     'spec': '3x2A', 'observed_text': '3x2A'})
        self.assertEqual((fuse['quantity'], fuse['unit'], fuse['spec']), (3, 'Cái', '3x2A'))
        light = normalize_scoped_row({'category': 'LIGHT', 'name': 'Đèn báo pha', 'spec': 'R', 'observed_text': 'R'})
        self.assertEqual(light['spec'], '')
        self.assertEqual(light['source_observations']['symbol_marking'], 'R')
        self.assertEqual(normalize_scoped_row({'category': 'RO LE THOI GIAN', 'spec': '24H'})['category'], 'TIMER')

    def test_preserves_a_printed_branch_code_reported_as_location(self):
        from app.services.ai.scoped_takeoff import ground_scoped_identity
        row = {'name': 'MCB', 'category': 'MCB', 'location': 'Nhánh P7', 'connected_load': 'BƠM PHUN SƯƠNG 07'}
        self.assertEqual(ground_scoped_identity(row, [])['tag'], 'P7')
        self.assertEqual(ground_scoped_identity({**row, 'location': 'P7'}, [])['tag'], 'P7')
        self.assertIsNone(ground_scoped_identity({**row, 'location': 'Nhánh 7'}, []).get('tag'))

    def test_contactor_ratings_are_populated_from_the_printed_contactor_label(self):
        from app.services.ai.scoped_takeoff import normalize_scoped_row
        row = normalize_scoped_row({'name': 'Contactor', 'category': 'CONTACTOR', 'spec': '2P-16A',
                                    'observed_text': '2P-16A C'})
        self.assertEqual((row['poles'], row['in_a']), (2, 16))
        self.assertIsNone(row.get('icu_ka'))

    def test_missing_breaker_numbers_are_read_from_the_literal_source_quote(self):
        from app.services.ai.scoped_takeoff import normalize_scoped_row
        row = {'category': 'MCB', 'observed_text': 'MCB-1P\n16A-10kA', 'spec': '16A-10kA'}
        result = normalize_scoped_row(row)
        self.assertEqual((result['poles'], result['in_a'], result['icu_ka']), (1, 16, 10))
        conflicting = normalize_scoped_row({**row, 'spec': '20A-6kA'})
        self.assertIsNone(conflicting.get('in_a'))
        self.assertIsNone(conflicting.get('icu_ka'))

    def test_literal_24h_control_block_has_a_canonical_timer_type(self):
        from app.services.ai.scoped_takeoff import normalize_scoped_row
        row=normalize_scoped_row({'name':'24H','category':'Bộ điều khiển thời gian','spec':'24H'})
        self.assertEqual(row['category'],'TIMER');self.assertEqual(row['spec'],'24H')
        timer = normalize_scoped_row({'name': 'Timer', 'observed_text': '24H', 'spec': ''})
        self.assertEqual(timer['spec'], '24H')
        unknown = normalize_scoped_row({'name': 'Timer 24H', 'spec': 'Chưa xác định'})
        self.assertEqual(unknown['spec'], '')

    def test_unknown_cluster_count_does_not_confirm_an_inferred_physical_quantity(self):
        from app.services.ai.scoped_takeoff import normalize_scoped_row
        row={'name':'Biến dòng','category':'CT','quantity':3,'drawing_quantity':1,'unit':'Cụm',
             'observed_text':'Ký hiệu CT đo 3 pha','source_observations':'Chưa ghi tỷ số'}
        result=normalize_scoped_row(row)
        self.assertEqual((result['quantity'],result['unit']),(1,'Cụm'))
        self.assertTrue(result['quantity_review']['blocking'])
        self.assertEqual(result['source_observations']['unverified_physical_quantity'],3)
        self.assertEqual(normalize_scoped_row({**row,'observed_text':'3xTI 80/5A'})['quantity'],3)

    def test_auxiliary_types_are_canonical_before_native_load_grounding(self):
        from app.services.ai.scoped_takeoff import normalize_scoped_row,ground_scoped_identity
        for category,name,kind in [('CURRENT_TRANSFORMER','Biến dòng','CT'),
                ('INDICATOR_LIGHT','Đèn báo pha','LIGHT'),('Thiết bị điều khiển','Khởi động từ','CONTACTOR')]:
            row=normalize_scoped_row({'category':category,'name':name,'connected_load':'Nguồn pha R,Y,B'})
            self.assertEqual(row['category'],kind)
            if kind in {'CT','LIGHT'}:
                self.assertIsNone(ground_scoped_identity(row,[{'text':'80/5A'}])['connected_load'])

    def test_native_tag_must_occur_in_source_before_the_whole_image_review(self):
        from app.services.ai.scoped_takeoff import ground_scoped_identity
        labels=[{'text':'L14. Chiếu sáng'},{'text':'MCB-1P 16A-6kA'},{'text':'L1. Logo'}]
        self.assertEqual(ground_scoped_identity({'tag':'L1'},labels)['tag'],'L1')
        self.assertEqual(ground_scoped_identity({'tag':'L14'},labels)['tag'],'L14')
        self.assertIsNone(ground_scoped_identity({'tag':'L4'},labels)['tag'])
        row=ground_scoped_identity({'tag':'VS'},labels)
        self.assertIsNone(row['tag']);self.assertEqual(row['source_observations']['unverified_tag']['value'],'VS')
        self.assertEqual(ground_scoped_identity({'tag':'VS'},labels+[{'text':'VS'}])['tag'],'VS')

    def test_type_and_pole_designations_are_not_branch_tags_or_named_loads(self):
        from app.services.ai.scoped_takeoff import ground_scoped_identity
        for tag in ('MCB-1P','MCB 2P','RCBO-1P+N','C'):
            row=ground_scoped_identity({'tag':tag,'connected_load':'Điều khiển các lộ bơm'},[])
            self.assertIsNone(row['tag']);self.assertIsNone(row['connected_load'])
            self.assertEqual(row['source_observations']['function_in_load'],'Điều khiển các lộ bơm')
        for tag in ('MCB-1','P6','MDK'):
            self.assertEqual(ground_scoped_identity({'tag':tag},[])['tag'],tag)

    def test_nested_source_load_claim_is_preserved_before_independent_review(self):
        from app.services.ai.scoped_takeoff import normalize_scoped_row
        row={'name':'MCB','source_observations':{'connected_load':'VAN ĐIỆN TỪ 02'}}
        self.assertEqual(normalize_scoped_row(row)['connected_load'],'VAN ĐIỆN TỪ 02')
        self.assertEqual(normalize_scoped_row({**row,'connected_load':'Bơm 01'})['connected_load'],'Bơm 01')
        self.assertNotIn('verified',normalize_scoped_row(row))

    def test_final_crop_relocation_does_not_count_one_verified_spare_twice(self):
        from app.services.ai.scoped_takeoff import deduplicate_checked_rows
        row={'name':'MCB','category':'MCB','spec':'1P 16A 10kA','quantity':1,
             'observed_text':'MCB-1P 16A-10kA','connected_load':None}
        original=[dict(row) for _ in range(3)]
        boxes=[{'device_id':str(i),'verified':True,'symbol_box_2d':box} for i,box in enumerate(
            ([794,130,814,166],[854,131,873,166],[803,131,818,177]))]
        remaining,devices,audited=deduplicate_checked_rows(original,['first','second','duplicate'],{'boxes':boxes})
        self.assertEqual(len(remaining),2)
        self.assertEqual(devices,['first','second'])
        self.assertEqual([b['device_id'] for b in audited['boxes']],['0','1'])
        boxes[2]['verified']=False
        self.assertEqual(len(deduplicate_checked_rows(original,[1,2,3],{'boxes':boxes})[0]),3)

    async def test_failed_inventory_coverage_defers_costly_device_crop_audit(self):
        with tempfile.TemporaryDirectory() as folder:
            image_path=Path(folder)/'source.png';Image.new('RGB',(100,100),'white').save(image_path)
            file=SimpleNamespace(id=7,filename='source.png',file_path=str(image_path))
            db=SimpleNamespace(execute=AsyncMock(return_value=SimpleNamespace(
                scalars=lambda:SimpleNamespace(all=lambda:[file]))))
            row={'name':'MCB','category':'MCB','spec':'16A','quantity':1,
                 'source_observations':{'coverage_review':{'status':'needs_review',
                    'issues':[{'reason':'Duplicated branch P1'}]}}}
            box={'device_id':'0','verified':True,'symbol_verified':True,
                 'symbol_box_2d':[100,100,200,200],'text_box_2d':[100,100,200,200]}
            payload={'devices':[row],'boxes':[box]}
            with patch('app.services.ai.scoped_takeoff.render_panel',AsyncMock(return_value=(str(image_path),''))), \
                 patch('app.services.ai.regional_takeoff.extract_regions',AsyncMock(return_value=payload)), \
                 patch('app.services.ai.scoped_takeoff.ConnectionPoolService.get_ordered_connections',AsyncMock(return_value=[object()])), \
                 patch('app.services.ai.device_crop_audit.audit_device_previews',AsyncMock()) as audit, \
                 patch('app.services.ai.takeoff_evidence_completion.complete_evidence',AsyncMock()) as repair:
                result=await extract_confirmed_panels(db,1,[{'source_file_id':7,'panel_code':'P1',
                    'source_page':None,'source_region':[0,0,1,1]}],'Bóc tách P1')
                payload['processing_interrupted']=True
                interrupted=await extract_confirmed_panels(db,1,[{'source_file_id':7,'panel_code':'P1',
                    'source_page':None,'source_region':[0,0,1,1]}],'Bóc tách P1')
                self.assertIn('Máy chủ AI',interrupted[0]['evidence_region']['reason'])
            audit.assert_not_awaited();repair.assert_not_awaited()
            self.assertEqual(len(result),1)
            self.assertEqual(result[0]['source_observations']['coverage_review']['status'],'needs_review')
            self.assertFalse(result[0]['evidence_image'])
            self.assertEqual(result[0]['evidence_region']['status'],'unverified')

    def test_unit_strings_do_not_reject_a_whole_panel(self):
        from app.services.ai.scoped_takeoff import normalize_scoped_row
        from app.schemas.ai import ExtractedDeviceSchema
        row = normalize_scoped_row({'category': 'Thiết bị đóng cắt', 'name': 'Aptomat',
            'observed_text': 'RCBO 2P 25A 6kA', 'spec': '2P25A6kA',
            'in_a': '25A', 'icu_ka': '6kA', 'poles': '2P'})
        device = ExtractedDeviceSchema.model_validate(row)
        self.assertEqual((device.category, device.in_a, device.icu_ka, device.poles), ('RCBO', 25, 6, 2))
        self.assertEqual(device.source_observations['raw_numeric_fields']['poles'], '2P')

    def test_text_source_observations_preserve_the_model_evidence(self):
        from app.services.ai.scoped_takeoff import normalize_scoped_row
        from app.schemas.ai import ExtractedDeviceSchema
        row = normalize_scoped_row({'category': 'MCB', 'name': 'MCB', 'spec': '10A',
            'source_observations': 'Nhãn L4 và đường nối đến tải chiếu sáng'})
        device = ExtractedDeviceSchema.model_validate(row)
        self.assertEqual(device.source_observations['description'], 'Nhãn L4 và đường nối đến tải chiếu sáng')

    def test_source_type_is_canonical_without_inventing_a_generic_breaker_type(self):
        from app.services.ai.scoped_takeoff import normalize_scoped_row
        self.assertEqual(normalize_scoped_row({'category': 'Aptomat', 'spec': 'MCB-1P-10A-6kA'})['category'], 'MCB')
        self.assertEqual(normalize_scoped_row({'category': 'Đồng hồ', 'spec': None})['category'], 'METER')
        self.assertEqual(normalize_scoped_row({'category': 'Aptomat', 'spec': ''})['category'], 'APTOMAT')

    def test_dense_crop_keeps_symbol_and_label_without_following_neighbour_wires(self):
        from app.services.ai.evidence_preview import device_preview
        image = Image.new('RGB', (1000, 1000), 'white')
        image.paste('black', (100, 100, 150, 150))
        image.paste('blue', (150, 100, 200, 150))
        image.paste('red', (205, 100, 250, 150))
        preview = device_preview(image, {'symbol_box_2d': [100, 100, 150, 150],
                                        'text_box_2d': [100, 150, 150, 200]}, tight=True)[0]
        crop = Image.open(io.BytesIO(base64.b64decode(preview['evidence_image'].split(',')[1])))
        pixels = list(crop.getdata())
        self.assertIn((0, 0, 0), pixels)
        self.assertIn((0, 0, 255), pixels)
        self.assertNotIn((255, 0, 0), pixels)

    def test_symbol_group_count_differences_are_not_reported_or_blocking(self):
        review = engineering_review({'issues': [
            {'code': 'quantity_representation', 'detail': 'One glyph, three phase lamps'},
            {'code': 'quantity_inference', 'detail': 'Engineering material count'}]})
        self.assertTrue(review['passed'])
        self.assertEqual(review['feedback'], '')
        self.assertFalse(engineering_review({'issues': [
            {'code': 'wrong_rating', 'detail': 'Label is 150A, candidate is 250A'}]})['passed'])

    async def test_real_dxf_render_excludes_unselected_panel_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'two-panels.dxf'
            doc = ezdxf.new()
            msp = doc.modelspace()
            msp.add_text('P1 MCB 20A', dxfattribs={'insert': (0, 0), 'height': 2})
            msp.add_circle((2, 6), 2)
            msp.add_text('P2 MCCB 250A', dxfattribs={'insert': (0, 200), 'height': 2})
            doc.saveas(path)
            evidence = cad_evidence(path)
            region = region_normalized(evidence['bounds'], [-10, -10, 40, 20])
            image, labels = await render_panel(SimpleNamespace(file_path=str(path)),
                {'source_region': region}, Path(tmp)/'unused.png')
            self.assertIn('P1 MCB 20A', labels)
            self.assertNotIn('P2 MCCB 250A', labels)
            with Image.open(image) as crop:
                self.assertGreater(crop.width, 100)

    async def test_extraction_audits_pixels_and_hides_rejected_crop(self):
        with tempfile.TemporaryDirectory() as tmp:
            image_path = Path(tmp)/'panel.png'
            image = Image.new('RGB', (1000, 1000), 'white')
            image.paste('black', (110, 110, 190, 290))
            image.paste('red', (700, 100, 900, 900))
            image.save(image_path)
            file = SimpleNamespace(id=7, filename='drawing.png', file_path=str(image_path))
            query = SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [file]))
            db = SimpleNamespace(execute=AsyncMock(return_value=query))
            rows = [{'name': 'MCB', 'category': 'MCB', 'spec': '20A', 'quantity': 1,
                     'tag': 'Q1'},
                    {'name': 'Meter', 'category': 'METER', 'spec': '', 'quantity': 1}]
            boxes = [{'device_id': str(i), 'verified': True, 'symbol_verified': True,
                      'symbol_box_2d': [100, 100, 200, 200], 'text_box_2d': [200, 100, 300, 200], 'tag_box_2d': [200, 100, 300, 200]}
                     for i in range(2)]
            checks = [{'device_id': str(i), 'matches': i == 0, 'symbol_complete': True,
                       'label_complete': True, 'isolated': True, 'tag_matches': True, 'observed': 'Q1 20A'} for i in range(2)]
            calls = AsyncMock(side_effect=[(json.dumps({'checks': checks}), None),
                                          (json.dumps({'boxes': []}), None), (json.dumps({'boxes': []}), None)])
            with patch('app.services.ai.scoped_takeoff.render_panel', AsyncMock(return_value=(str(image_path), 'Q1 20A'))), \
                 patch('app.services.ai.regional_takeoff.extract_regions', AsyncMock(return_value={'devices': rows, 'boxes': boxes})), \
                 patch('app.services.ai.scoped_takeoff.ConnectionPoolService.get_ordered_connections', AsyncMock(return_value=[object()])), \
                 patch('app.services.ai.scoped_takeoff.ConnectionPoolService.call_with_fallback', calls):
                result = await extract_confirmed_panels(db, 1, [{'source_file_id': 7,
                    'source_page': None, 'panel_code': 'P1', 'source_region': [.1, .1, .5, .5]}], 'Extract P1', whole_panel=False)
            self.assertEqual(calls.await_count, 3)  # Regional extraction mocked; audit + two recovery reads.
            self.assertTrue(result[0]['evidence_image'])
            self.assertEqual(result[0]['evidence'], 'Q1 20A')
            self.assertFalse(result[1]['evidence_image'])
            self.assertIsNone(result[0]['panel_evidence_image'])
            self.assertEqual({r['panel_code'] for r in result}, {'P1'})
            crop = Image.open(io.BytesIO(base64.b64decode(result[0]['evidence_image'].split(',')[1])))
            self.assertNotIn((255, 0, 0), crop.convert('RGB').getdata())


class ScopedCandidateCacheTests(unittest.TestCase):
    def test_candidate_cache_is_bound_to_source_request_scope_and_model(self):
        from app.services.ai.scoped_takeoff import scoped_candidate_key
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'drawing.dwg';path.write_bytes(b'source revision 1')
            file=SimpleNamespace(id=7,file_path=str(path));panel={'source_region':[0,0,1,1]}
            key=scoped_candidate_key(1,file,panel,'bóc toàn bộ','model-a')
            self.assertNotEqual(key,scoped_candidate_key(2,file,panel,'bóc toàn bộ','model-a'))
            self.assertNotEqual(key,scoped_candidate_key(1,file,panel,'bóc MCB','model-a'))
            self.assertNotEqual(key,scoped_candidate_key(1,file,panel,'bóc toàn bộ','model-b'))
            self.assertNotEqual(key,scoped_candidate_key(1,file,{'source_region':[0,0,.5,1]},'bóc toàn bộ','model-a'))
            path.write_bytes(b'source revision 2')
            self.assertNotEqual(key,scoped_candidate_key(1,file,panel,'bóc toàn bộ','model-a'))

if __name__ == '__main__':
    unittest.main()
