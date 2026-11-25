"""In-process realtime SSE pub/sub for user notifications."""
import asyncio
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any


_subscribers: dict[int, set[asyncio.Queue]] = defaultdict(set)


def subscribe(user_id: int) -> asyncio.Queue:
    queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    _subscribers[user_id].add(queue)
    return queue


def unsubscribe(user_id: int, queue: asyncio.Queue) -> None:
    queues = _subscribers.get(user_id)
    if not queues:
        return
    queues.discard(queue)
    if not queues:
        _subscribers.pop(user_id, None)


def serialize_notification(notif: Any) -> dict:
    created = getattr(notif, "created_at", None)
    if isinstance(created, datetime):
        created_iso = created.replace(tzinfo=timezone.utc).isoformat() if created.tzinfo is None else created.isoformat()
    else:
        created_iso = datetime.now(timezone.utc).isoformat()
    return {
        "id": notif.id,
        "title": notif.title,
        "body": notif.body,
        "type": notif.type,
        "link": notif.link,
        "is_read": bool(notif.is_read),
        "created_at": created_iso,
    }


def publish_notification(user_id: int, payload: dict) -> None:
    queues = list(_subscribers.get(user_id) or ())
    for queue in queues:
        try:
            queue.put_nowait(payload)
        except asyncio.QueueFull:
            try:
                queue.get_nowait()
                queue.put_nowait(payload)
            except Exception:
                pass
