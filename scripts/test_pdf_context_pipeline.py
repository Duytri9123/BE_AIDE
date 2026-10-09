import json
import unittest
from unittest.mock import AsyncMock
from app.services.ai.pdf_context import build_context, extraction_prompt
from app.services.ai.response_parser import ResponseParserService
from app.services.ai.analysis_pipeline_service import AnalysisPipelineService
from app.schemas.ai import ExtractedDeviceSchema


class ContextTests(unittest.IsolatedAsyncioTestCase):
    async def test_text_pdf_never_uses_ocr(self):
        call=AsyncMock()
        result=await build_context('L1 CB-3P 20A 6kA','unused',call)
        call.assert_not_awaited()
        self.assertEqual(result['source'],'pdf_text_layer')
        self.assertIn('CB-3P',result['content'])

    async def test_scanned_pdf_transcribes_before_extraction(self):
        call=AsyncMock(return_value=json.dumps({'panels':[{'panel_code':'P','lines':[{'text':'L1 CB-3P 20A'}]}]}))
        result=await build_context('','page.png',call)
        self.assertEqual(result['source'],'ocr_transcription')
        self.assertIn('L1 CB-3P',extraction_prompt('contract',result))

    async def test_empty_ocr_blocks_unfounded_takeoff(self):
        with self.assertRaises(ValueError):
            await build_context('','page.png',AsyncMock(return_value='{"panels":[]}'))

    def test_quantity_evidence_survives_parser_and_normalization(self):
        parsed=ResponseParserService.parse_device_list(json.dumps({'devices':[{
            'category':'FUSE','name':'Cụm cầu chì','quantity':3,'drawing_quantity':1,
            'procurement_quantity':3,'quantity_basis':'Nhãn cụm ghi 3x6A','quantity_confidence':.98}]}))[0]
        row=ExtractedDeviceSchema(**vars(parsed))
        AnalysisPipelineService._infer_practical_quantities([row])
        AnalysisPipelineService._infer_practical_quantities([row])
        self.assertEqual((row.drawing_quantity,row.quantity,row.procurement_quantity),(1,3,3))
        self.assertIn('3x6a',row.quantity_basis.lower())


class AuditMergeTests(unittest.TestCase):
    def test_spatial_audit_preserves_unreviewed_devices_and_metadata(self):
        from app.services.ai.pdf_context import merge_verified_devices
        from app.services.ai.response_parser import ExtractedDevice
        main=ExtractedDevice(category='MCCB',name='MCCB tổng',spec='3P 200A 85kA',quantity=1,in_a=None,icu_ka=None,poles=None,brand='',part_number='',confidence=0.9,panel_code='P',tag='Q1',connected_load='Nguồn tổng')
        selector=ExtractedDevice(category='SELECTOR',name='Chuyển mạch',spec='',quantity=1,in_a=None,icu_ka=None,poles=None,brand='',part_number='',confidence=0.9,panel_code='P',tag='VS')
        reviewed=ExtractedDevice(category='CB',name='MCCB tổng',spec='3P 200A 85kA',quantity=1,in_a=None,icu_ka=None,poles=None,brand='',part_number='',confidence=0.9,panel_code='P',tag='Q1')
        rows=merge_verified_devices([main,selector],[reviewed])
        self.assertEqual([d.tag for d in rows],['Q1','VS'])
        self.assertEqual(rows[0].category,'MCCB')
        self.assertEqual(rows[0].connected_load,'Nguồn tổng')
        self.assertIsNone(rows[0].box_2d)
