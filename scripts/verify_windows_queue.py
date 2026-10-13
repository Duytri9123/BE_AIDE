"""Actual Windows solo worker + API + one AI fixture, isolated SQLite and Redis."""
import asyncio
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
import httpx
import redis

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'tmp'/'queue_fix_verification'


async def main():
    OUT.mkdir(parents=True,exist_ok=True)
    os.chdir(ROOT);sys.path.insert(0,str(ROOT))
    from app.core.security import create_access_token
    source=sqlite3.connect(ROOT/'webbaogia.db')
    snapshot=sqlite3.connect(OUT/'snapshot.sqlite')
    source.backup(snapshot);source.close()
    row=snapshot.execute('SELECT p.user_id,p.id,f.id FROM projects p JOIN project_files f ON f.project_id=p.id WHERE f.filename=? ORDER BY f.id DESC LIMIT 1',('owner_load_test_sld.dxf',)).fetchone()
    if row is None:raise RuntimeError('Owner fixture missing')
    uid,pid,fid=row
    other=snapshot.execute('SELECT id FROM users WHERE status=? AND id!=? LIMIT 1',('active',uid)).fetchone()[0]
    admin=snapshot.execute("SELECT id FROM users WHERE status='active' AND role='admin' LIMIT 1").fetchone()[0]
    snapshot.close()
    url=None
    for index in (14,15):
        candidate=f'redis://127.0.0.1:6379/{index}'
        with redis.Redis.from_url(candidate) as c:
            if c.dbsize()==0:url=candidate;break
    if url is None:raise RuntimeError('No empty isolated Redis DB; refusing to touch existing queues')
    env=os.environ.copy()
    env.update({'PYTHONUTF8':'1','DATABASE_URL':'sqlite+aiosqlite:///'+(OUT/'snapshot.sqlite').as_posix(),
                'REDIS_URL':url,'CELERY_BROKER_URL':url,'CELERY_RESULT_BACKEND':url,
                'PROJECTS_DIR':str(OUT/'projects'),'EXPORTS_DIR':str(OUT/'exports'),
                'QUEUE_ANALYSIS_ENABLED':'true'})
    report={'redis_db':url.rsplit('/',1)[-1],'project_id':pid,'checks':{}}
    processes=[]
    with (OUT/'worker.log').open('w',encoding='utf-8') as workerlog,(OUT/'api.log').open('w',encoding='utf-8') as apilog:
        try:
            worker=subprocess.Popen([sys.executable,'-m','celery','-A','app.tasks.celery_app','worker',
                '--pool=solo','--concurrency=1','--queues=aide_analysis,aide_cad','--loglevel=INFO',
                '--without-gossip','--without-mingle'],cwd=ROOT,env=env,stdout=workerlog,stderr=workerlog)
            processes.append(worker)
            server=subprocess.Popen([sys.executable,'-m','uvicorn','app.main:app','--port','18081',
                '--host','127.0.0.1','--no-access-log'],cwd=ROOT,env=env,stdout=apilog,stderr=apilog)
            processes.append(server)
            with redis.Redis.from_url(url) as cache:
                for _ in range(40):
                    if worker.poll() is not None:raise RuntimeError('Worker startup failed')
                    if cache.exists('aide:jobs:worker-ready'):break
                    await asyncio.sleep(1)
                else:raise RuntimeError('Worker heartbeat missing')
            async with httpx.AsyncClient(base_url='http://127.0.0.1:18081',timeout=10,
                    headers={'Authorization':'Bearer '+create_access_token(uid)},trust_env=False) as client:
                for _ in range(30):
                    try:
                        if (await client.get('/health')).status_code==200:break
                    except httpx.HTTPError:pass
                    await asyncio.sleep(1)
                r=await client.post('/api/v1/analyze/async-start',json={'project_id':pid,'file_id':fid,'is_new_session':True})
                r.raise_for_status();job=r.json()['task_id'];report['analysis_job']=job
                duplicate=await client.post('/api/v1/analyze/async-start',json={'project_id':pid,'file_id':fid})
                report['checks']['duplicate_409']=duplicate.status_code==409
                denied=await client.get('/api/v1/analyze/task/'+job,headers={'Authorization':'Bearer '+create_access_token(other)})
                report['checks']['other_owner_404']=denied.status_code==404
                unknown=await client.get('/api/v1/analyze/task/unknown')
                report['checks']['unknown_job_404']=unknown.status_code==404
                samples=[];started=time.perf_counter()
                result=None
                for _ in range(90):
                    t=time.perf_counter();h=await client.get('/health');samples.append((time.perf_counter()-t)*1000)
                    r=await client.get('/api/v1/analyze/task/'+job);r.raise_for_status();state=r.json()
                    if state['status']=='SUCCESS':result=state['result'];break
                    if state['status'] in ('FAILURE','CANCELLED'):raise RuntimeError('Analysis failed: '+state.get('error',''))
                    await asyncio.sleep(2)
                if result is None:raise RuntimeError('Analysis deadline exceeded')
                report['analysis_seconds']=round(time.perf_counter()-started,2)
                report['analysis_devices']=[{'category':d['category'],'tag':d.get('tag'),'quantity':d['quantity']} for d in result['devices']]
                report['checks']['quantity_three']=sum(d['quantity'] for d in result['devices'])==3
                report['checks']['distinct_tags']=set(d.get('tag') for d in result['devices'])=={'QF1','QF2','QF3'}
                report['health_max_ms']=round(max(samples),1)
                (OUT/'analysis.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
                await asyncio.sleep(1)
                started=time.perf_counter()
                async with client.stream('POST','/api/v1/analyze/generate-quotation-cad/stream',json={
                    'project_id':pid,'devices':result['devices'],'enclosure_dimensions':'800x600x250',
                    'panel_code':'TEST-LT','brand_preference':'Schneider'},timeout=120) as stream:
                    stream.raise_for_status();report['checks']['sse_task_header']=bool(stream.headers.get('x-task-id'))
                    final=None
                    async for line in stream.aiter_lines():
                        if not line.startswith('data: '):continue
                        event=json.loads(line[6:])
                        if event.get('type')=='complete':final=event['result']
                        if event.get('type')=='error':raise RuntimeError('CAD worker failed: '+event.get('detail',''))
                report['cad_seconds']=round(time.perf_counter()-started,2)
                report['checks']['honest_cad_review']=final['cad_status']=='needs_review' and final['success'] is False and final['cad_file'] is None and bool(final['cad_blockers'])
                report['checks']['excel_created']=bool(final['quotation_file']) and Path(final['quotation_file']['file_path']).is_file()
                (OUT/'cad.json').write_text(json.dumps(final,ensure_ascii=False,indent=2),encoding='utf-8')
                t=time.perf_counter();r=await client.get('/api/v1/device-library/models?limit=50',timeout=30,
                     headers={'Authorization':'Bearer '+create_access_token(admin)})
                report['models_50_seconds']=round(time.perf_counter()-t,2)
                report['models_50_status']=r.status_code
                report['checks']['models_50_ok']=r.status_code==200 and len(r.json())==50
                with redis.Redis.from_url(url) as cache:
                    report['checks']['slots_released']=cache.zcard('aide:jobs:slots')==0
                print(json.dumps(report,ensure_ascii=True),flush=True)
                if not all(report['checks'].values()):raise AssertionError('One or more integration checks failed')
        finally:
            for process in reversed(processes):
                process.terminate()
                try:process.wait(timeout=10)
                except subprocess.TimeoutExpired:process.kill();process.wait()
            with redis.Redis.from_url(url) as cache:
                owned=list(cache.scan_iter(match='aide:jobs:*'))+list(cache.scan_iter(match='celery-task-meta-*'))
                owned += [b'aide_analysis',b'aide_cad',b'_kombu.binding.aide_analysis',b'_kombu.binding.aide_cad',b'_kombu.binding.celeryev',b'_kombu.binding.celery.pidbox']
                if owned:cache.delete(*owned)
            (OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__':asyncio.run(main())
