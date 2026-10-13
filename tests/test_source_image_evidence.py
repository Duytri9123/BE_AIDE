import tempfile
import unittest
from pathlib import Path
from PIL import Image
from app.schemas.ai import ExtractedDeviceSchema
from app.services.ai.source_image_evidence import oriented_source
from app.services.ai.analysis_pipeline_service import AnalysisPipelineService
from app.services.ai.web_device_recommendations import technical_search_key
from app.services.ai.inventory_validation import inventory_kind


class SourceImageTests(unittest.IsolatedAsyncioTestCase):
    def test_png_transport_matches_declared_jpeg_and_keeps_aspect(self):
        import io
        from app.services.ai.vision_analyzer import normalize_vision_image_bytes
        image=Image.new('RGBA',(900,1600),(0,0,0,0));data=io.BytesIO();image.save(data,format='PNG')
        decoded=Image.open(io.BytesIO(normalize_vision_image_bytes(data.getvalue())))
        self.assertEqual(decoded.format,'JPEG')
        self.assertEqual(decoded.size,(900,1600))
        self.assertEqual(decoded.getpixel((0,0)),(255,255,255))
    async def test_malformed_quad_cannot_break_location_verification(self):
        import json
        from unittest.mock import AsyncMock
        from app.services.ai.source_image_evidence import refine_locations
        device=ExtractedDeviceSchema(category='LIGHT',name='Đèn báo R',spec='',tag='R')
        call=AsyncMock(return_value=json.dumps({'boxes':[{'device_id':'0','verified':True,'symbol_verified':True,
            'symbol_box_2d':[10,10,20,20],'text_box_2d':[10,10,20,20],'branch_quad':[1,2,3,4]}]}))
        result=await refine_locations(Image.new('RGB',(900,1600)),call,[device],{'boxes':[]})
        self.assertEqual(result['boxes'][0]['branch_quad'],[])

    def test_different_phase_lamps_cannot_share_one_symbol_crop(self):
        devices=[ExtractedDeviceSchema(category='LIGHT',name='Đèn '+tag,spec='',tag=tag) for tag in ['R','Y']]
        payload={'boxes':[{'device_id':str(i),'verified':True,'symbol_verified':True,
            'symbol_box_2d':[10,10,20,20],'text_box_2d':[10,10,20,20]} for i in range(2)]}
        AnalysisPipelineService._apply_verified_boxes(devices,payload,require_symbols=True)
        self.assertTrue(all(d.box_2d is None for d in devices))
    def test_portrait_coordinates_preserve_native_axes(self):
        left, top, right, bottom = AnalysisPipelineService._evidence_crop_pixels([250, 250, 750, 750], 900, 1600)
        self.assertEqual((left, top, right, bottom), (207, 336, 693, 1264))

    def test_exif_rotation_uses_same_oriented_canvas(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'source.jpg'
            image = Image.new('RGB', (1600, 900))
            exif = image.getexif(); exif[274] = 6
            image.save(path, exif=exif)
            self.assertEqual(oriented_source(path).size, (900, 1600))

    def test_same_spec_different_branch_uses_same_search(self):
        first = ExtractedDeviceSchema(category='MCB', name='Nhánh bơm M1', spec='3P 20A 6kA', poles=3, in_a=20, icu_ka=6)
        other = first.model_copy(update={'name': 'Nhánh bơm M2', 'tag': 'M2'})
        self.assertEqual(technical_search_key(first), technical_search_key(other))

    def test_current_transformer_is_not_meter(self):
        self.assertEqual(inventory_kind('METER', 'Biến dòng đo lường 3XCT', '63/5'), 'CT')

    def test_timer_registry_does_not_infer_absent_portfolio(self):
        from app.services.ai.manufacturer_registry import manufacturer_categories, portfolio_hint
        registry = manufacturer_categories()
        self.assertIn('TIMER', registry['Omron']['categories'])
        self.assertNotIn('TIMER', registry['LS Electric']['categories'])
        self.assertEqual(registry['LS Electric']['other_categories_status'], 'unknown')
        self.assertIn('Autonics', portfolio_hint('TIMER'))

    def test_unverified_device_does_not_retain_stale_image(self):
        device = ExtractedDeviceSchema(category='FUSE', name='Cầu chì bổ sung', spec='', evidence_image='stale', box_2d=[0, 0, 50, 50])
        AnalysisPipelineService._apply_verified_boxes([device], {'boxes': []}, require_symbols=True)
        self.assertIsNone(device.evidence_image)
        self.assertIsNone(device.box_2d)
