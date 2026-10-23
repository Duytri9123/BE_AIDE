"""CAD gateway authentication, provider/model policy and native tool transport."""
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch, AsyncMock

import httpx
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.models.base import Base
import app.models
from app.models.ai_provider import AiProvider
from app.models.ai_provider_model import AiProviderModel
from app.models.ai_connection import AiConnection
from app.api.v1.endpoints.cad_agent import router
from app.db.session import get_db
from app.api.deps import get_current_active_user
from app.services.ai import cad_agent_gateway as gateway


class CadGatewayTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        gateway.MODEL_CACHE.clear()
        self.engine = create_async_engine('sqlite+aiosqlite:///:memory:')
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.db = async_sessionmaker(self.engine, expire_on_commit=False)()
        self.db.add(AiProvider(id='test', name='Test', slug='test', api_type='antigravity_engine', base_url='https://provider.invalid/v1'))
        await self.db.flush()
        self.db.add_all([
            AiProviderModel(provider_id='test', model_key='gemini-live', label='Live', is_active=True),
            AiProviderModel(provider_id='test', model_key='gemini-disabled', label='Disabled', is_active=False),
            AiConnection(provider='test', api_key='SERVER_SECRET', selected_model='gemini-live', status='active')])
        await self.db.commit()
        self.app = FastAPI()
        self.app.include_router(router, prefix='/cad-agent')
        async def database(): yield self.db
        self.app.dependency_overrides[get_db] = database
        self.app.dependency_overrides[get_current_active_user] = lambda: SimpleNamespace(id=1)
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url='http://test')

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.db.close()
        await self.engine.dispose()

    async def test_anonymous_cannot_use_system_keys(self):
        del self.app.dependency_overrides[get_current_active_user]
        response = await self.client.get('/cad-agent/providers')
        self.assertEqual(response.status_code, 401)

    async def test_metadata_never_returns_credentials_or_inactive_models(self):
        response = await self.client.get('/cad-agent/providers')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('SERVER_SECRET', response.text)
        self.assertNotIn('api_key', response.text)
        self.assertEqual([m['model_key'] for m in response.json()[0]['models']], ['gemini-live'])

    async def test_disabled_provider_rejected(self):
        provider = await self.db.get(AiProvider, 'test')
        provider.is_active = False
        await self.db.commit()
        self.assertEqual((await self.client.get('/cad-agent/providers')).json(), [])
        response = await self.client.post('/cad-agent/providers/test/inference', json={'model':'gemini-live','payload':{}})
        self.assertEqual(response.status_code, 404)

    async def test_live_discovery_keeps_admin_disabled_models_disabled(self):
        with patch.object(gateway, 'discover_models', new=AsyncMock(return_value=[
            gateway.model_option('gemini-new'), gateway.model_option('gemini-disabled')])):
            result = await self.client.get('/cad-agent/providers/test/models?refresh=true')
        self.assertEqual(result.json()['source'], 'provider_api')
        self.assertEqual([m['model_key'] for m in result.json()['models']], ['gemini-new'])

    async def test_unlisted_model_cannot_use_system_key(self):
        with patch.object(gateway, 'discover_models', new=AsyncMock(return_value=[])):
            response = await self.client.post('/cad-agent/providers/test/inference', json={'model':'gemini-unknown','payload':{}})
        self.assertEqual(response.status_code, 400)

    async def test_system_only_allows_antigravity_gemini(self):
        self.db.add(AiProviderModel(provider_id='test', model_key='claude-opus', label='Claude', is_active=True))
        await self.db.commit()
        result = await self.client.get('/cad-agent/providers')
        self.assertEqual([m['model_key'] for m in result.json()[0]['models']], ['gemini-live'])
        with patch.object(gateway, 'discover_models', new=AsyncMock(return_value=[
            gateway.model_option('gemini-latest'), gateway.model_option('claude-opus'), gateway.model_option('gpt-oss')])):
            result = await self.client.get('/cad-agent/providers/test/models?refresh=true')
        self.assertEqual([m['model_key'] for m in result.json()['models']], ['gemini-latest'])
        for key in ['claude-opus', 'ag/claude-opus', 'gpt-oss']:
            result = await self.client.post('/cad-agent/providers/test/inference', json={'model':key,'payload':{}})
            self.assertEqual(result.status_code, 400)
        provider = await self.db.get(AiProvider, 'test')
        provider.api_type = 'google_gemini'
        await self.db.commit()
        self.assertEqual((await self.client.get('/cad-agent/providers')).json(), [])
        self.assertEqual((await self.client.get('/cad-agent/providers/test/models')).status_code, 404)
        self.assertEqual((await self.client.post('/cad-agent/providers/test/inference', json={'model':'gemini-live','payload':{}})).status_code, 404)

    async def test_antigravity_disabled_alias_cannot_bypass_policy(self):
        provider = await self.db.get(AiProvider, 'test')
        provider.api_type = 'antigravity_engine'
        self.db.add(AiProviderModel(provider_id='test', model_key='ag/gemini-blocked', label='Blocked', is_active=False))
        await self.db.commit()
        with patch.object(gateway, 'discover_models', new=AsyncMock(return_value=[gateway.model_option('gemini-blocked')])):
            result = await self.client.get('/cad-agent/providers/test/models?refresh=true')
        self.assertEqual(result.json()['models'], [])
        response = await self.client.post('/cad-agent/providers/test/inference', json={'model':'gemini-blocked','payload':{}})
        self.assertEqual(response.status_code, 400)

    async def test_tool_payload_and_native_sse_survive_proxy(self):
        seen = []
        def upstream(request):
            seen.append(request)
            return httpx.Response(200, headers={'Content-Type':'text/event-stream'},
                content=b'data: {"choices":[{"delta":{"tool_calls":[]}}]}\n\ndata: [DONE]\n\n')
        real_client = httpx.AsyncClient
        with patch.object(gateway.httpx, 'AsyncClient', side_effect=lambda **kw: real_client(transport=httpx.MockTransport(upstream), **kw)), \
             patch.object(gateway.TokenRefreshService, 'get_active_token', new=AsyncMock(return_value='SERVER_SECRET')), \
             patch.object(gateway.TokenRefreshService, 'get_project_id', new=AsyncMock(return_value='test-project')):
            response = await self.client.post('/cad-agent/providers/test/inference', json={
                'model':'gemini-live','payload':{'messages':[{'role':'developer','content':'system'}],
                'tools':[{'type':'function','function':{'name':'draw_line','parameters':{'type':'object'}}}]}})
        self.assertEqual(response.status_code, 200)
        self.assertIn('[DONE]', response.text)
        self.assertEqual(seen[0].headers['Authorization'], 'Bearer SERVER_SECRET')
        body = json.loads(seen[0].content)
        self.assertEqual(body['tools'][0]['function']['name'], 'draw_line')
        self.assertEqual(body['messages'][0]['role'], 'developer')
        self.assertNotIn('SERVER_SECRET', response.text)

    async def test_model_discovery_failure_falls_back_with_warning(self):
        with patch.object(gateway, 'discover_models', new=AsyncMock(side_effect=httpx.ConnectError('offline'))):
            result = await self.client.get('/cad-agent/providers/test/models?refresh=true')
        self.assertEqual(result.json()['source'], 'system_catalog')
        self.assertTrue(result.json()['warning'])

    async def test_antigravity_preserves_selected_version_and_refreshes_oauth(self):
        provider = SimpleNamespace(api_type='antigravity_engine', base_url='unused')
        connection = SimpleNamespace(api_key='refresh')
        with patch.object(gateway.TokenRefreshService, 'get_active_token', new=AsyncMock(return_value='access')), \
             patch.object(gateway.TokenRefreshService, 'get_project_id', new=AsyncMock(return_value='real-project')):
            url, headers, payload = await gateway.native_request(provider, connection, 'ag/gemini-new',
                {'model':'ag/gemini-new','project':'caller-project','request':{'tools':[]}}, True)
        self.assertIn('streamGenerateContent', url)
        self.assertEqual(payload['model'], 'gemini-new')
        self.assertEqual(payload['project'], 'real-project')
        self.assertEqual(headers['Authorization'], 'Bearer access')

    async def test_google_and_anthropic_use_correct_protocol(self):
        connection = SimpleNamespace(api_key='secret')
        google = SimpleNamespace(api_type='google_gemini',base_url='https://generativelanguage.googleapis.com')
        url, headers, body = await gateway.native_request(google, connection, 'gemini-new', {'tools':[]}, True)
        self.assertTrue(url.endswith('/openai/chat/completions'))
        self.assertEqual(body['model'], 'gemini-new')
        anthropic = SimpleNamespace(api_type='anthropic',base_url='https://api.anthropic.com/v1')
        url, headers, body = await gateway.native_request(anthropic, connection, 'claude-new', {'tools':[]}, False)
        self.assertTrue(url.endswith('/messages'))
        self.assertEqual(headers['x-api-key'], 'secret')
        self.assertFalse(body['stream'])


if __name__ == '__main__': unittest.main()
