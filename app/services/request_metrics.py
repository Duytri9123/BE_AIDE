"""Per-request timings without recording SQL text, parameters or user data."""
import logging
import time
from contextvars import ContextVar
from sqlalchemy import event

_current = ContextVar('request_metrics', default=None)
logger = logging.getLogger(__name__)


def instrument_engine(engine):
    if getattr(engine, '_request_metrics_installed', False):
        return
    engine._request_metrics_installed = True
    @event.listens_for(engine, 'before_cursor_execute')
    def before(conn, cursor, statement, parameters, context, executemany):
        metrics = _current.get()
        if metrics is not None:
            metrics['queries'] += 1
            context._request_started = time.perf_counter()
    @event.listens_for(engine, 'after_cursor_execute')
    def after(conn, cursor, statement, parameters, context, executemany):
        metrics = _current.get()
        start = getattr(context, '_request_started', None)
        if metrics is not None and start is not None:
            metrics['db_ms'] += (time.perf_counter()-start)*1000


class RequestMetricsMiddleware:
    def __init__(self, app, slow_ms=1000):
        self.app = app
        self.slow_ms = slow_ms

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or not scope['path'].startswith('/api/'):
            return await self.app(scope, receive, send)
        metrics = {'queries':0, 'db_ms':0.0, 'bytes':0}
        token = _current.set(metrics); start = time.perf_counter(); status = 500
        async def timed_send(message):
            nonlocal status
            if message['type'] == 'http.response.start':
                status = message['status']
                headers = list(message.get('headers', []))
                elapsed = (time.perf_counter()-start)*1000
                headers.append((b'server-timing', f'app;dur={elapsed:.2f}, db;dur={metrics["db_ms"]:.2f}, sql;desc="{metrics["queries"]} queries"'.encode()))
                message = {**message, 'headers':headers}
            elif message['type'] == 'http.response.body':
                metrics['bytes'] += len(message.get('body', b''))
            await send(message)
        try:
            await self.app(scope, receive, timed_send)
        finally:
            elapsed = (time.perf_counter()-start)*1000
            if elapsed >= self.slow_ms:
                # Route template omits IDs and query strings. SSE timing is full
                # stream lifetime; the header measures time to response start.
                route = scope.get('route')
                logger.warning('api_slow method=%s route=%s status=%s total_ms=%.2f db_ms=%.2f sql_count=%d response_bytes=%d',
                               scope['method'], getattr(route,'path','unmatched'), status,
                               elapsed,metrics['db_ms'],metrics['queries'],metrics['bytes'])
            _current.reset(token)
