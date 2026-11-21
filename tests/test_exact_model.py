import unittest
import asyncio,time
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
from app.services.ai.vision_analyzer import normalize_antigravity_model, VisionAnalyzerService
from app.services.ai.connection_pool import ConnectionPoolService
from app.core.exceptions import AIVisionError, AIRateLimitError
from app.core.exceptions import AITimeoutError

class ExactModelTests(unittest.IsolatedAsyncioTestCase):
    async def test_queued_request_gets_its_own_model_deadline(self):
        from app.services.ai.connection_pool import call_connection_request, connection_request_gate

        connection = SimpleNamespace(provider='antigravity', api_key='queue-test')
        with patch.dict('os.environ', {'AI_CONNECTION_CONCURRENCY': '1'}), \
             patch('app.core.config.settings.AI_VISION_TIMEOUT', .4), \
             patch('app.services.ai.connection_pool.TokenRefreshService.get_active_token', AsyncMock(return_value='test-token')):
            async def call(**kwargs):
                await asyncio.sleep(.25)
                return 'ok'

            async with connection_request_gate(connection):
                request = asyncio.create_task(call_connection_request(call, connection, 'test-model', {}))
                await asyncio.sleep(.25)
            self.assertEqual(await request, 'ok')

    async def test_pool_preserves_timeout_type_after_localizing_the_message(self):
        from app.services.ai.connection_pool import transient_transport_failure
        model='ag/gemini-3.8-flash-high'
        connection=SimpleNamespace(id=1,provider='antigravity',selected_model=model,
            name='test',priority=1,quotas={},api_key='test-token')
        db=MagicMock();result=MagicMock();result.scalars.return_value.all.return_value=[]
        db.execute=AsyncMock(return_value=result)
        with patch.object(ConnectionPoolService,'_record_connection_error',AsyncMock()), \
             patch('app.services.ai.connection_pool.TokenRefreshService.get_active_token',AsyncMock(return_value='test-token')):
            with self.assertRaises(AIVisionError) as captured:
                await ConnectionPoolService.call_with_fallback(db,[connection],
                    AsyncMock(side_effect=AITimeoutError('Hết thời gian chờ 60s')))
        self.assertEqual(captured.exception.details['last_error_type'],'AITimeoutError')
        self.assertTrue(transient_transport_failure(captured.exception))
        self.assertFalse(transient_transport_failure(AIRateLimitError('429')))

    async def test_same_account_requests_are_bounded_across_copied_connections(self):
        from app.services.ai.connection_pool import call_connection_request
        running=0;peak=0
        async def call(**kwargs):
            nonlocal running,peak
            running+=1;peak=max(peak,running)
            await asyncio.sleep(.01);running-=1
            return 'ok'
        connections=[SimpleNamespace(provider='antigravity',api_key='same-test-token') for _ in range(6)]
        with patch.dict('os.environ',{'AI_CONNECTION_CONCURRENCY':'2'}), \
             patch('app.services.ai.connection_pool.TokenRefreshService.get_active_token',AsyncMock(return_value='active-test-token')):
            result=await asyncio.gather(*(call_connection_request(call,c,'ag/gemini-3.8-flash-high',{}) for c in connections))
        self.assertEqual(result,['ok']*6);self.assertEqual(peak,2)

    async def test_connection_deadline_includes_stalled_token_renewal(self):
        from app.services.ai.connection_pool import call_connection_request
        cancelled=asyncio.Event()
        async def refresh(token):
            try:await asyncio.Event().wait()
            finally:cancelled.set()
        call=AsyncMock()
        connection=SimpleNamespace(provider='antigravity',api_key='test-token')
        with patch('app.services.ai.connection_pool.TokenRefreshService.get_active_token',new=refresh), \
             patch('app.core.config.settings.AI_VISION_TIMEOUT',.02):
            with self.assertRaises(AITimeoutError):
                await call_connection_request(call,connection,'ag/gemini-3.8-flash-high',{})
        self.assertTrue(cancelled.is_set());call.assert_not_awaited()

    async def test_structured_extraction_enables_json_without_changing_native_model(self):
        from app.services.ai.regional_takeoff import COVERAGE_SCHEMA
        response=httpx.Response(200,json={'candidates':[{'content':{'parts':[{'text':'{"checks":[]}'}]}}]},
            request=httpx.Request('POST','https://example.test'))
        client=AsyncMock();client.post.return_value=response
        with patch('app.services.ai.vision_analyzer.httpx.AsyncClient') as factory:
            factory.return_value.__aenter__.return_value=client
            await VisionAnalyzerService._call_antigravity('', 'test', 'test-token',
                'ag/gemini-3.8-flash-high',project_id='test-project',json_mode=True,response_schema=COVERAGE_SCHEMA)
        payload=client.post.call_args.kwargs['json']
        self.assertEqual(payload['model'],'gemini-3.8-flash-high')
        self.assertEqual(payload['request']['generationConfig']['responseMimeType'],'application/json')
        self.assertEqual(payload['request']['generationConfig']['responseSchema'],COVERAGE_SCHEMA)
        self.assertNotIn('temperature',payload['request']['generationConfig'])

    async def test_wall_time_deadline_cancels_a_stalled_request(self):
        cancelled=asyncio.Event()
        async def stalled(*args,**kwargs):
            try:await asyncio.Event().wait()
            finally:cancelled.set()
        client=AsyncMock();client.post.side_effect=stalled
        with patch('app.services.ai.vision_analyzer.httpx.AsyncClient') as factory, \
             patch('app.services.ai.vision_analyzer.settings.AI_VISION_TIMEOUT',.02):
            factory.return_value.__aenter__.return_value=client
            started=time.monotonic()
            with self.assertRaises(AITimeoutError):
                await VisionAnalyzerService._call_antigravity('','test','test-token',
                    'ag/gemini-3.8-flash-high',project_id='test-project')
        self.assertTrue(cancelled.is_set())
        self.assertLess(time.monotonic()-started,.5)
        self.assertEqual(client.post.await_count,1)

    async def test_interrupted_response_retries_only_that_read_with_same_model_and_request_id(self):
        response=httpx.Response(200,json={'candidates':[{'content':{'parts':[{'text':'ok'}]}}]},
            request=httpx.Request('POST','https://example.test'))
        client=AsyncMock();client.post.side_effect=[httpx.ReadError('interrupted'),response]
        with patch('app.services.ai.vision_analyzer.httpx.AsyncClient') as factory, \
             patch('app.services.ai.vision_analyzer.asyncio.sleep',AsyncMock()):
            factory.return_value.__aenter__.return_value=client
            result=await VisionAnalyzerService._call_antigravity('','test','test-token',
                'ag/gemini-3.8-flash-high',project_id='test-project')
        self.assertEqual(result,'ok')
        self.assertEqual(client.post.await_count,2)
        first,second=[args.kwargs['json'] for args in client.post.await_args_list]
        self.assertEqual(first['model'],'gemini-3.8-flash-high')
        self.assertEqual(first['requestId'],second['requestId'])

    async def test_transport_retry_is_bounded(self):
        client=AsyncMock();client.post.side_effect=httpx.ReadError('interrupted')
        with patch('app.services.ai.vision_analyzer.httpx.AsyncClient') as factory, \
             patch('app.services.ai.vision_analyzer.asyncio.sleep',AsyncMock()):
            factory.return_value.__aenter__.return_value=client
            with self.assertRaises(AIVisionError):
                await VisionAnalyzerService._call_antigravity('','test','test-token',
                    'ag/gemini-3.8-flash-high',project_id='test-project')
        self.assertEqual(client.post.await_count,2)

    def test_native_ids_are_preserved(self):
        for model in ('gemini-3.8-flash-high', 'claude-opus-4-6', 'gpt-oss-120b-medium'):
            self.assertEqual(normalize_antigravity_model('ag/' + model), model)
        with self.assertRaises(AIVisionError):
            normalize_antigravity_model('')

    async def test_outbound_payload_uses_exact_model(self):
        response = httpx.Response(200, json={'candidates':[{'content':{'parts':[{'text':'ok'}]}}]}, request=httpx.Request('POST','https://example.test'))
        client = AsyncMock()
        client.post.return_value = response
        with patch('app.services.ai.vision_analyzer.httpx.AsyncClient') as factory:
            factory.return_value.__aenter__.return_value = client
            result = await VisionAnalyzerService._call_antigravity('', 'test', 'test-token', 'ag/gemini-3.8-flash-high', project_id='test-project')
        self.assertEqual(result, 'ok')
        self.assertEqual(client.post.call_args.kwargs['json']['model'], 'gemini-3.8-flash-high')

    async def test_pool_does_not_use_other_configured_models_after_failure(self):
        def connection(i, model):
            return SimpleNamespace(id=i, provider='antigravity', selected_model=model,
                                   name='test', priority=i, quotas={}, api_key='test-token')
        connections=[connection(1,'ag/gemini-3.8-flash-high'),connection(2,'ag/gemini-2.5-flash')]
        db=MagicMock()
        result=MagicMock()
        result.scalars.return_value.all.return_value=[]
        db.execute=AsyncMock(return_value=result)
        call=AsyncMock(side_effect=AIRateLimitError('429', {}))
        with patch.object(ConnectionPoolService,'_record_connection_error',AsyncMock()), patch('app.services.ai.connection_pool.TokenRefreshService.get_active_token',AsyncMock(return_value='test-token')):
            with self.assertRaises(AIVisionError):
                await ConnectionPoolService.call_with_fallback(db,connections,call)
        self.assertEqual(call.await_count,1)
        self.assertEqual(call.await_args.kwargs['model'],'ag/gemini-3.8-flash-high')

    async def test_pool_can_fail_over_to_another_account_on_same_model(self):
        model='ag/gemini-3.8-flash-high'
        connections=[SimpleNamespace(id=i, provider='antigravity', selected_model=model,
                                     name='test', priority=i, quotas={}, api_key='test-token') for i in (1,2)]
        db=MagicMock();result=MagicMock();result.scalars.return_value.all.return_value=[]
        db.execute=AsyncMock(return_value=result)
        call=AsyncMock(side_effect=[AIRateLimitError('429', {}),'ok'])
        with patch.object(ConnectionPoolService,'_record_connection_error',AsyncMock()), patch('app.services.ai.connection_pool.TokenRefreshService.get_active_token',AsyncMock(return_value='test-token')):
            response,connection=await ConnectionPoolService.call_with_fallback(db,connections,call)
        self.assertEqual(response,'ok')
        self.assertEqual(connection.id,2)
        self.assertEqual([a.kwargs['model'] for a in call.await_args_list],[model,model])
