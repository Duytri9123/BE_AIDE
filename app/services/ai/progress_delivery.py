"""Retry transient progress transport failures without restarting CAD work."""
import asyncio
from redis.exceptions import ConnectionError, TimeoutError


async def deliver(callback, payload):
    for attempt in range(3):
        try:
            result=callback(payload)
            if asyncio.iscoroutine(result):
                await result
            return
        except (ConnectionError, TimeoutError):
            if attempt == 2:
                raise
            await asyncio.sleep(.25 * (attempt+1))
