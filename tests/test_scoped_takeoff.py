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
                    'source_page': None, 'panel_code': 'P1', 'source_region': [.1, .1, .5, .5]}], 'Extract P1')
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
