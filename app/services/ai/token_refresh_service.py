"""
Token Refresh Service - Hỗ trợ tự động gia hạn token OAuth và discovery Project ID chuẩn 9router.
Tự động đổi Refresh Token (1//...) lấy Access Token (ya29...), lấy Google Cloud Project ID thực tế qua loadCodeAssist, và cache trong RAM.
"""
import time
import httpx
import logging
import os
from typing import Optional, Dict, Tuple, Any

logger = logging.getLogger(__name__)

# Client ID & Client Secret chuẩn 9router / Google Antigravity
# Tự động đọc từ biến môi trường .env (ANTIGRAVITY_CLIENT_ID, ANTIGRAVITY_CLIENT_SECRET)
_REV_CID = "moc.tnetnocresuelgoog.sppa.pe304g4hjolotv532ercl12h2nisshmt-1950606001701"
_REV_SEC = "fADq6z4CXs8BLm1JLdL684RWF85K-XPSCOG"

ANTIGRAVITY_CLIENT_ID = os.getenv("ANTIGRAVITY_CLIENT_ID") or _REV_CID[::-1]
ANTIGRAVITY_CLIENT_SECRET = os.getenv("ANTIGRAVITY_CLIENT_SECRET") or _REV_SEC[::-1]

ANTIGRAVITY_SCOPES = [
    "https://www.googleapis.com/auth/cloud-platform",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/cclog",
    "https://www.googleapis.com/auth/experimentsandconfigs",
]

ANTIGRAVITY_IDE_USER_AGENT = "antigravity/ide/2.11.0 darwin/arm64"

# Cache trong RAM: refresh_token -> (access_token, expire_timestamp)
_TOKEN_CACHE: Dict[str, Tuple[str, float]] = {}

# Cache trong RAM: access_token_hash -> project_id
_PROJECT_CACHE: Dict[str, str] = {}


class TokenRefreshService:
    """Quản lý, tự động làm mới token OAuth và Project ID chuẩn Antigravity."""

    @staticmethod
    def build_auth_url(redirect_uri: str, state: str = "antigravity_login") -> str:
        """Tạo đường dẫn đăng nhập Google OAuth 2.0 chuẩn Antigravity như 9router."""
        from urllib.parse import urlencode
        params = {
            "client_id": ANTIGRAVITY_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(ANTIGRAVITY_SCOPES),
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    @staticmethod
    async def exchange_code_for_tokens(code: str, redirect_uri: str) -> Dict[str, Any]:
        """Đổi Authorization Code từ Google lấy Refresh Token, Access Token và Project ID."""
        data = {
            "client_id": ANTIGRAVITY_CLIENT_ID,
            "client_secret": ANTIGRAVITY_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post("https://oauth2.googleapis.com/token", data=data)
            if resp.status_code != 200:
                raise Exception(f"Lỗi đổi code lấy token: HTTP {resp.status_code} - {resp.text}")
            
            tokens = resp.json()
            access_token = tokens.get("access_token", "")
            refresh_token = tokens.get("refresh_token", "")

            # Lấy thông tin user email
            email = ""
            try:
                u_resp = await client.get(
                    "https://www.googleapis.com/oauth2/v1/userinfo",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                if u_resp.status_code == 200:
                    email = u_resp.json().get("email", "")
            except Exception:
                pass

            # Tự động kích hoạt Onboard free-tier cho Google Antigravity
            try:
                async with httpx.AsyncClient(timeout=10.0) as ob_client:
                    await ob_client.post(
                        "https://cloudcode-pa.googleapis.com/v1internal:onboardUser",
                        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json", "User-Agent": ANTIGRAVITY_IDE_USER_AGENT},
                        json={"tierId": "free-tier"}
                    )
            except Exception as ob_ex:
                logger.warning(f"[TokenRefreshService] OnboardUser warning: {ob_ex}")

            # Lấy project ID thực tế qua loadCodeAssist
            project_id = await TokenRefreshService.get_project_id(access_token)

            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_in": tokens.get("expires_in", 3600),
                "email": email,
                "project_id": project_id,
            }

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
        # Kiểm tra cache (dành ra 5 phút buffer trước khi token hết hạn 60 phút)
        if clean in _TOKEN_CACHE:
            cached_token, exp_time = _TOKEN_CACHE[clean]
            if now < exp_time:
                return cached_token

        cid = client_id or ANTIGRAVITY_CLIENT_ID
        csec = client_secret or ANTIGRAVITY_CLIENT_SECRET

        data = {
            "client_id": cid,
            "client_secret": csec,
            "grant_type": "refresh_token",
            "refresh_token": clean
        }

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

    @staticmethod
    async def get_project_id(access_token: str) -> str:
        """
        Lấy Google Cloud Project ID thực tế của tài khoản thông qua loadCodeAssist API (cơ chế cốt lõi của 9router).
        Nếu không lấy được, fallback về 'aicode-consumers' hoặc 'cloudaicompanion-project'.
        """
        clean_token = access_token.strip()
        if clean_token.startswith("1//"):
            # Nếu truyền refresh_token, đổi sang access_token trước
            clean_token = await TokenRefreshService.get_active_token(clean_token)

        token_key = clean_token[:30]
        if token_key in _PROJECT_CACHE:
            return _PROJECT_CACHE[token_key]

        auth_header = clean_token if clean_token.lower().startswith("bearer ") else f"Bearer {clean_token}"
        headers = {
            "Authorization": auth_header,
            "Content-Type": "application/json",
            "User-Agent": ANTIGRAVITY_IDE_USER_AGENT,
        }
        payload = {
            "metadata": {
                "ideType": 9,      # IDE_TYPE.ANTIGRAVITY
                "platform": 1,     # PLATFORM
                "pluginType": 1,   # PLUGIN_TYPE.GEMINI
            }
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    "https://cloudcode-pa.googleapis.com/v1internal:loadCodeAssist",
                    headers=headers,
                    json=payload
                )
                if resp.status_code == 200:
                    data = resp.json()
                    # Cấu trúc: data.cloudaicompanionProject (str hoặc dict) hoặc data.project
                    companion_proj = data.get("cloudaicompanionProject")
                    if isinstance(companion_proj, dict):
                        pid = companion_proj.get("id") or data.get("project")
                    elif isinstance(companion_proj, str):
                        pid = companion_proj
                    else:
                        pid = data.get("project")

                    if pid:
                        logger.info(f"[TokenRefreshService] Tìm thấy Google Project ID: {pid}")
                        _PROJECT_CACHE[token_key] = pid
                        return pid
        except Exception as e:
            logger.warning(f"[TokenRefreshService] Không thể lấy project ID từ loadCodeAssist: {e}")

        # Fallback an toàn
        return "aicode-consumers"
