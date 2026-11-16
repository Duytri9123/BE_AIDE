import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pymupdf
from app.services.ai.requirement_analysis import render_pdf_page
from app.services.ai.takeoff_verifier import verify_takeoff


class SourceCropTests(unittest.TestCase):
    def test_crop_preserves_only_region_text_and_zooms(self):
        with tempfile.TemporaryDirectory() as folder:
            pdf, image = Path(folder) / 'source.pdf', Path(folder) / 'crop.png'
            doc = pymupdf.open()
            page = doc.new_page(width=600, height=400)
            page.insert_text((50, 60), 'LEFT WP1 250A')
            page.insert_text((400, 60), 'RIGHT WP2 125A')
            doc.save(pdf)
            doc.close()
            text = render_pdf_page(pdf, 1, image, [0, 0, .5, 1])
            self.assertIn('LEFT WP1 250A', text)
            self.assertNotIn('RIGHT', text)
            pixmap = pymupdf.Pixmap(str(image))
            self.assertEqual((pixmap.width, pixmap.height), (1800, 2400))


class VisualAuditTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.pdf = Path(self.folder.name) / 'source.pdf'
        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_text((40, 80), 'WP1 250A; WP2 no rating')
        doc.save(self.pdf)
        doc.close()
        self.file = SimpleNamespace(id=7, filename='source.pdf', file_path=str(self.pdf))
        self.rows = [{'source_file_id': 7, 'source_page': 1, 'panel_code': 'P',
                      'tag': 'WP2', 'spec': '125A', 'quantity': 1}]

    async def review(self, response):
        with patch('app.services.ai.takeoff_verifier.ConnectionPoolService.get_ordered_connections', AsyncMock(return_value=[object()])), patch('app.services.ai.takeoff_verifier.ConnectionPoolService.call_with_fallback', AsyncMock(return_value=(response, None))):
            return await verify_takeoff(None, [self.file], self.rows, 'Extract P', [])

    async def test_rejected_visual_audit_is_not_passed(self):
        result = await self.review('{"passed":false,"feedback":"WP2 has no rating"}')
        self.assertFalse(result['passed'])
        self.assertIn('WP2', result['feedback'])

    async def test_malformed_model_review_fails_closed(self):
        self.assertFalse((await self.review('done'))['passed'])
        self.assertFalse((await self.review('{"passed":"true"}'))['passed'])

    async def test_success_requires_boolean_visual_approval(self):
        self.assertTrue((await self.review('{"passed":true,"feedback":"Matches source"}'))['passed'])

    async def test_invalid_page_never_reaches_model(self):
        self.rows[0]['source_page'] = 2
        with patch('app.services.ai.takeoff_verifier.ConnectionPoolService.get_ordered_connections', AsyncMock(return_value=[object()])), patch('app.services.ai.takeoff_verifier.ConnectionPoolService.call_with_fallback', AsyncMock()) as model:
            result = await verify_takeoff(None, [self.file], self.rows, 'Extract P', [])
            self.assertFalse(result['passed'])
            model.assert_not_awaited()

    async def test_discovery_is_independent_of_candidate(self):
        with patch('app.services.ai.takeoff_verifier.ConnectionPoolService.get_ordered_connections', AsyncMock(return_value=[object()])), patch('app.services.ai.takeoff_verifier.ConnectionPoolService.call_with_fallback', AsyncMock(side_effect=[('WP2 no rating; one meter', None), ('{"passed":false,"feedback":"Missing meter"}', None)])) as model:
            result = await verify_takeoff(None, [self.file], self.rows, 'Extract P', [])
            self.assertFalse(result['passed'])
            discovery, comparison = model.await_args_list
            self.assertNotIn('candidate', discovery.kwargs['prompt'])
            self.assertIn('WP2 no rating; one meter', comparison.kwargs['prompt'])
            self.assertIn('candidate', comparison.kwargs['prompt'])


class ToolResultTests(unittest.IsolatedAsyncioTestCase):
    async def test_catalog_items_survive_excerpt_before_filter_metadata(self):
        from fastapi import FastAPI
        from app.services.ai.el_tools import execute_api_tool
        app = FastAPI()
        @app.get('/catalog')
        async def catalog():
            return {'categories': ['metadata' * 1000] * 20, 'items': [{'sku': 'ACTUAL-500', 'api_key': 'hidden'}], 'total': 1}
        tool = {'path': '/catalog', 'method': 'GET', 'bound': {},
                'input_schema': {'properties': {'query': {'properties': {'q': {}}}}}}
        result = await execute_api_tool(app, None, 9, 37, tool, {'query': {'q': 'MCCB'}}, {})
        import json
        excerpt = json.dumps(result)[:12000]
        self.assertIn('ACTUAL-500', excerpt)
        self.assertNotIn('hidden', excerpt)

    async def test_unknown_tool_query_is_rejected_instead_of_ignored(self):
        from fastapi import HTTPException
        from app.services.ai.el_tools import execute_api_tool
        tool = {'input_schema': {'properties': {'query': {'properties': {'q': {}}}}}}
        with self.assertRaises(HTTPException) as error:
            await execute_api_tool(None, None, 9, 37, tool, {'query': {'wrong': 'x'}}, {})
        self.assertEqual(error.exception.status_code, 422)


class SavedExtractionSchemaTests(unittest.TestCase):
    def test_group_unit_and_source_evidence_survive_api_serialization(self):
        from app.schemas.ai import ExtractedDeviceSchema
        row = ExtractedDeviceSchema(category='CT', name='TI', spec='500/5', quantity=1,
                                    unit='Cụm', source_file_id=119, source_page=1,
                                    evidence='TI 500/5', observed_text='TI 500/5')
        saved = row.model_dump()
        self.assertEqual(saved['unit'], 'Cụm')
        self.assertEqual(saved['source_file_id'], 119)
        self.assertEqual(saved['evidence'], 'TI 500/5')
