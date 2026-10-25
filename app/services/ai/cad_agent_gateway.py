"""Native provider transport for CAD tools; system credentials never reach the browser."""
import re
import time

import httpx
from fastapi import HTTPException
from sqlalchemy import select

from app.models.ai_connection import AiConnection
from app.models.ai_provider import AiProvider
from app.models.ai_provider_model import AiProviderModel
from app.services.ai.token_refresh_service import TokenRefreshService

MODEL_CACHE = {}
SUPPORTED_TYPES = {'openai_compatible', 'anthropic', 'google_gemini', 'antigravity_engine'}


def model_recency(model):
    """Sort provider versions naturally, keeping the latest choices first."""
    key = model['model_key']
    version = re.search(r'(?:gemini-|gpt-|claude-(?:opus-|sonnet-|haiku-)?)(\d+)(?:[.-](\d+))?', key)
    return (int(version[1]) if version else 0, int(version[2] or 0) if version else 0,
            2 if 'high' in key else 1 if 'medium' in key else 0, key)


def protocol(provider):
    if provider.api_type == 'antigravity_engine':
        return 'antigravity'
    if provider.api_type == 'google_gemini':
        return 'google'
    if provider.api_type == 'anthropic':
        return 'anthropic'
    return 'openai'


def model_option(key, label=None, raw=None):
    raw = raw or {}
    modalities = raw.get('architecture', {}).get('input_modalities', [])
    vision = ('image' in modalities or bool(re.search(
        r'gpt-(?:[456](?:\.|-|$))|claude|gemini|pixtral|llava|(?:qwen.*vl)|deepseek-vl|grok-(?:[234])', key, re.I)))
    return {'model_key': key, 'label': label or key, 'supports_vision': vision}


async def provider_state(db, provider_id):
    provider = await db.get(AiProvider, provider_id)
    if not provider or not provider.is_active or provider.api_type not in SUPPORTED_TYPES:
        raise HTTPException(404, 'Provider không khả dụng cho CAD Agent.')
    connections = (await db.execute(select(AiConnection).where(
        AiConnection.provider == provider_id, AiConnection.is_active.is_(True),
        AiConnection.api_key.isnot(None), AiConnection.api_key != '',
        AiConnection.status.notin_(['inactive', 'rate_limited'])
    ).order_by(AiConnection.priority, AiConnection.created_at.desc()))).scalars().all()
    if not connections:
        raise HTTPException(409, 'Provider chưa có kết nối hệ thống khả dụng. Chọn provider khác hoặc API cá nhân.')
    models = (await db.execute(select(AiProviderModel).where(
        AiProviderModel.provider_id == provider_id
    ).order_by(AiProviderModel.sort_order, AiProviderModel.id))).scalars().all()
    return provider, connections, models


async def discover_models(provider, connection):
    kind = protocol(provider)
    key = connection.api_key.strip()
    base = (provider.base_url or '').rstrip('/')
    headers = {'Authorization': f'Bearer {key}'}
    if kind == 'google':
        url = 'https://generativelanguage.googleapis.com/v1beta/models'
        headers = {'x-goog-api-key': key}
    elif kind == 'anthropic':
        url = f'{base}/models'
        headers = {'x-api-key': key, 'anthropic-version': '2023-06-01'}
    elif kind == 'antigravity':
        key = await TokenRefreshService.get_active_token(key)
        project = await TokenRefreshService.get_project_id(key)
        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.post('https://daily-cloudcode-pa.googleapis.com/v1internal:fetchAvailableModels',
                headers={'Authorization': f'Bearer {key}', 'User-Agent': 'antigravity/ide/2.11.0 darwin/arm64'},
                json={'project': project})
            response.raise_for_status()
            models = response.json().get('models', {})
            options = [model_option(model_id, row.get('displayName') or row.get('modelDisplayName') or model_id)
                for model_id, row in models.items()
                if not re.search(r'^(?:chat_|tab_)|image|tiered$', model_id, re.I)
                and not row.get('deprecated')]
            return sorted(options, key=model_recency, reverse=True)
    else:
        url = f'{base}/models'
    items = []
    params = {}
    async with httpx.AsyncClient(timeout=None, follow_redirects=False) as client:
        for _ in range(20):
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            body = response.json()
            for row in body.get('models', body.get('data', [])):
                methods = row.get('supportedGenerationMethods')
                if methods is not None and 'generateContent' not in methods:
                    continue
                key_id = str(row.get('id') or row.get('name') or '').removeprefix('models/')
                if not key_id or re.search(r'embed|whisper|tts|moderation|image-|dall-e|transcrib|realtime|audio|sora', key_id, re.I):
                    continue
                items.append((row.get('created', row.get('created_at', '')), model_option(
                    key_id, row.get('display_name') or row.get('displayName') or key_id, row)))
            if body.get('nextPageToken'):
                params = {'pageToken': body['nextPageToken']}
            elif body.get('has_more') and body.get('last_id'):
                params = {'after_id': body['last_id']}
            else:
                break
    items.sort(key=lambda item: str(item[0]), reverse=True)
    return list({item[1]['model_key']: item[1] for item in items}.values())


async def get_models(db, provider_id, refresh=False):
    provider, connections, rows = await provider_state(db, provider_id)
    canonical = lambda key: key.removeprefix('ag/') if protocol(provider) == 'antigravity' else key
    disabled = {canonical(row.model_key) for row in rows if not row.is_active}
    cached = MODEL_CACHE.get(provider_id)
    warning = None
    if refresh or not cached or cached[0] < time.monotonic():
        try:
            discovered = await discover_models(provider, connections[0])
            if discovered:
                cached = (time.monotonic() + 300, discovered)
                MODEL_CACHE[provider_id] = cached
        except Exception:
            warning = 'Không tải được model trực tiếp; đang dùng danh mục hệ thống. Có thể thử làm mới lại.'
    if cached:
        models = [row for row in cached[1] if canonical(row['model_key']) not in disabled]
        source = 'provider_api' if not warning else 'cached_provider_api'
    else:
        models = [model_option(row.model_key, row.label) for row in rows if row.is_active]
        source = 'system_catalog'
    return {'models': models, 'source': source, 'warning': warning}


async def native_request(provider, connection, model, payload, stream):
    """Choose the destination from trusted server metadata, never a caller URL."""
    kind = protocol(provider)
    key = connection.api_key.strip()
    base = (provider.base_url or 'https://api.openai.com/v1').rstrip('/')
    headers = {'Content-Type': 'application/json'}
    body = dict(payload)
    if kind == 'antigravity':
        key = await TokenRefreshService.get_active_token(key)
        # Preserve the selected model/version; never silently downgrade it.
        body['model'] = model.removeprefix('ag/')
        body['project'] = await TokenRefreshService.get_project_id(key)
        url = 'https://daily-cloudcode-pa.googleapis.com/v1internal:' + (
            'streamGenerateContent?alt=sse' if stream else 'generateContent')
        headers.update({'Authorization': f'Bearer {key.removeprefix("Bearer ")}',
                        'User-Agent': 'antigravity/ide/2.11.0 darwin/arm64', 'x-request-source': 'local'})
    elif kind == 'google':
        url = 'https://generativelanguage.googleapis.com/v1beta/openai/chat/completions'
        headers['Authorization'] = f'Bearer {key}'
        body.update(model=model, stream=stream)
    elif kind == 'anthropic':
        url = f'{base}/messages'
        headers.update({'x-api-key': key, 'anthropic-version': '2023-06-01'})
        body.update(model=model, stream=stream)
    else:
        url = f'{base}/chat/completions'
        headers['Authorization'] = f'Bearer {key.removeprefix("Bearer ")}'
        body.update(model=model, stream=stream)
        for message in body.get('messages', []):
            if message.get('role') == 'developer':
                message['role'] = 'system'
    return url, headers, body


async def open_inference(db, provider_id, model, payload, stream):
    provider, connections, rows = await provider_state(db, provider_id)
    canonical = lambda key: key.removeprefix('ag/') if protocol(provider) == 'antigravity' else key
    active = {canonical(row.model_key) for row in rows if row.is_active}
    disabled = {canonical(row.model_key) for row in rows if not row.is_active}
    selected = canonical(model)
    if selected in disabled:
        raise HTTPException(400, 'Model đã bị tắt trong hệ thống.')
    if selected not in active:
        live = await get_models(db, provider_id)
        if selected not in {canonical(row['model_key']) for row in live['models']}:
            raise HTTPException(400, 'Model không thuộc danh sách khả dụng của provider đã chọn.')
    client = httpx.AsyncClient(timeout=None, follow_redirects=False)
    try:
        for connection in connections:
            try:
                url, headers, body = await native_request(provider, connection, model, payload, stream)
                response = await client.send(client.build_request('POST', url, headers=headers, json=body), stream=True)
            except Exception:
                continue
            if response.is_success:
                return client, response
            await response.aclose()
        raise HTTPException(502, 'Các kết nối của provider không phản hồi thành công. Hãy thử model/provider khác hoặc API cá nhân.')
    except BaseException:
        await client.aclose()
        raise
