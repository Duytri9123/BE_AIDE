"""Check reduced model round trips without bypassing source verification."""
import tempfile
import time
import statistics
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.api.v1.endpoints import el_agent
from app.services.ai import requirement_analysis


class RoutingTests(unittest.IsolatedAsyncioTestCase):
    async def test_greetings_do_not_invoke_model_or_discover_sources(self):
        durations = []
        with patch.object(el_agent, 'owned_project', AsyncMock()), patch.object(el_agent.ConnectionPoolService, 'call_with_fallback', AsyncMock()) as model, patch('app.services.ai.takeoff_regions.discover_panels', AsyncMock()) as discovery:
            for message in ['hi', 'Hi!', 'hello', 'xin chào', 'chào EL', 'cảm ơn', 'ok'] * 10:
                payload = SimpleNamespace(project_id=1, message=message,
                    context={'file_ids': [7], 'takeoff_scope': [{'scope_token': 'expired'}]})
                started = time.perf_counter()
                result = await el_agent.next_action(payload, SimpleNamespace(app=None), None, None)
                durations.append((time.perf_counter() - started) * 1000)
                self.assertTrue(result['reply'])
                self.assertNotIn('devices', result)
            model.assert_not_awaited()
            discovery.assert_not_awaited()
        print(f'Greeting routing (70 mocked-auth calls): median={statistics.median(durations):.3f} ms max={max(durations):.3f} ms')

    async def test_unconfirmed_takeoff_only_discovers_panels(self):
        payload = SimpleNamespace(project_id=1, message='Bóc tách thiết bị trong bản vẽ',
            context={'file_ids': [7], 'tools': [{'name': 'read_project_sources'}]})
        with patch.object(el_agent, 'owned_project', AsyncMock()), patch('app.services.ai.takeoff_regions.discover_panels', AsyncMock(return_value={'requires_confirmation': True})) as discovery, patch('app.services.ai.scoped_takeoff.extract_confirmed_panels', AsyncMock()) as extractor:
            result = await el_agent.next_action(payload, SimpleNamespace(app=None), None, None)
        self.assertTrue(result['requires_confirmation'])
        discovery.assert_awaited_once_with(None, 1, [7])
        extractor.assert_not_awaited()

    async def test_confirmed_takeoff_uses_direct_scoped_extractor(self):
        from app.services.ai.takeoff_regions import sign_scope
        panel = {'source_file_id': 7, 'source_page': 1, 'panel_code': 'P1', 'source_region': [.1, .2, .4, .6]}
        payload = SimpleNamespace(project_id=1, message='Bóc tách tủ đã xác nhận P1', context={
            'file_ids': [7], 'takeoff_scope': [{'scope_token': sign_scope(panel, 1)}]})
        rows = [{'name': 'MCB', 'panel_code': 'P1'}]
        with patch.object(el_agent, 'owned_project', AsyncMock()), patch('app.services.ai.scoped_takeoff.extract_confirmed_panels', AsyncMock(return_value=rows)) as extractor, patch.object(el_agent, 'format_reply_response', AsyncMock(return_value={'reply': 'saved'})) as formatter, patch.object(el_agent.ConnectionPoolService, 'call_with_fallback', AsyncMock()) as planner:
            result = await el_agent.next_action(payload, SimpleNamespace(app=None), None, None)
        self.assertEqual(result['reply'], 'saved')
        self.assertEqual(extractor.await_args.args[2][0]['source_region'], panel['source_region'])
        self.assertEqual(formatter.await_args.args[3]['observations'][0]['arguments']['source_region'], panel['source_region'])
        planner.assert_not_awaited()

    async def test_scope_retries_once_after_missing_evidence_and_does_not_claim_success(self):
        from app.services.ai.takeoff_regions import sign_scope
        panel = {'source_file_id': 7, 'source_page': 1, 'panel_code': 'P1', 'source_region': [.1, .2, .4, .6]}
        payload = SimpleNamespace(project_id=1, message='Bóc tách P1', context={
            'file_ids': [7], 'takeoff_scope': [{'scope_token': sign_scope(panel, 1)}]})
        with patch.object(el_agent, 'owned_project', AsyncMock()), patch('app.services.ai.scoped_takeoff.extract_confirmed_panels', AsyncMock(return_value=[])) as extractor, patch.object(el_agent, 'format_reply_response', AsyncMock(return_value={'verification_feedback': 'Thiếu ảnh tag L4'})):
            result = await el_agent.next_action(payload, SimpleNamespace(app=None), None, None)
        self.assertEqual(extractor.await_count, 2)
        self.assertIn('Thiếu ảnh tag L4', extractor.await_args.args[3])
        self.assertIn('chưa lưu', result['reply'])
        self.assertNotIn('iteration_id', result)

    async def test_simple_question_uses_short_prompt_and_retains_context(self):
        payload = SimpleNamespace(project_id=1, message='Nó là gì?', context={
            'messages': [{'role': 'user', 'content': 'MCCB'}],
            'observations': [{'tool': 'read_project_sources', 'result': 'MCCB Q1'}]})
        with patch.object(el_agent, 'owned_project', AsyncMock()), patch.object(el_agent, 'api_tools', return_value={}), patch.object(el_agent.ConnectionPoolService, 'get_ordered_connections', AsyncMock(return_value=[object()])), patch.object(el_agent.ConnectionPoolService, 'call_with_fallback', AsyncMock(return_value=('{"reply":"MCCB Q1"}', None))) as model, patch.object(el_agent, 'format_reply_response', AsyncMock(return_value={'reply': 'MCCB Q1'})):
            await el_agent.next_action(payload, SimpleNamespace(app=None), None, None)
        prompt = model.await_args.kwargs['prompt']
        self.assertLess(len(prompt), 3000)
        self.assertIn('MCCB Q1', prompt)
        self.assertIn('Nó là gì?', prompt)
        self.assertNotIn('8 CỘT', prompt)

    async def test_single_checked_source_does_not_call_synthesis(self):
        with tempfile.TemporaryDirectory() as folder:
            image = Path(folder) / 'source.png'
            image.write_bytes(b'mocked image')
            file = SimpleNamespace(id=7, filename='source.png', file_path=str(image))
            result = MagicMock()
            result.scalars.return_value = [file]
            db = SimpleNamespace(execute=AsyncMock(return_value=result))
            checked = {'information': 'Q1: chưa ghi thông số', 'numeric_checks': [{'status': 'uncertain'}]}
            with patch.object(requirement_analysis, 'read_image_checked', AsyncMock(return_value=checked)) as reader, patch.object(requirement_analysis.ConnectionPoolService, 'call_with_fallback', AsyncMock()) as synthesis:
                plan = await requirement_analysis.analyze_requirements(db, [], 1, 'Đọc tủ này', {
                    'file_ids': [7], 'messages': [{'role': 'user', 'content': 'Chọn tủ AP1'}]})
            synthesis.assert_not_awaited()
            self.assertIn('Chọn tủ AP1', reader.await_args.args[5])
            self.assertEqual(plan.operations, [])
            self.assertEqual(plan.source_reading['sources'][0]['numeric_checks'], checked['numeric_checks'])


if __name__ == '__main__':
    unittest.main()
