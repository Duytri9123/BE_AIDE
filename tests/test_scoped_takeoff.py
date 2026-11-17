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
            calls = AsyncMock(side_effect=[(json.dumps({'devices': rows, 'boxes': boxes}), None),
                                          (json.dumps({'checks': checks}), None),
                                          (json.dumps({'boxes': []}), None), (json.dumps({'boxes': []}), None)])
            with patch('app.services.ai.scoped_takeoff.render_panel', AsyncMock(return_value=(str(image_path), 'Q1 20A'))), \
                 patch('app.services.ai.scoped_takeoff.ConnectionPoolService.get_ordered_connections', AsyncMock(return_value=[object()])), \
                 patch('app.services.ai.scoped_takeoff.ConnectionPoolService.call_with_fallback', calls):
                result = await extract_confirmed_panels(db, 1, [{'source_file_id': 7,
                    'source_page': None, 'panel_code': 'P1', 'source_region': [.1, .1, .5, .5]}], 'Extract P1')
            self.assertEqual(calls.await_count, 4)  # Extraction + audit + two bounded recovery reads.
            self.assertTrue(result[0]['evidence_image'])
            self.assertEqual(result[0]['evidence'], 'Q1 20A')
            self.assertFalse(result[1]['evidence_image'])
            self.assertIsNone(result[0]['panel_evidence_image'])
            self.assertEqual({r['panel_code'] for r in result}, {'P1'})
            crop = Image.open(io.BytesIO(base64.b64decode(result[0]['evidence_image'].split(',')[1])))
            self.assertNotIn((255, 0, 0), crop.convert('RGB').getdata())


if __name__ == '__main__':
    unittest.main()
