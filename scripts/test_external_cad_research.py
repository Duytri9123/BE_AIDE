import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.ai.response_parser import ResponseParserService
from app.schemas.ai import ExtractedDeviceSchema
from app.services.cad.external_research import research_missing_geometry, acquire_supplier_dxf


class ExternalCadTests(unittest.IsolatedAsyncioTestCase):
    async def test_ready_geometry_never_queries_web_or_database(self):
        db = AsyncMock()
        rows = [{'cad': {'asset_id': 'verified'}}]
        self.assertIs(await research_missing_geometry(rows, db), rows)
        db.execute.assert_not_called()

    async def test_same_product_is_searched_once_without_project_documents(self):
        connection = SimpleNamespace(provider='google', api_key='test', selected_model='test')
        first = MagicMock(); first.scalars.return_value.first.return_value = connection
        second = MagicMock(); second.scalar_one_or_none.return_value = None
        db = SimpleNamespace(execute=AsyncMock(side_effect=[first, second]))
        rows = [dict(brand='LS', category='MCB', spec='3P 20A 10kA', source_filename='private.pdf', cad={}) for _ in range(2)]
        with patch('app.services.cad.external_research.DeviceCatalogEngine.get_instance'), \
             patch('app.services.cad.external_research.WebSearchService.search', new_callable=AsyncMock) as search, \
             patch('app.services.cad.external_research.product_information', return_value={'sources': [], 'ai_summary': ''}):
            search.return_value = {'success': True, 'results': []}
            result = await research_missing_geometry(rows, db)
            search.assert_awaited_once()
            self.assertNotIn('private.pdf', search.call_args.args[0])
            self.assertEqual(result[0]['cad']['external_research']['status'], 'no_verified_sources')
            self.assertFalse(result[0]['cad']['external_research']['fabrication_ready'])

    async def test_untrusted_download_is_not_requested(self):
        with patch('app.services.cad.external_research.httpx.AsyncClient') as client:
            self.assertIsNone(await acquire_supplier_dxf({'url': 'https://other.example/drawing.dxf'}, 'LS'))
            client.assert_not_called()

    def test_ai_analysis_survives_parser_and_public_schema(self):
        parsed = ResponseParserService.parse_device_list(json.dumps({'devices': [{
            'category': 'MCB', 'name': 'CB', 'spec': '3P 20A 10kA',
            'technical_analysis': 'Thông số bảo vệ được đọc từ nhãn thiết bị.'}]}))
        self.assertEqual(len(parsed), 1)
        public = ExtractedDeviceSchema.model_validate(vars(parsed[0]))
        self.assertEqual(public.technical_analysis, parsed[0].technical_analysis)


if __name__ == '__main__':
    unittest.main()
