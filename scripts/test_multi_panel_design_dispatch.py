import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from app.services.ai.analysis_pipeline_service import AnalysisPipelineService


class MultiPanelDispatchTests(unittest.IsolatedAsyncioTestCase):
    async def test_separate_panels_and_require_both_to_complete(self):
        original = AnalysisPipelineService.generate_cad_and_quotation
        empty_result = Mock()
        empty_result.scalars.return_value.first.return_value = None
        db = SimpleNamespace(execute=AsyncMock(return_value=empty_result))
        rows = [{'panel_code': 'PX1', 'name': 'Main1'}, {'panel_code': 'PX2', 'name': 'Main2'}]
        first = dict(cad_status='ready', cad_file={'id': 1}, cad_blockers=[],
                     devices=[rows[0]], quotation_rows=[{'panel_code': 'PX1'}])
        second = dict(cad_status='needs_review', cad_file=None, cad_blockers=['missing contactor'],
                      devices=[rows[1]], quotation_rows=[{'panel_code': 'PX2'}])
        with patch.object(AnalysisPipelineService, 'generate_cad_and_quotation',
                          new=AsyncMock(side_effect=[first, second])) as generate:
            result = await original(SimpleNamespace(id=16), db, rows,
                enclosure_dimensions='600x400x250', multi_panel_list=[
                    {'panel_code': 'PX1', 'dimension': '900x600x250'},
                    {'panel_code': 'PX2', 'dimension': '700x500x250'}])
        self.assertFalse(result['success'])
        self.assertEqual(result['cad_blockers'], ['PX2: missing contactor'])
        self.assertEqual(result['quotation_rows'], [])
        self.assertEqual(generate.await_args_list[0].args[2], [rows[0]])
        self.assertEqual(generate.await_args_list[1].args[2], [rows[1]])
        self.assertEqual(generate.await_args_list[0].kwargs['enclosure_dimensions'], '900x600x250')
        self.assertEqual(generate.await_args_list[1].kwargs['enclosure_dimensions'], '700x500x250')
        self.assertTrue(all(call.kwargs['per_panel'] for call in generate.await_args_list))

    async def test_saved_requirements_reach_each_panel(self):
        original = AnalysisPipelineService.generate_cad_and_quotation
        session = SimpleNamespace(id=1)
        latest = SimpleNamespace(user_message='LS, thao tac qua canh trong', confidence_scores={}, ai_parsed_devices=[])
        results = []
        for value in (latest, session, latest):
            result = Mock()
            result.scalars.return_value.first.return_value = value
            results.append(result)
        db = SimpleNamespace(execute=AsyncMock(side_effect=results), commit=AsyncMock())
        output = dict(cad_status='needs_review', cad_file=None, cad_blockers=[], devices=[], quotation_rows=[])
        with patch.object(AnalysisPipelineService, 'generate_cad_and_quotation', new=AsyncMock(return_value=output)) as generate:
            await original(SimpleNamespace(id=16), db, [{'panel_code':'PX1'}, {'panel_code':'PX2'}])
        self.assertEqual(len(generate.await_args_list), 2)
        for call in generate.await_args_list:
            self.assertEqual(call.kwargs['user_prompt'], latest.user_message)

    def test_user_brand_is_found_in_geometry_catalog_without_price_rows(self):
        engine = SimpleNamespace(items=[], reference_profiles=[{'brand': 'Schneider'}, {'brand': 'LS'}])
        self.assertEqual(AnalysisPipelineService._detect_requested_brand('Dùng Schneider', engine), 'Schneider')
        self.assertIsNone(AnalysisPipelineService._detect_requested_brand('Tủ ngoài trời', engine))


if __name__ == '__main__':
    unittest.main()
