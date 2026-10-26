import unittest
from unittest.mock import AsyncMock, patch
from PIL import Image
from app.schemas.ai import ExtractedDeviceSchema
from app.services.ai.source_image_evidence import verify_pdf_measurement_crops


class PdfMeasurementCropTests(unittest.IsolatedAsyncioTestCase):
    async def test_only_measurement_rows_are_refined_and_audited(self):
        meter = ExtractedDeviceSchema(category='VOLTMETER', name='Vôn kế', spec='0-600V', box_2d=[355,155,384,195])
        breaker = ExtractedDeviceSchema(category='MCB', name='MCB', spec='', box_2d=[100,300,120,400])
        payload = {'boxes': [{'device_id':'0', 'verified':True, 'symbol_verified':True,
            'symbol_box_2d':[375,160,385,175], 'text_box_2d':[365,160,375,190]}]}
        with patch('app.services.ai.source_image_evidence.refine_locations', AsyncMock(return_value=payload)) as refine, \
             patch('app.services.ai.source_image_evidence.audit_crops', AsyncMock(return_value=payload)) as audit:
            failures = await verify_pdf_measurement_crops(Image.new('RGB',(100,100)), AsyncMock(), [breaker,meter])
        self.assertFalse(failures)
        self.assertEqual(refine.call_args.args[2], [meter])
        audit.assert_awaited_once()
        self.assertEqual(meter.box_2d,[365,160,385,190])
        self.assertEqual(breaker.box_2d,[100,300,120,400])

    async def test_rejected_crop_is_not_published_as_verified(self):
        meter = ExtractedDeviceSchema(category='VOLTMETER', name='Vôn kế', spec='', box_2d=[355,155,384,195], evidence_image='wrong-crop')
        payload={'boxes':[{'device_id':'0','verified':False}]}
        with patch('app.services.ai.source_image_evidence.refine_locations',AsyncMock(return_value=payload)), \
             patch('app.services.ai.source_image_evidence.audit_crops',AsyncMock(return_value=payload)):
            failures=await verify_pdf_measurement_crops(Image.new('RGB',(100,100)),AsyncMock(),[meter])
        self.assertEqual(failures,[meter])
        self.assertIsNone(meter.box_2d)
        self.assertIsNone(meter.evidence_image)


if __name__ == '__main__':
    unittest.main()
