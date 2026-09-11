"""
Token Refresh Service - Hỗ trợ tự động gia hạn token OAuth (Google Antigravity & OpenAI/Codex).
Cơ chế tương tự 9router: Tự động đổi Refresh Token (1//...) lấy Access Token (ya29...) và cache trong RAM.
"""
import time
import httpx
from typing import Optional, Dict

logger = None

# Cache trong RAM: refresh_token -> (access_token, expire_timestamp)
_TOKEN_CACHE: Dict[str, tuple[str, float]] = {}

DEFAULT_GOOGLE_CLIENT_ID = "770932025776-joodcr55bkmc3b0ch44bve8oigfudebk.apps.googleusercontent.com"


class TokenRefreshService:
    """Quản lý và tự động làm mới các token OAuth."""

    @staticmethod
    async def get_active_token(
        raw_token: str,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None
    ) -> str:
        """
        Nếu raw_token là Google Refresh Token (bắt đầu bằng 1//),
        tự động làm mới hoặc trả về Access Token (ya29...) còn hạn.
        Ngược lại trả về nguyên chuỗi raw_token.
        """
        clean = (raw_token or "").strip()
        if not clean.startswith("1//"):
            return clean

        now = time.time()
        # Kiểm tra cache (dành ra 10 phút buffer trước khi token hết hạn 60 phút)
        if clean in _TOKEN_CACHE:
            cached_token, exp_time = _TOKEN_CACHE[clean]
            if now < exp_time:
                return cached_token

        # Gọi làm mới qua Google OAuth
        cid = client_id or DEFAULT_GOOGLE_CLIENT_ID
        data = {
            "client_id": cid,
            "grant_type": "refresh_token",
            "refresh_token": clean
        }
        if client_secret:
            data["client_secret"] = client_secret

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post("https://oauth2.googleapis.com/token", data=data)
                if resp.status_code == 200:
                    res_json = resp.json()
                    access_token = res_json.get("access_token", "")
                    expires_in = float(res_json.get("expires_in", 3600))
                    # Lưu cache (trừ 300s buffer an toàn)
                    _TOKEN_CACHE[clean] = (access_token, now + expires_in - 300)
                    return access_token
                else:
                    raise Exception(f"Google OAuth refresh trả về HTTP {resp.status_code}: {resp.text[:200]}")
        except Exception as ex:
            raise Exception(f"Lỗi khi làm mới Google OAuth Refresh Token: {str(ex)}")
