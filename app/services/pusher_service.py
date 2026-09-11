import hmac
import hashlib
import json
import time
import httpx
import logging
from typing import Dict, Any, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class PusherService:
    """
    Lightweight, Native Async Pusher Client using httpx and crypto.
    Provides real-time broadcasting to frontend channels and Admin Dashboard.
    """
    def __init__(
        self,
        app_id: str = None,
        key: str = None,
        secret: str = None,
        cluster: str = None,
        ssl: bool = True
    ):
        self.app_id = app_id or settings.PUSHER_APP_ID
        self.key = key or settings.PUSHER_KEY
        self.secret = secret or settings.PUSHER_SECRET
        self.cluster = cluster or settings.PUSHER_CLUSTER
        self.ssl = ssl if ssl is not None else settings.PUSHER_SSL
        self.scheme = "https" if self.ssl else "http"
        self.host = f"api-{self.cluster}.pusher.com"

    async def trigger(self, channel: str, event_name: str, data: Dict[str, Any]) -> bool:
        """
        Broadcast an event to a Pusher channel asynchronously.
        """
        if not self.app_id or not self.key or not self.secret:
            logger.info(f"[Pusher Dev] Broadcasting event '{event_name}' on '{channel}': {data}")
            return True

        try:
            path = f"/apps/{self.app_id}/events"
            body = json.dumps({
                "name": event_name,
                "channels": [channel],
                "data": json.dumps(data)
            })
            
            body_md5 = hashlib.md5(body.encode("utf-8")).hexdigest()
            auth_timestamp = str(int(time.time()))
            
            query_params = {
                "auth_key": self.key,
                "auth_timestamp": auth_timestamp,
                "auth_version": "1.0",
                "body_md5": body_md5
            }
            
            sorted_query = "&".join([f"{k}={v}" for k, v in sorted(query_params.items())])
            string_to_sign = f"POST\n{path}\n{sorted_query}"
            
            auth_signature = hmac.new(
                self.secret.encode("utf-8"),
                string_to_sign.encode("utf-8"),
                hashlib.sha256
            ).hexdigest()
            
            url = f"{self.scheme}://{self.host}{path}?{sorted_query}&auth_signature={auth_signature}"
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    url,
                    content=body,
                    headers={"Content-Type": "application/json"}
                )
                if response.status_code == 200:
                    logger.info(f"[Pusher] Successfully triggered event '{event_name}' on channel '{channel}'")
                    return True
                else:
                    logger.warning(f"[Pusher] Response error {response.status_code}: {response.text}")
                    return False
        except Exception as e:
            logger.error(f"[Pusher] Failed to trigger event: {e}")
            return False

    async def notify_admin(
        self,
        event_type: str,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Helper to send instant toast notifications and stats updates to Admin Dashboard.
        Event Types: 'new-user', 'new-project', 'file-uploaded', 'ai-completed', 'system-alert'
        """
        payload = {
            "type": event_type,
            "title": title,
            "message": message,
            "timestamp": time.strftime("%H:%M:%S"),
            "data": data or {}
        }
        return await self.trigger(settings.PUSHER_CHANNEL, "admin-notification", payload)

    async def notify_user(
        self,
        user_id: int,
        title: str,
        message: str,
        event_type: str = "info",
        link: Optional[str] = None
    ) -> bool:
        """
        Send a real-time notification to a specific user and admin via Pusher.
        """
        payload = {
            "user_id": user_id,
            "type": event_type,
            "title": title,
            "message": message,
            "link": link,
            "timestamp": time.strftime("%H:%M:%S")
        }
        # Trigger on user specific channel
        await self.trigger(f"user-{user_id}", "user-notification", payload)
        # Also broadcast to admin channel
        return await self.trigger(settings.PUSHER_CHANNEL, "admin-notification", payload)

# Global singleton
pusher_service = PusherService()

