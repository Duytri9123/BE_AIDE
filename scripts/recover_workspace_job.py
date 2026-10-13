"""Recover a finished worker job's stale progress through the queue service."""
import asyncio
from app.services import job_queue


async def main():
    with job_queue.sync_client() as client:
        job=client.get(job_queue.PREFIX+'project:16')
        info=client.hgetall(job_queue.PREFIX+job) if job else None
    if info:
        recovered=await job_queue.refresh_terminal_job(job,info)
        print('Workspace 16 job state:',recovered['status'])
    else: print('Workspace 16 has no active job slot.')


if __name__=='__main__': asyncio.run(main())
