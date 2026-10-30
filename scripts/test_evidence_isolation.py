import base64
import io
import json
import unittest
from unittest.mock import AsyncMock

from PIL import Image, ImageDraw
from app.schemas.ai import ExtractedDeviceSchema as Device
from app.services.ai.analysis_pipeline_service import AnalysisPipelineService as Pipeline
from app.services.ai.source_image_evidence import audit_crops


class EvidenceIsolationTests(unittest.IsolatedAsyncioTestCase):
    def test_missing_numeric_fields_are_not_a_transcription_conflict(self):
        from app.services.ai.source_semantic_review import preserve_transcribed_label
        device = Device(category='MCCB',name='Main',spec='MCCB-630A3P',
                        source_observations={'spec_label':'MCCB-630A3P'})
        self.assertFalse(preserve_transcribed_label(device, {
            'source_spec':'MCCB-630A3P','poles':3,'in_a':630}))
        device.in_a = 630
        self.assertTrue(preserve_transcribed_label(device, {
            'source_spec':'MCCB-160A3P','poles':3,'in_a':160}))

    def test_rejected_or_missing_recheck_clears_old_verified_crop(self):
        for payload in ({'boxes': []}, {'boxes': [{'device_id': '0', 'verified': False}]}):
            device = Device(category='METER', name='Meter', spec='', box_2d=[100,100,200,200],
                            evidence_image='old-image', evidence_images=[{'evidence_image':'old-image'}],
                            evidence_region={'status':'verified'})
            Pipeline._apply_verified_boxes([device], payload, require_symbols=True)
            self.assertIsNone(device.box_2d)
            self.assertIsNone(device.evidence_image)
            self.assertFalse(device.evidence_images)
            self.assertEqual(device.evidence_region['verification_status'], 'needs_review')

    def test_separated_symbol_and_label_do_not_include_intervening_feeder(self):
        image = Image.new('RGB', (1000,1000), 'white')
        draw = ImageDraw.Draw(image)
        draw.rectangle((100,100,140,140), fill='black')
        draw.rectangle((300,100,340,140), fill='blue')
        draw.rectangle((200,95,250,145), fill='red')  # Other feeder inside the union.
        device = Device(category='MCCB', name='Breaker', spec='', box_2d=[100,100,140,340],
                        evidence_region={'symbol_box_2d':[100,100,141,141],
                                         'text_box_2d':[100,300,141,341]})
        previews = Pipeline._linked_evidence_images(device, image)
        output = Image.open(io.BytesIO(base64.b64decode(previews[0]['evidence_image'].split(',')[1])))
        colors = set(output.get_flattened_data())
        self.assertIn((0,0,0), colors)
        self.assertIn((0,0,255), colors)
        self.assertNotIn((255,0,0), colors)

    async def test_audit_requires_complete_isolated_symbol_and_label(self):
        for failed in ('symbol_complete', 'label_complete', 'isolated', 'missing'):
            check = dict(device_id='0', matches=True, symbol_complete=True, label_complete=True,
                         isolated=True, observed='source mark')
            if failed == 'missing':
                del check['isolated']
            else:
                check[failed] = False
            row = dict(device_id='0', verified=True, symbol_verified=True,
                       symbol_box_2d=[100,100,200,200], text_box_2d=[100,210,200,300])
            call = AsyncMock(return_value=json.dumps({'checks':[check]}))
            result = await audit_crops(Image.new('RGB',(1000,1000),'white'), call,
                                      [Device(category='METER', name='Meter', spec='')], {'boxes':[row]})
            self.assertFalse(result['boxes'][0]['verified'], failed)

    async def test_complete_isolated_evidence_passes_with_source_context(self):
        async def inspect(path, prompt):
            with Image.open(path) as image:
                self.assertEqual(image.width, 1320)
            self.assertIn('ngữ cảnh', prompt)
            return json.dumps({'checks':[dict(device_id='0', matches=True, symbol_complete=True,
                               label_complete=True, isolated=True, observed='MCCB 630A 3P')]})
        row = dict(device_id='0', verified=True, symbol_verified=True,
                   symbol_box_2d=[100,100,200,200], text_box_2d=[100,210,200,300])
        result = await audit_crops(Image.new('RGB',(1000,1000),'white'), inspect,
                                  [Device(category='MCCB',name='Breaker',spec='630A 3P')], {'boxes':[row]})
        self.assertTrue(result['boxes'][0]['verified'])


if __name__ == '__main__':
    unittest.main()
