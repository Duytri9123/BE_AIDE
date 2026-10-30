"""Short-lived, single-use grants for the loopback Google OAuth callback."""
import hashlib
import re
import secrets

from fastapi import HTTPException
import redis.asyncio as redis
from redis.exceptions import RedisError

from app.core.config import settings

TTL_SECONDS = 600
PREFIX = "aide:antigravity:oauth:"
_CONSUME = "local v = redis.call('GET', KEYS[1]); redis.call('DEL', KEYS[1]); return v"


def _key(state: str) -> str:
    return PREFIX + hashlib.sha256(state.encode()).hexdigest()


def _client():
    return redis.from_url(settings.REDIS_URL, decode_responses=True,
                          socket_connect_timeout=3, socket_timeout=3)


async def create_state(admin_id: int) -> str:
    state = secrets.token_urlsafe(32)
    try:
        async with _client() as client:
            await client.set(_key(state), str(admin_id), ex=TTL_SECONDS)
    except RedisError:
        raise HTTPException(503, "Không thể khởi tạo phiên Google OAuth. Vui lòng thử lại.")
    return state


async def consume_state(state: str | None) -> int:
    if not state or not re.fullmatch(r"[A-Za-z0-9_-]{43}", state):
        raise HTTPException(400, "Phiên Google OAuth không hợp lệ. Vui lòng đăng nhập lại từ trang quản trị.")
    try:
        async with _client() as client:
            identity = await client.eval(_CONSUME, 1, _key(state))
    except RedisError:
        raise HTTPException(503, "Không thể xác thực phiên Google OAuth. Vui lòng thử lại.")
    if identity is None:
        raise HTTPException(400, "Phiên Google OAuth đã hết hạn hoặc đã sử dụng. Vui lòng đăng nhập lại.")
    return int(identity)
