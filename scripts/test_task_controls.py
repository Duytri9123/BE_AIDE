"""Exercise the HTTP control routes against isolated jobs in the local Redis."""
import asyncio
import threading
import unittest
from types import SimpleNamespace
from uuid import uuid4
from fastapi import FastAPI
import httpx
from app.api.deps import get_current_active_user
from app.api.v1.endpoints.task_control import router
from app.services import job_queue


class TaskControlHttpTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.job='test-control-'+uuid4().hex
        self.project='test-project-'+uuid4().hex
        self.owner=123456789
        self.app=FastAPI()
        self.app.include_router(router,prefix='/analyze')
        self.app.dependency_overrides[get_current_active_user]=lambda:SimpleNamespace(id=self.owner)
        with job_queue.sync_client() as client:
            client.hset(job_queue.PREFIX+self.job,mapping={'project_id':self.project,
                'user_id':str(self.owner),'kind':'analysis','status':'PROGRESS','progress':'20'})
            client.expire(job_queue.PREFIX+self.job,60)
        self.http=httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app),base_url='http://test')

    async def asyncTearDown(self):
        await self.http.aclose()
        with job_queue.sync_client() as client:
            client.hset(job_queue.PREFIX+self.job,'pause_requested','0')
            client.delete(job_queue.PREFIX+self.job,job_queue.PREFIX+self.job+':events')
            client.zrem(job_queue.PREFIX+'slots',self.job)

    async def test_pause_and_resume_keep_the_same_job(self):
        response=await self.http.post('/analyze/task/'+self.job+'/pause')
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['status'],'PAUSING')
        done=threading.Event()
        thread=threading.Thread(target=lambda:(job_queue.control_point(self.job),done.set()),daemon=True)
        thread.start()
        try:
            for _ in range(30):
                with job_queue.sync_client() as client:
                    if client.hget(job_queue.PREFIX+self.job,'status')=='PAUSED':break
                await asyncio.sleep(.1)
            else:self.fail('Worker control point never paused')
            self.assertFalse(done.is_set())
            response=await self.http.post('/analyze/task/'+self.job+'/resume')
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.json()['task_id'],self.job)
            await asyncio.to_thread(thread.join,3)
            self.assertTrue(done.is_set())
            with job_queue.sync_client() as client:
                self.assertEqual(client.hget(job_queue.PREFIX+self.job,'status'),'PROGRESS')
        finally:
            with job_queue.sync_client() as client:client.hset(job_queue.PREFIX+self.job,'pause_requested','0')
            await asyncio.to_thread(thread.join,3)

    async def test_other_owner_cannot_control_job(self):
        self.app.dependency_overrides[get_current_active_user]=lambda:SimpleNamespace(id=42)
        response=await self.http.post('/analyze/task/'+self.job+'/pause')
        self.assertEqual(response.status_code,404)

    async def test_completed_job_rejects_resume(self):
        with job_queue.sync_client() as client:client.hset(job_queue.PREFIX+self.job,'status','SUCCESS')
        response=await self.http.post('/analyze/task/'+self.job+'/resume')
        self.assertEqual(response.status_code,409)


if __name__=='__main__':unittest.main()
