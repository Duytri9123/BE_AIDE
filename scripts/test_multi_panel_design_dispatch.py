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
        self.assertEqual(len(result['quotation_rows']), 2)
        self.assertEqual(generate.await_args_list[0].args[2], [rows[0]])
        self.assertEqual(generate.await_args_list[1].args[2], [rows[1]])
        self.assertEqual(generate.await_args_list[0].kwargs['enclosure_dimensions'], '900x600x250')
        self.assertEqual(generate.await_args_list[1].kwargs['enclosure_dimensions'], '700x500x250')
        self.assertTrue(all(call.kwargs['per_panel'] for call in generate.await_args_list))


if __name__ == '__main__':
    unittest.main()
