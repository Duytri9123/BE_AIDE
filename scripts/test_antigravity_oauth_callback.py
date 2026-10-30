"""OAuth regression: host-only admin cookies, single-use grants, and access checks.

Uses isolated short-lived Redis keys; Google and the database are mocked.
"""
import sys
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import httpx
from fastapi import FastAPI, Request
from starlette.middleware.sessions import SessionMiddleware

from app.api.v1.endpoints import admin_helpers as routes
from app.db.session import get_db
from app.services.ai import oauth_state


class OAuthCallbackTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.admin = SimpleNamespace(id=123, is_active=True, is_superuser=True, role="admin")
        self.db = AsyncMock()
        self.db.add = Mock()
        self.db.get.return_value = self.admin
        self.result = Mock()
        self.result.scalar_one_or_none.return_value = self.admin
        self.db.execute.return_value = self.result
        app = FastAPI()
        app.add_middleware(SessionMiddleware, secret_key="oauth-regression-only")

        @app.get("/test-session")
        async def login(request: Request):
            request.session["token"] = str(self.admin.id)
            return {"ok": True}

        async def fake_db():
            yield self.db

        app.dependency_overrides[get_db] = fake_db
        app.include_router(routes.router, prefix="/api/v1")
        app.include_router(routes.oauth_callback_router, prefix="/api/v1")
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://127.0.0.1:8000")
        self.exchange = AsyncMock(return_value={"refresh_token": "fake-token", "email": "test@example.com", "project_id": "test-project"})
        self.patcher = patch.object(routes.TokenRefreshService, "exchange_code_for_tokens", self.exchange)
        self.patcher.start()

    async def asyncTearDown(self):
        self.patcher.stop()
        await self.client.aclose()

    async def start_login(self):
        await self.client.get("/test-session")
        response = await self.client.get("/api/v1/admin-api/antigravity/auth-url")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        query = parse_qs(urlsplit(data["auth_url"]).query)
        self.assertEqual(query["redirect_uri"], [routes.ANTIGRAVITY_REDIRECT_URI])
        return query["state"][0]

    async def callback(self, state, **params):
        return await self.client.get(routes.ANTIGRAVITY_REDIRECT_URI, params={"state": state, **params})

    async def test_cross_host_callback_and_replay(self):
        state = await self.start_login()
        self.result.scalar_one_or_none.return_value = None  # Create a new connection.
        response = await self.callback(state, code="fake-code")
        self.assertNotIn("session=", response.request.headers.get("cookie", ""))
        self.assertEqual(response.status_code, 200)
        self.assertIn("Đăng nhập thành công", response.text)
        self.exchange.assert_awaited_once_with("fake-code", routes.ANTIGRAVITY_REDIRECT_URI)
        self.db.commit.assert_awaited_once()
        self.assertEqual((await self.callback(state, code="fake-code")).status_code, 400)
        self.assertEqual(self.exchange.await_count, 1)

    async def test_invalid_missing_and_expired_state(self):
        for state in ("", "antigravity_login", "A" * 43):
            self.assertEqual((await self.callback(state, code="fake-code")).status_code, 400)
        state = await self.start_login()
        async with oauth_state._client() as client:
            await client.delete(oauth_state._key(state))
        self.assertEqual((await self.callback(state, code="fake-code")).status_code, 400)
        self.exchange.assert_not_awaited()

    async def test_admin_revoked_after_start(self):
        state = await self.start_login()
        self.admin.is_active = False
        self.assertEqual((await self.callback(state, code="fake-code")).status_code, 403)
        self.exchange.assert_not_awaited()

    async def test_google_error_escapes_and_consumes_state(self):
        state = await self.start_login()
        response = await self.callback(state, error="<script>bad</script>")
        self.assertIn("&lt;script&gt;", response.text)
        self.assertEqual((await self.callback(state, code="fake-code")).status_code, 400)
        self.exchange.assert_not_awaited()

    async def test_other_routes_still_require_admin(self):
        for path in ("auth-url", "check-status"):
            response = await self.client.get("/api/v1/admin-api/antigravity/" + path)
            self.assertEqual(response.status_code, 401)
        response = await self.client.post("/api/v1/admin-api/antigravity/exchange", json={"code": "fake-code"})
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
