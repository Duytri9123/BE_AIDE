import asyncio
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from fastapi import HTTPException
from app.services.ai.el_progress import progress_events, run_step, progress_scope


def decode(frame):
    return json.loads(frame.removeprefix('data: ').strip())

class ElProgressTests(unittest.IsolatedAsyncioTestCase):
    async def test_reports_running_before_work_finishes_with_actual_panel_and_devices(self):
        gate=asyncio.Event()
        async def read():
            await gate.wait()
            return {'devices':3}
        async def operation():
            with progress_scope('Tủ TĐ-30.A · nguồn.dwg'):
                return await run_step('Đang kiểm ảnh L4, L5',read())
        events=progress_events(operation)
        first=decode(await anext(events))
        self.assertEqual(first['activity']['state'],'running')
        self.assertIn('TĐ-30.A',first['activity']['detail'])
        self.assertIn('L4, L5',first['activity']['label'])
        self.assertNotIn('progress',first['activity'])
        gate.set()
        done=decode(await anext(events));result=decode(await anext(events))
        self.assertEqual(first['activity']['id'],done['activity']['id'])
        self.assertEqual(done['activity']['state'],'success')
        self.assertEqual(result['result'],{'devices':3})
        await events.aclose()

    async def test_parallel_requests_have_separate_activities_and_nested_context(self):
        async def collect(panel):
            async def work():
                with progress_scope(panel):
                    return await run_step('Kiểm nhánh',run_step('Gọi model',asyncio.sleep(0,result=panel)))
            return [decode(e) async for e in progress_events(work)]
        a,b=await asyncio.gather(collect('Tủ A'),collect('Tủ B'))
        for frames,panel,other in ((a,'Tủ A','Tủ B'),(b,'Tủ B','Tủ A')):
            acts=[e['activity'] for e in frames if e['type']=='activity']
            self.assertTrue(all(panel in e['detail'] and other not in e['detail'] for e in acts))
            self.assertIn('Kiểm nhánh',next(e['detail'] for e in acts if e['label']=='Gọi model'))

    async def test_no_elapsed_cutoff_at_150_seconds(self):
        clock=iter([0,151])
        async def work(): return await run_step('Đọc nguồn',asyncio.sleep(0,result='xong'))
        with patch('app.services.ai.el_progress.time',SimpleNamespace(monotonic=lambda:next(clock))):
            frames=[decode(e) async for e in progress_events(work)]
        self.assertEqual(frames[-1]['result'],'xong')
        self.assertIn('151.0',frames[-2]['activity']['detail'])

    async def test_heartbeat_does_not_create_fake_activity_and_disconnect_cancels(self):
        stopped=asyncio.Event()
        async def wait():
            try: await asyncio.Event().wait()
            finally: stopped.set()
        events=progress_events(wait,heartbeat=.01)
        self.assertEqual(await anext(events),': keepalive\n\n')
        await events.aclose()
        self.assertTrue(stopped.is_set())

    async def test_failure_is_terminal_not_completion(self):
        async def bad():raise HTTPException(422,'Chưa đủ căn cứ L4')
        async def work():return await run_step('Kiểm L4',bad())
        frames=[decode(e) async for e in progress_events(work)]
        self.assertEqual(frames[-2]['activity']['state'],'error')
        self.assertEqual(frames[-1]['status'],422)
        self.assertNotIn('complete',[e['type'] for e in frames])

class ElProgressRouteTests(unittest.IsolatedAsyncioTestCase):
    async def test_stream_route_authenticates_and_uses_its_own_session(self):
        import httpx
        from contextlib import asynccontextmanager
        from unittest.mock import AsyncMock
        from fastapi import FastAPI
        from app.api.v1.endpoints import el_agent
        app=FastAPI();app.include_router(el_agent.router,prefix='/el')
        app.dependency_overrides[el_agent.get_db]=lambda: 'request-session'
        app.dependency_overrides[el_agent.get_current_active_user]=lambda: SimpleNamespace(id=7)
        closed=[]
        @asynccontextmanager
        async def session():
            try:yield 'stream-session'
            finally:closed.append(True)
        async def next_action(payload,request,db,user):
            self.assertEqual(db,'stream-session')
            return await run_step('Đang đọc tủ thử nghiệm',asyncio.sleep(0,result={'reply':'xong'}))
        with patch.object(el_agent,'owned_project',new=AsyncMock()),patch.object(el_agent,'next_action',new=next_action),patch('app.db.session.AsyncSessionLocal',session):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
                response=await client.post('/el/next/stream',json={'project_id':30,'message':'bóc tủ A'})
        self.assertEqual(response.status_code,200)
        frames=[decode(line) for line in response.text.split('\n') if line.startswith('data:')]
        self.assertEqual([f['type'] for f in frames],['activity','activity','complete'])
        self.assertEqual(response.headers['x-accel-buffering'],'no')
        self.assertTrue(closed)
        with patch.object(el_agent,'owned_project',new=AsyncMock(side_effect=HTTPException(404,'Không thuộc dự án'))),patch.object(el_agent,'next_action',new=AsyncMock()) as action:
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
                denied=await client.post('/el/next/stream',json={'project_id':99,'message':'hi'})
            self.assertEqual(denied.status_code,404);action.assert_not_awaited()

class ElEvidenceRetryTests(unittest.IsolatedAsyncioTestCase):
    async def test_missing_pixel_evidence_does_not_repeat_whole_panel_extraction(self):
        from types import SimpleNamespace
        from unittest.mock import AsyncMock
        from app.api.v1.endpoints import el_agent
        from app.schemas.ai import ChatRequest
        panel={'panel_code':'MDB','source_file_id':126,'source_page':None,'source_region':[0,0,1,1]}
        with patch.object(el_agent,'owned_project',new=AsyncMock()), \
             patch('app.services.ai.takeoff_regions.confirmed_scope',return_value=[panel]), \
             patch('app.services.ai.scoped_takeoff.extract_confirmed_panels',new=AsyncMock(return_value=[])) as extraction, \
             patch.object(el_agent,'format_reply_response',new=AsyncMock(return_value={'verification_kind':'device_evidence','verification_feedback':'Thiếu ảnh L4'})):
            response=await el_agent.next_action(ChatRequest(project_id=42,message='bóc tách MDB',context={'file_ids':[126]}),SimpleNamespace(),SimpleNamespace(),SimpleNamespace(id=23))
        self.assertEqual(extraction.await_count,1)
        self.assertEqual(response['processing_status'],'needs_review')
        self.assertIn('L4',response['reply'])

if __name__=='__main__':unittest.main()
