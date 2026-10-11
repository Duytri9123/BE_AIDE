"""Bounded Redis cache for display snapshots; filesystem remains authoritative."""
import hashlib
import json
import time
import redis
from redis.backoff import NoBackoff
from redis.retry import Retry
from app.core.config import settings

_client = None
_retry_after = 0.0


def _redis():
    global _client
    if _client is None:
        _client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True,
            socket_connect_timeout=0.5, socket_timeout=1,
            retry=Retry(NoBackoff(), 0))
    return _client


def _key(root):
    scope = hashlib.sha256(str(root.resolve()).encode()).hexdigest()[:20]
    return 'aide:catalogtb:display:v2:' + scope


def read_snapshot(root):
    global _retry_after
    if time.monotonic() < _retry_after:
        return None
    try:
        raw = _redis().get(_key(root))
        if not raw:
            return None
        payload = json.loads(raw)
        remaining = payload['expires_at'] - time.time()
        data = payload['data']
        if remaining <= 0 or not isinstance(data.get('items'), list):
            return None
        return data, min(remaining, 60)
    except (redis.RedisError, ValueError, KeyError, TypeError, AttributeError):
        _retry_after = time.monotonic() + 30
        return None


def write_snapshot(root, data):
    global _retry_after
    if time.monotonic() < _retry_after:
        return False
    try:
        payload = json.dumps({'expires_at': time.time() + 60, 'data': data}, ensure_ascii=False)
        return bool(_redis().setex(_key(root), 60, payload))
    except (redis.RedisError, ValueError, TypeError):
        _retry_after = time.monotonic() + 30
        return False
