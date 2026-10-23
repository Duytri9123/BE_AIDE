"""Project chat integration tests against an isolated database and provider stub."""
import json
import uuid
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
from fastapi import FastAPI
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

import app.models
from app.models.base import Base
from app.models.user import User
from app.models.project import Project
from app.models.conversation_session import ConversationSession
from app.models.analysis_iteration import AnalysisIteration
from app.api.v1.endpoints.chat import router
from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.services.ai.project_chat import parse_plan, apply_plan


class ProjectChatTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine('sqlite+aiosqlite:///:memory:')
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.db = async_sessionmaker(self.engine, expire_on_commit=False)()
        self.user = User(id=1, email='chat@test.invalid', hashed_password='unused')
        self.db.add_all([self.user, User(id=2, email='other@test.invalid', hashed_password='unused')])
        await self.db.flush()
        self.db.add_all([Project(id=1, user_id=1, name='Chat fixture'), Project(id=2, user_id=2, name='Other')])
        await self.db.flush()
        self.session = ConversationSession(id=uuid.uuid4(), project_id=1, user_id=1, total_iterations=1)
        self.db.add(self.session)
        await self.db.flush()
        self.devices = [{'category':'MCCB','name':'MCCB 100A','spec':'100A','in_a':100,
            'quantity':1,'brand':'Schneider','part_number':'OLD-SKU','panel_code':'DB1',
            'source_filename':'drawing.pdf','source_page':2,'box_2d':[1,2,30,40],
            'selected_product':{'sku':'OLD-SKU','price':100},'catalog_matches':{'old':1}}]
        self.source = AnalysisIteration(session_id=self.session.id, iteration_number=1,
            trigger_type='extraction', status='completed', ai_parsed_devices=self.devices,
            files_analyzed={'file_names':['drawing.pdf']}, confidence_scores={
                'panels':[{'panel_code':'DB1','panel_name':'DB1','devices':self.devices}],
                'design_result':{'cad_file':{'id':10}},'quotation_rows':[{'price':100}]})
        self.db.add(self.source)
        await self.db.commit()
        self.app = FastAPI()
        self.app.include_router(router, prefix='/chat')
        async def database(): yield self.db
        self.app.dependency_overrides[get_db] = database
        self.app.dependency_overrides[get_current_active_user] = lambda: self.user
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url='http://test')
        self.pool = patch('app.api.v1.endpoints.chat.ConnectionPoolService.get_ordered_connections',
            new=AsyncMock(return_value=[SimpleNamespace(id=1)]))
        self.inference = patch('app.api.v1.endpoints.chat.ConnectionPoolService.call_with_fallback', new=AsyncMock())
        self.pool_mock = self.pool.start()
        self.ai = self.inference.start()
        self.ai.return_value = (json.dumps({'reply':'Xin chào.','operations':[]}), None)

    async def asyncTearDown(self):
        self.inference.stop()
        self.pool.stop()
        await self.client.aclose()
        await self.db.close()
        await self.engine.dispose()

    def payload(self, message='thay bằng hãng LS giúp tôi nhé', **extra):
        return {'project_id':1,'message':message,'request_id':str(uuid.uuid4()),
            'current_devices':self.devices, 'context':{'iteration_id':self.source.id,'messages':[]}, **extra}

    def plan(self, operations, reply='Đã điều chỉnh theo yêu cầu.'):
        self.ai.return_value = (json.dumps({'reply':reply,'operations':operations}), None)

    async def count(self):
        return (await self.db.execute(select(func.count(AnalysisIteration.id)))).scalar_one()

    async def test_brand_change_persists_and_preserves_evidence(self):
        self.plan([{'op':'update','index':0,'changes':{'brand':'LS'}}])
        response = await self.client.post('/chat/', json=self.payload())
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertEqual(result['action_type'], 'update_devices')
        self.assertNotEqual(result['iteration_id'], self.source.id)
        device = result['devices'][0]
        self.assertEqual(device['brand'], 'LS')
        self.assertEqual(device['source_filename'], 'drawing.pdf')
        self.assertEqual(device['box_2d'], [1,2,30,40])
        self.assertNotIn('selected_product', device)
        self.assertNotIn('part_number', device)
        await self.db.refresh(self.source)
        self.assertEqual(self.source.ai_parsed_devices[0]['brand'], 'Schneider')
        saved = await self.db.get(AnalysisIteration, result['iteration_id'])
        self.assertEqual(saved.ai_parsed_devices[0]['brand'], 'LS')
        self.assertEqual(saved.files_analyzed, self.source.files_analyzed)
        self.assertNotIn('quotation_rows', saved.confidence_scores)
        self.assertIsNone(saved.confidence_scores['design_result']['cad_file'])

    async def test_add_one_and_followup_receive_latest_snapshot_and_history(self):
        self.plan([{'op':'add','changes':{'category':'MCCB','name':'MCCB 100A','spec':'100A','in_a':100,'quantity':1}}])
        first = (await self.client.post('/chat/', json=self.payload('Thêm một MCCB 100A'))).json()
        self.assertEqual(len(first['devices']), 2)
        self.assertEqual(first['devices'][1]['quantity'], 1)
        self.plan([{'op':'update','index':1,'changes':{'brand':'LS'}}])
        history = [{'role':'user','content':'Thêm một MCCB 100A'}, {'role':'assistant','content':first['reply']}]
        second = await self.client.post('/chat/', json=self.payload('Đổi cái vừa thêm sang LS',
            current_devices=first['devices'], context={'iteration_id':first['iteration_id'],'messages':history}))
        self.assertEqual(second.status_code, 200, second.text)
        self.assertEqual(second.json()['devices'][1]['brand'], 'LS')
        self.assertEqual(second.json()['devices'][0]['brand'], 'Schneider')
        prompt = self.ai.call_args.kwargs['prompt']
        self.assertIn('Thêm một MCCB 100A', prompt)
        self.assertIn('Đổi cái vừa thêm sang LS', prompt)

    async def test_greeting_empty_does_not_create_devices(self):
        response = await self.client.post('/chat/', json=self.payload('Xin chào', current_devices=[], context={}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['action_type'], 'general_chat')
        self.assertIsNone(response.json()['devices'])
        self.assertEqual(await self.count(), 1)

    async def test_question_is_readonly(self):
        await self.client.post('/chat/', json=self.payload('Có bao nhiêu thiết bị?'))
        self.assertEqual(await self.count(), 1)

    async def test_retry_is_idempotent(self):
        self.plan([{'op':'add','changes':{'category':'MCCB','name':'MCCB 100A'}}])
        payload = self.payload('Thêm một MCCB 100A')
        first = await self.client.post('/chat/', json=payload)
        second = await self.client.post('/chat/', json=payload)
        self.assertEqual(first.json(), second.json())
        self.assertEqual(await self.count(), 2)
        self.assertEqual(self.ai.await_count, 1)

    async def test_remove_last_device_stays_empty(self):
        self.plan([{'op':'remove','index':0}])
        response = await self.client.post('/chat/', json=self.payload('Xóa MCCB này'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['devices'], [])
        saved = await self.db.get(AnalysisIteration, response.json()['iteration_id'])
        self.assertEqual(saved.confidence_scores['panels'][0]['devices'], [])
        from app.services.analysis_reads import latest_analysis
        _, latest, _ = await latest_analysis(self.db, 1, self.user)
        self.assertEqual(latest.id, saved.id)
        self.assertEqual(latest.ai_parsed_devices, [])

    async def test_invalid_response_never_saves(self):
        for operations in ([{'op':'update','index':99,'changes':{'brand':'LS'}}],
            [{'op':'update','index':0,'changes':{'quantity':0}}],
            [{'op':'update','index':0,'changes':{'unit_price':12}}]):
            self.plan(operations)
            response = await self.client.post('/chat/', json=self.payload())
            self.assertEqual(response.status_code, 502)
        self.ai.return_value = ('not json', None)
        self.assertEqual((await self.client.post('/chat/', json=self.payload())).status_code, 502)
        self.assertEqual(await self.count(), 1)

    async def test_provider_failure_never_claims_success(self):
        self.ai.side_effect = RuntimeError('provider failed')
        response = await self.client.post('/chat/', json=self.payload())
        self.assertEqual(response.status_code, 502)
        self.assertEqual(await self.count(), 1)

    async def test_no_provider_is_actionable_error(self):
        self.pool_mock.return_value = []
        self.assertEqual((await self.client.post('/chat/', json=self.payload())).status_code, 503)
        self.ai.assert_not_awaited()

    async def test_other_project_and_iteration_are_rejected(self):
        self.assertEqual((await self.client.post('/chat/', json=self.payload(project_id=2))).status_code, 404)
        self.assertEqual((await self.client.post('/chat/', json=self.payload(context={'iteration_id':999}))).status_code, 404)
        self.ai.assert_not_awaited()

    async def test_new_chat_can_add_without_extraction(self):
        self.db.add(Project(id=3, user_id=1, name='Empty'))
        await self.db.commit()
        self.plan([{'op':'add','changes':{'category':'MCB','name':'MCB 20A','in_a':20}}])
        response = await self.client.post('/chat/', json=self.payload('Thêm một MCB 20A', project_id=3,
            current_devices=[], context={}))
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(len(response.json()['devices']), 1)
        self.assertEqual(response.json()['devices'][0]['quantity'], 1)

    async def test_editing_older_session_is_restored_as_latest(self):
        newer = ConversationSession(id=uuid.uuid4(), project_id=1, user_id=1, total_iterations=1)
        self.db.add(newer)
        await self.db.flush()
        self.db.add(AnalysisIteration(session_id=newer.id, iteration_number=1,
            trigger_type='extraction',status='completed',ai_parsed_devices=self.devices))
        await self.db.commit()
        self.plan([{'op':'update','index':0,'changes':{'brand':'LS'}}])
        response = await self.client.post('/chat/', json=self.payload())
        self.assertEqual(response.status_code, 200)
        from app.services.analysis_reads import latest_analysis
        _, latest, _ = await latest_analysis(self.db, 1, self.user)
        self.assertEqual(latest.id, response.json()['iteration_id'])

    async def test_flat_provider_operations_are_normalized_safely(self):
        self.plan([{'op':'add','category':'MCCB','name':'MCCB 100A','quantity':1}])
        response = await self.client.post('/chat/', json=self.payload('Thêm một MCCB 100A'))
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(len(response.json()['devices']), 2)
        self.assertEqual(response.json()['devices'][-1]['quantity'], 1)

    async def test_anonymous_rejected(self):
        self.app.dependency_overrides.pop(get_current_active_user)
        self.assertEqual((await self.client.post('/chat/', json=self.payload())).status_code, 401)


if __name__ == '__main__':
    unittest.main()
