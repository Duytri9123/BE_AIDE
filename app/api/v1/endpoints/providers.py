from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.db.session import get_db
from app.models.ai_provider import AiProvider
from app.models.ai_provider_model import AiProviderModel
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()


class AiModelOut(BaseModel):
    id: int
    model_key: str
    label: str
    sort_order: int

    class Config:
        from_attributes = True


class AiProviderOut(BaseModel):
    id: str
    name: str
    slug: str
    icon: Optional[str] = None
    description: Optional[str] = None
    api_type: str
    base_url: Optional[str] = None
    is_active: bool
    sort_order: int
    models: List[AiModelOut] = []

    class Config:
        from_attributes = True


class AiPriorityModelOut(AiModelOut):
    provider_id: str
    provider_name: str
    provider_icon: Optional[str] = None


@router.get("", response_model=List[AiProviderOut])
async def get_providers(db: AsyncSession = Depends(get_db)):
    """Lấy danh sách AI providers kèm icon và model (active)"""
    stmt = (
        select(AiProvider)
        .options(
            selectinload(
                AiProvider.models.and_(AiProviderModel.is_active.is_(True))
            )
        )
        .where(AiProvider.is_active == True)
        .order_by(AiProvider.sort_order)
    )
    result = await db.execute(stmt)
    providers = result.scalars().all()
    return providers


@router.get("/priority-models", response_model=List[AiPriorityModelOut])
async def get_priority_models(db: AsyncSession = Depends(get_db)):
    """Danh sách model AI để thực thi, chỉ gồm provider/model đang hoạt động."""
    stmt = (
        select(AiProviderModel, AiProvider)
        .join(AiProvider, AiProvider.id == AiProviderModel.provider_id)
        .where(
            AiProvider.is_active.is_(True),
            AiProviderModel.is_active.is_(True),
        )
        .order_by(AiProviderModel.sort_order, AiProviderModel.id)
    )
    result = await db.execute(stmt)
    return [
        AiPriorityModelOut(
            id=model.id,
            model_key=model.model_key,
            label=model.label,
            sort_order=model.sort_order,
            provider_id=provider.id,
            provider_name=provider.name,
            provider_icon=provider.icon,
        )
        for model, provider in result.all()
    ]


@router.get("/{provider_id}/models", response_model=List[AiModelOut])
async def get_provider_models(provider_id: str, db: AsyncSession = Depends(get_db)):
    """Danh sách model đang hoạt động của một provider đang hoạt động."""
    stmt = (
        select(AiProviderModel)
        .join(AiProvider, AiProvider.id == AiProviderModel.provider_id)
        .where(
            AiProviderModel.provider_id == provider_id,
            AiProviderModel.is_active.is_(True),
            AiProvider.is_active.is_(True),
        )
        .order_by(AiProviderModel.sort_order)
    )
    result = await db.execute(stmt)
    models = result.scalars().all()
    return models
