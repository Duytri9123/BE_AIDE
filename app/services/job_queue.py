"""Bounded owner-scoped jobs, shared by the API and Windows solo worker."""
import asyncio
import json
import time
import uuid

from fastapi import HTTPException
import redis
import redis.asyncio as async_redis

from app.core.config import settings

PREFIX = 'aide:jobs:'
READY_KEY = PREFIX + 'worker-ready'
ADMIT = """
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', ARGV[1])
if redis.call('EXISTS', KEYS[2]) == 1 then return -1 end
if redis.call('ZCARD', KEYS[1]) >= tonumber(ARGV[2]) then return -2 end
redis.call('SET', KEYS[2], ARGV[3], 'EX', ARGV[4])
redis.call('ZADD', KEYS[1], tonumber(ARGV[1])+tonumber(ARGV[4]), ARGV[3])
redis.call('HSET', KEYS[3], 'user_id', ARGV[5], 'project_id', ARGV[6],
 'status', 'PENDING', 'kind', ARGV[7])
redis.call('EXPIRE', KEYS[3], ARGV[4])
return 1
"""
RELEASE = """
if redis.call('GET', KEYS[2]) == ARGV[1] then redis.call('DEL', KEYS[2]) end
redis.call('ZREM', KEYS[1], ARGV[1])
"""


def sync_client():
    return redis.Redis.from_url(settings.REDIS_URL, decode_responses=True,
                               socket_connect_timeout=10, socket_timeout=10)


def publish(job_id, event, status='PROGRESS', result=None):
    """Worker callback. Progress never exposes provider credentials."""
    with sync_client() as client:
        pipe = client.pipeline()
        pipe.hset(PREFIX+job_id, mapping={'status':status, 'stage':event.get('stage',''),
                  'progress':str(event.get('progress',0)),
                  'detail':str(event.get('detail') or ''), 'event_status':str(event.get('status') or 'running'),
                  'message':event.get('message') or event.get('title') or ''})
        if result is not None:
            pipe.hset(PREFIX+job_id, 'result', json.dumps(result, ensure_ascii=False))
        pipe.rpush(PREFIX+job_id+':events', json.dumps(event, ensure_ascii=False))
        pipe.expire(PREFIX+job_id, settings.ANALYSIS_JOB_TTL_SECONDS)
        pipe.expire(PREFIX+job_id+':events', settings.ANALYSIS_JOB_TTL_SECONDS)
        pipe.execute()


def release(job_id, project_id):
    with sync_client() as client:
        client.eval(RELEASE,2,PREFIX+'slots',PREFIX+f'project:{project_id}',job_id)


def cancelled(job_id):
    with sync_client() as client:
        return (client.hget(PREFIX+job_id,'cancel_requested') == '1'
                or client.hget(PREFIX+job_id,'status') == 'CANCELLED')


class JobCancelled(BaseException):
    """Must propagate through optional progress callbacks that catch Exception."""


def control_point(job_id):
    """Pause between stages without discarding the running analysis or billing twice."""
    paused=False
    while True:
        with sync_client() as client:
            info=client.hgetall(PREFIX+job_id)
            if info.get('cancel_requested')=='1' or info.get('status')=='CANCELLED':
                raise JobCancelled('Tác vụ đã bị hủy.')
            requested=info.get('pause_requested')=='1'
            if requested:
                client.expire(PREFIX+job_id,settings.ANALYSIS_JOB_TTL_SECONDS)
                client.expire(PREFIX+f"project:{info['project_id']}",settings.ANALYSIS_JOB_TTL_SECONDS)
                client.zadd(PREFIX+'slots',{job_id:time.time()+settings.ANALYSIS_JOB_TTL_SECONDS})
        if not requested:
            if paused:
                publish(job_id,{'type':'log','stage':'control','title':'Tiếp tục xử lý từ bước đã dừng','status':'running'})
            return
        if not paused:
            publish(job_id,{'type':'log','stage':'control','title':'Đã tạm dừng · Giữ tiến trình hiện tại','status':'paused',
                            'progress':int(info.get('progress') or 0)},'PAUSED')
            paused=True
        time.sleep(0.5)


async def enqueue(kind, project_id, user_id, payload):
    # Producers must not import the worker pipeline and its CAD/catalog engines.
    # Send the registered task name; only the worker loads those heavy services.
    from app.tasks.celery_app import celery_app
    client = async_redis.from_url(settings.REDIS_URL, decode_responses=True,
                                  socket_connect_timeout=10, socket_timeout=10)
    job_id = str(uuid.uuid4())
    try:
        if not await client.exists(READY_KEY):
            raise HTTPException(503,'Worker xử lý bản vẽ chưa hoạt động. Vui lòng thử lại sau.')
        admitted = await client.eval(ADMIT,3,PREFIX+'slots',PREFIX+f'project:{project_id}',
                        PREFIX+job_id,str(time.time()),settings.ANALYSIS_MAX_PENDING_JOBS,
                        job_id,settings.ANALYSIS_JOB_TTL_SECONDS,user_id,project_id,kind)
        if admitted == -1:
            raise HTTPException(409,'Dự án đang có tác vụ phân tích hoặc tạo CAD. Vui lòng chờ tác vụ đó hoàn tất.')
        if admitted == -2:
            raise HTTPException(429,'Hàng đợi đang đầy. Vui lòng thử lại sau.',headers={'Retry-After':'30'})
        task_name = ('app.tasks.worker_tasks.analyze_project_async_task' if kind == 'analysis'
                     else 'app.tasks.worker_tasks.generate_cad_async_task')
        try:
            await asyncio.to_thread(celery_app.send_task, task_name,
                kwargs={'project_id':project_id,'user_id':user_id,'payload':payload},
                task_id=job_id,queue='aide_'+kind)
        except Exception as exc:
            await client.eval(RELEASE,2,PREFIX+'slots',PREFIX+f'project:{project_id}',job_id)
            await client.delete(PREFIX+job_id)
            raise HTTPException(503,'Không gửi được tác vụ vào hàng đợi.') from exc
        return job_id
    except redis.RedisError as exc:
        raise HTTPException(503,'Không kết nối được hàng đợi xử lý.') from exc
    finally:
        await client.aclose()


async def owned_job(job_id, user_id):
    async with async_redis.from_url(settings.REDIS_URL,decode_responses=True,
                                   socket_connect_timeout=10,socket_timeout=10) as client:
        info = await client.hgetall(PREFIX+job_id)
    if not info or info.get('user_id') != str(user_id):
        raise HTTPException(404,'Không tìm thấy tác vụ của bạn.')
    info = await refresh_terminal_job(job_id, info)
    if info.get('pause_requested')=='1' and info.get('status') not in ('SUCCESS','FAILURE','CANCELLED','PAUSED'):
        info={**info,'status':'PAUSING','message':'Chờ bước AI hiện tại hoàn tất để tạm dừng.'}
    elif info.get('pause_requested')=='0' and info.get('status')=='PAUSED':
        info={**info,'status':'RESUMING','message':'Đang tiếp tục tác vụ hiện tại.'}
    return info


async def refresh_terminal_job(job_id, info):
    """Recover a terminal worker result when progress delivery lost Redis access."""
    if info.get('status') in ('SUCCESS','FAILURE','CANCELLED'):
        return info
    from app.tasks.celery_app import celery_app
    state = await asyncio.to_thread(lambda: celery_app.AsyncResult(job_id).state)
    if state not in ('FAILURE','REVOKED'):
        return info
    status = 'CANCELLED' if state == 'REVOKED' else 'FAILURE'
    event = {'type':'error','stage':info.get('kind') or '',
             'message':'Tác vụ đã dừng do lỗi xử lý hoặc kết nối. Có thể chạy lại.',
             'detail':'Tác vụ đã dừng do lỗi xử lý hoặc kết nối. Có thể chạy lại.'}
    await asyncio.to_thread(publish,job_id,event,status)
    await asyncio.to_thread(release,job_id,info['project_id'])
    return {**info,'status':status,'message':event['message']}


async def events(job_id):
    """Disconnecting a browser does not destroy an already accepted job."""
    cursor = 0
    idle_ticks = 0  # seconds since last real event
    async with async_redis.from_url(settings.REDIS_URL,decode_responses=True,
                                   socket_connect_timeout=10,socket_timeout=10) as client:
        yield 'data: '+json.dumps({'type':'log','stage':'queued','title':'Đã tiếp nhận, đang chờ xử lý','task_id':job_id},ensure_ascii=False)+'\n\n'
        while True:
            rows = await client.lrange(PREFIX+job_id+':events',cursor,-1)
            if rows:
                idle_ticks = 0
            for row in rows:
                cursor += 1
                yield 'data: '+row+'\n\n'
                if json.loads(row).get('type') in ('complete','error'):
                    return
            status = await client.hget(PREFIX+job_id,'status')
            if not rows and status not in ('SUCCESS','FAILURE','CANCELLED',None):
                info = await client.hgetall(PREFIX+job_id)
                info = await refresh_terminal_job(job_id, info)
                status = info.get('status')
            if status in ('CANCELLED','FAILURE'):
                yield 'data: '+json.dumps({'type':'error','detail':'Tác vụ đã dừng.','message':'Tác vụ đã dừng.'},ensure_ascii=False)+'\n\n'
                return
            if status is None:
                yield 'data: '+json.dumps({'type':'error','detail':'Tác vụ đã hết hạn.','message':'Tác vụ đã hết hạn.'},ensure_ascii=False)+'\n\n'
                return
            idle_ticks += 1
            yield ': heartbeat\n\n'
            await asyncio.sleep(1)



async def wait_result(job_id):
    async with async_redis.from_url(settings.REDIS_URL,decode_responses=True,
                                   socket_connect_timeout=10,socket_timeout=10) as client:
        while True:
            try:
                info = await client.hgetall(PREFIX+job_id)
            except (redis.TimeoutError, redis.ConnectionError):
                # The worker owns the accepted job. A transient poll failure
                # must not turn it into HTTP 500 or cause duplicate submission.
                await asyncio.sleep(1)
                continue
            if not info:
                raise HTTPException(404, 'Không tìm thấy tác vụ hoặc kết quả đã hết hạn.')
            if info.get('status') == 'SUCCESS':
                return json.loads(info['result'])
            if info.get('status') in ('FAILURE','CANCELLED'):
                raise HTTPException(422,info.get('message') or 'Tác vụ xử lý thất bại.')
            await asyncio.sleep(1)
