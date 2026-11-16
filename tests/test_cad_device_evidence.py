import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from PIL import Image
from app.schemas.ai import ExtractedDeviceSchema
from app.services.ai.analysis_pipeline_service import AnalysisPipelineService as Pipeline
from app.services.ai.cad_device_evidence import attach_device_crops


class CadDeviceEvidenceTests(unittest.IsolatedAsyncioTestCase):
    async def test_only_audited_device_region_becomes_a_crop(self):
        devices = [ExtractedDeviceSchema(name='Breaker', category='MCB', spec='20A', tag='Q1'),
                   ExtractedDeviceSchema(name='Meter', category='METER', spec='', tag='M1')]
        checked = {'boxes': [{'device_id': '0', 'verified': True, 'symbol_verified': True,
                             'symbol_box_2d': [100, 100, 200, 200],
                             'text_box_2d': [200, 100, 300, 200]}]}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'source.png'
            image = Image.new('RGB', (1000, 1000), 'white')
            image.paste('black', (110, 110, 190, 290))
            image.paste('red', (700, 100, 900, 900))  # Adjacent device must stay out.
            image.save(path)
            with patch('app.services.ai.source_image_evidence.refine_locations', AsyncMock(return_value=checked)), \
                 patch('app.services.ai.source_image_evidence.audit_crops', AsyncMock(return_value=checked)):
                await attach_device_crops(devices, str(path), AsyncMock(return_value='{"boxes":[]}'))
        self.assertTrue(devices[0].evidence_image)
        self.assertEqual(devices[0].evidence_region['status'], 'verified')
        import base64, io
        crop = Image.open(io.BytesIO(base64.b64decode(devices[0].evidence_image.split(',')[1])))
        self.assertLess(crop.width, 300)
        self.assertNotIn((255, 0, 0), crop.convert('RGB').getdata())
        self.assertFalse(devices[1].evidence_image)

    def test_verified_crop_keeps_its_source_coordinate_frame(self):
        device = ExtractedDeviceSchema(name='Breaker', category='MCB', spec='20A', tag='Q1',
            box_2d=[100, 100, 200, 200], evidence_image='checked-crop',
            evidence_region={'status': 'verified', 'coordinate_space': 'normalized_1000',
                             'box_2d': [100, 100, 200, 200]})
        cad = SimpleNamespace(is_reliable=True, texts=[{'text': 'Q1', 'x': 50, 'y': 50}],
                              bounds={'min_x': 0, 'min_y': 0, 'width': 100, 'height': 100})
        Pipeline._attach_cad_evidence_regions([device], cad)
        self.assertEqual(device.box_2d, [100, 100, 200, 200])
        self.assertEqual(device.evidence_region['coordinate_space'], 'normalized_1000')

    def test_text_match_alone_does_not_claim_verified_device_location(self):
        device = ExtractedDeviceSchema(name='Breaker', category='MCB', spec='20A', tag='Q1')
        cad = SimpleNamespace(is_reliable=True, texts=[{'text': 'Q1', 'x': 50, 'y': 50}],
                              bounds={'min_x': 0, 'min_y': 0, 'width': 100, 'height': 100})
        Pipeline._attach_cad_evidence_regions([device], cad)
        self.assertEqual(device.evidence_region['status'], 'label_only')
        self.assertFalse(device.evidence_image)


if __name__ == '__main__':
    unittest.main()
