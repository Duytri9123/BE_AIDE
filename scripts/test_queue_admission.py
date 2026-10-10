"""Redis admission/ownership/cancellation, isolated namespace and no dispatched AI."""
import asyncio
import json
from pathlib import Path
import sys
import uuid
from unittest.mock import Mock,patch
from fastapi import HTTPException
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.services import job_queue as jobs
from app.tasks.worker_tasks import analyze_project_async_task


async def main():
    prefix='aide:test:'+uuid.uuid4().hex+':'
    checks={}
    with patch.object(jobs,'PREFIX',prefix),patch.object(jobs,'READY_KEY',prefix+'ready'),\
         patch.object(jobs.settings,'ANALYSIS_MAX_PENDING_JOBS',1),\
         patch.object(analyze_project_async_task,'apply_async',Mock()) as submit:
        async def expect_status(call,status):
            try:await call
            except HTTPException as e:assert e.status_code==status;return True
            raise AssertionError('Expected rejection')
        try:
            checks['missing_worker_503']=await expect_status(jobs.enqueue('analysis',1,1,{}),503)
            with jobs.sync_client() as c:c.set(jobs.READY_KEY,'1',ex=60)
            job=await jobs.enqueue('analysis',1,1,{})
            checks['duplicate_409']=await expect_status(jobs.enqueue('analysis',1,1,{}),409)
            checks['queue_full_429']=await expect_status(jobs.enqueue('analysis',2,1,{}),429)
            checks['owner_404']=await expect_status(jobs.owned_job(job,2),404)
            info=await jobs.owned_job(job,1);assert info['status']=='PENDING'
            with jobs.sync_client() as c:c.hset(prefix+job,'cancel_requested','1')
            assert jobs.cancelled(job)
            jobs.publish(job,{'type':'error','detail':'cancelled'},'CANCELLED')
            jobs.release(job,1)
            checks['cancel_releases_slot']=True
            submit.side_effect=RuntimeError('broker unavailable')
            checks['broker_error_503']=await expect_status(jobs.enqueue('analysis',2,1,{}),503)
            with jobs.sync_client() as c:
                checks['broker_failure_releases_slot']=c.zcard(prefix+'slots')==0 and not c.exists(prefix+'project:2')
            assert all(checks.values())
            print(json.dumps(checks))
        finally:
            with jobs.sync_client() as c:
                keys=list(c.scan_iter(match=prefix+'*'))
                if keys:c.delete(*keys)


if __name__=='__main__':asyncio.run(main())
