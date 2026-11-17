"""Request-local progress from executed operations; no simulated stages or percentages."""
import asyncio
import json
import time
from contextlib import contextmanager
from contextvars import ContextVar
from uuid import uuid4

_sink = ContextVar('el_progress_sink', default=None)
_scope = ContextVar('el_progress_scope', default='')

@contextmanager
def progress_scope(label):
    token = _scope.set(label)
    try:
        yield
    finally:
        _scope.reset(token)

async def run_step(label, operation, *, detail='', tool='elquote'):
    sink = _sink.get()
    if sink is None:
        return await operation
    event = dict(id=uuid4().hex, tool=tool, label=label, state='running',
                 detail=' · '.join(str(v) for v in (_scope.get(), detail) if v))
    started = time.monotonic()
    sink(dict(type='activity', activity=event))
    token = _scope.set(' · '.join(v for v in (_scope.get(), label) if v))
    try:
        result = await operation
    except BaseException as exc:
        sink(dict(type='activity', activity={**event, 'state':'error',
            'detail':event['detail'] + (' · Đã dừng' if isinstance(exc, asyncio.CancelledError) else ' · Thao tác chưa hoàn tất')}))
        raise
    finally:
        _scope.reset(token)
    sink(dict(type='activity', activity={**event, 'state':'success', 'label':label.replace('Đang ', 'Đã ', 1).replace('ElQuote đang ', 'ElQuote đã ', 1),
        'detail':' · '.join(v for v in (event['detail'], f'{time.monotonic()-started:.1f} giây') if v)}))
    return result

async def progress_events(operation, *, heartbeat=15):
    """Cancel the owned operation when the stream closes; never retry a write."""
    queue = asyncio.Queue()
    async def run():
        token = _sink.set(queue.put_nowait)
        try:
            result = await operation()
            queue.put_nowait(dict(type='complete', result=result))
        except asyncio.CancelledError:
            queue.put_nowait(dict(type='error', message='ElQuote đã dừng yêu cầu.', status=499))
            raise
        except Exception as exc:
            queue.put_nowait(dict(type='error', message=str(getattr(exc,'detail',None) or exc),
                                 status=getattr(exc,'status_code',500)))
        finally:
            _sink.reset(token)
    task = asyncio.create_task(run())
    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=heartbeat)
            except asyncio.TimeoutError:
                yield ': keepalive\n\n'
                continue
            yield 'data: '+json.dumps(event, ensure_ascii=False, default=str)+'\n\n'
            if event['type'] in ('complete','error'):
                break
    finally:
        if not task.done():
            task.cancel()
        await asyncio.gather(task, return_exceptions=True)

def progress_step(label):
    from functools import wraps
    def decorate(fn):
        @wraps(fn)
        async def wrapped(*args, **kwargs):
            return await run_step(label, fn(*args, **kwargs))
        return wrapped
    return decorate
