"""Idempotent bootstrap for the editable built-in AI prompt templates."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.prompts import DEFAULT_PROMPT_TEMPLATES
from app.models.prompt_template import PromptTemplate


async def seed_default_prompt_templates(db: AsyncSession) -> None:
    """Create only missing templates; administrator edits are never overwritten."""
    for template in DEFAULT_PROMPT_TEMPLATES:
        exists = await db.scalar(
            select(PromptTemplate.id).where(PromptTemplate.type == template["type"]).limit(1)
        )
        if not exists:
            db.add(PromptTemplate(**template))
    await db.commit()
