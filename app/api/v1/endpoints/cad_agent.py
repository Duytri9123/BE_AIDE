"""Authenticated CAD-agent access to configured AI providers."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import raiseload

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.ai_provider import AiProvider
from app.services.ai.cad_agent_gateway import SUPPORTED_TYPES, get_models, open_inference, protocol

router = APIRouter(dependencies=[Depends(get_current_active_user)])


@router.get('/providers')
async def providers(db=Depends(get_db)):
    from app.models.ai_connection import AiConnection
    from app.models.ai_provider_model import AiProviderModel
    usable = select(AiConnection.id).where(
        AiConnection.provider == AiProvider.id, AiConnection.is_active.is_(True),
        AiConnection.api_key.isnot(None), AiConnection.api_key != '',
        AiConnection.status.notin_(['inactive', 'rate_limited'])
    ).exists()
    rows = (await db.execute(select(AiProvider).options(raiseload("*")).where(
        AiProvider.is_active.is_(True), AiProvider.api_type.in_(SUPPORTED_TYPES), usable
    ).order_by(AiProvider.sort_order, AiProvider.id))).scalars().all()
    ids = [p.id for p in rows]
    models = (await db.execute(select(AiProviderModel).where(
        AiProviderModel.provider_id.in_(ids), AiProviderModel.is_active.is_(True)
    ).order_by(AiProviderModel.sort_order, AiProviderModel.id))).scalars().all() if ids else []
    grouped = {}
    for model in models:
        grouped.setdefault(model.provider_id, []).append(model)
    from app.services.ai.cad_agent_gateway import model_option
    return [{'id': p.id, 'name': p.name, 'protocol': protocol(p),
             'models': [model_option(m.model_key, m.label) for m in grouped.get(p.id, [])]}
            for p in rows]


@router.get('/providers/{provider_id}/models')
async def models(provider_id: str, refresh: bool = False, db=Depends(get_db)):
    return await get_models(db, provider_id, refresh)


class InferenceRequest(BaseModel):
    model: str = Field(min_length=1, max_length=255)
    payload: dict
    stream: bool = True


@router.post('/providers/{provider_id}/inference')
async def inference(provider_id: str, request: InferenceRequest, db=Depends(get_db)):
    client, response = await open_inference(db, provider_id, request.model, request.payload, request.stream)

    async def content():
        try:
            async for chunk in response.aiter_bytes():
                yield chunk
        finally:
            await response.aclose()
            await client.aclose()

    return StreamingResponse(content(), media_type=response.headers.get('content-type',
        'text/event-stream' if request.stream else 'application/json'),
        headers={'Cache-Control': 'no-store', 'X-Accel-Buffering': 'no'})
