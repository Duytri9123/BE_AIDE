import json
import logging
import time
import asyncio
from typing import Any, Optional, Dict, Tuple
import redis
import redis.asyncio as aioredis
from app.core.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """
    Dịch vụ Caching hiệu năng cao hỗ trợ cả Redis và In-Memory Fallback.
    Nếu Redis server không hoạt động hoặc mất kết nối, hệ thống sẽ tự động
    chuyển sang In-Memory Cache mà không làm gián đoạn hoặc sập ứng dụng.
    """
    _instance: Optional["CacheService"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.redis_url = getattr(settings, "REDIS_URL", "redis://localhost:6379/0")
        self._async_redis: Optional[aioredis.Redis] = None
        self._sync_redis: Optional[redis.Redis] = None

        # Bộ nhớ tạm In-Memory khi Redis offline: {key: (expire_timestamp, value)}
        self._memory_cache: Dict[str, Tuple[float, Any]] = {}
        self._redis_available: bool = True
        self._last_redis_check: float = 0.0
        self._retry_interval: float = 15.0  # Thử kết nối lại sau 15 giây nếu Redis rớt mạng

        self._init_clients()
        self._initialized = True

    def _init_clients(self):
        try:
            self._sync_redis = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_timeout=1.5,
                socket_connect_timeout=1.5
            )
            # Kiểm tra ping nhanh
            self._sync_redis.ping()
            self._redis_available = True
            logger.info("[CacheService] Kết nối Redis thành công tại: %s", self.redis_url)
        except Exception as e:
            self._redis_available = False
            self._last_redis_check = time.time()
            logger.warning(
                "[CacheService] Chưa bật Redis (%s). Tự động kích hoạt In-Memory Fallback Cache.",
                str(e)
            )

    def _get_async_client(self) -> Optional[aioredis.Redis]:
        if not self._redis_available:
            return None
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        if self._async_redis is not None:
            if getattr(self, "_async_redis_loop", None) is not current_loop:
                self._async_redis = None

        if self._async_redis is None:
            try:
                self._async_redis = aioredis.from_url(
                    self.redis_url,
                    decode_responses=True,
                    socket_timeout=1.5,
                    socket_connect_timeout=1.5
                )
                self._async_redis_loop = current_loop
            except Exception:
                self._async_redis = None
        return self._async_redis

    def _should_retry_redis(self) -> bool:
        return not self._redis_available and (time.time() - self._last_redis_check > self._retry_interval)

    # ---------------------------------------------------------
    # In-Memory Cache Helper Methods
    # ---------------------------------------------------------
    def _mem_get(self, key: str) -> Optional[Any]:
        if key in self._memory_cache:
            exp, val = self._memory_cache[key]
            if exp == 0 or exp > time.time():
                return val
            else:
                del self._memory_cache[key]
        return None

    def _mem_set(self, key: str, val: Any, expire_seconds: Optional[int] = None):
        exp = (time.time() + expire_seconds) if expire_seconds else 0
        self._memory_cache[key] = (exp, val)
        # Tự dọn dẹp nếu bộ nhớ quá 5000 phần tử
        if len(self._memory_cache) > 5000:
            now = time.time()
            expired_keys = [k for k, (e, _) in self._memory_cache.items() if e != 0 and e <= now]
            for k in expired_keys:
                self._memory_cache.pop(k, None)

    def _mem_delete(self, key: str):
        self._memory_cache.pop(key, None)

    def _mem_clear_prefix(self, prefix: str):
        keys = [k for k in self._memory_cache if k.startswith(prefix)]
        for k in keys:
            del self._memory_cache[k]

    # ---------------------------------------------------------
    # Asynchronous Cache API (Cho FastAPI & Async Services)
    # ---------------------------------------------------------
    async def get(self, key: str) -> Optional[str]:
        if self._should_retry_redis():
            self._init_clients()

        if self._redis_available:
            try:
                client = self._get_async_client()
                if client:
                    return await client.get(key)
            except Exception as e:
                logger.warning("[CacheService] Lỗi đọc Redis async: %s. Dùng memory cache.", str(e))
                self._redis_available = False
                self._last_redis_check = time.time()

        return self._mem_get(key)

    async def set(self, key: str, value: str, expire: Optional[int] = None) -> bool:
        if self._should_retry_redis():
            self._init_clients()

        success = False
        if self._redis_available:
            try:
                client = self._get_async_client()
                if client:
                    if expire:
                        await client.setex(key, expire, value)
                    else:
                        await client.set(key, value)
                    success = True
            except Exception as e:
                logger.warning("[CacheService] Lỗi ghi Redis async: %s. Dùng memory cache.", str(e))
                self._redis_available = False
                self._last_redis_check = time.time()

        self._mem_set(key, value, expire)
        return success or True

    async def get_json(self, key: str) -> Optional[Any]:
        raw = await self.get(key)
        if raw is not None:
            try:
                return json.loads(raw)
            except Exception:
                return raw
        return None

    async def set_json(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        raw = json.dumps(value, ensure_ascii=False)
        return await self.set(key, raw, expire)

    async def delete(self, key: str) -> bool:
        self._mem_delete(key)
        if self._redis_available:
            try:
                client = self._get_async_client()
                if client:
                    await client.delete(key)
                    return True
            except Exception:
                pass
        return True

    async def clear_prefix(self, prefix: str) -> int:
        self._mem_clear_prefix(prefix)
        count = 0
        if self._redis_available:
            try:
                client = self._get_async_client()
                if client:
                    keys = await client.keys(f"{prefix}*")
                    if keys:
                        count = await client.delete(*keys)
            except Exception:
                pass
        return count

    # ---------------------------------------------------------
    # Synchronous Cache API (Cho Catalog Engine, Celery & Sync code)
    # ---------------------------------------------------------
    def get_sync(self, key: str) -> Optional[str]:
        if self._should_retry_redis():
            self._init_clients()

        if self._redis_available and self._sync_redis:
            try:
                return self._sync_redis.get(key)
            except Exception as e:
                self._redis_available = False
                self._last_redis_check = time.time()

        return self._mem_get(key)

    def set_sync(self, key: str, value: str, expire: Optional[int] = None) -> bool:
        if self._should_retry_redis():
            self._init_clients()

        if self._redis_available and self._sync_redis:
            try:
                if expire:
                    self._sync_redis.setex(key, expire, value)
                else:
                    self._sync_redis.set(key, value)
            except Exception:
                self._redis_available = False
                self._last_redis_check = time.time()

        self._mem_set(key, value, expire)
        return True

    def get_json_sync(self, key: str) -> Optional[Any]:
        raw = self.get_sync(key)
        if raw is not None:
            try:
                return json.loads(raw)
            except Exception:
                return raw
        return None

    def set_json_sync(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        raw = json.dumps(value, ensure_ascii=False)
        return self.set_sync(key, raw, expire)

    def delete_sync(self, key: str) -> bool:
        self._mem_delete(key)
        if self._redis_available and self._sync_redis:
            try:
                self._sync_redis.delete(key)
            except Exception:
                pass
        return True

    def clear_prefix_sync(self, prefix: str) -> int:
        self._mem_clear_prefix(prefix)
        count = 0
        if self._redis_available and self._sync_redis:
            try:
                keys = self._sync_redis.keys(f"{prefix}*")
                if keys:
                    count = self._sync_redis.delete(*keys)
            except Exception:
                pass
        return count


# Singleton instance
cache_service = CacheService()
