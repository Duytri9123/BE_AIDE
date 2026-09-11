"""Resolve AI prompts from the administrator-managed prompt template store."""
from typing import Mapping, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.prompt_template import PromptTemplate


class PromptTemplateService:
    """Keeps prompt content editable without a code deployment."""

    @staticmethod
    async def get_active_content(
        db: Optional[AsyncSession], template_type: str, fallback: str
    ) -> str:
        if db is None:
            raise RuntimeError(
                "Không thể tải PromptTemplate từ BE vì không có phiên cơ sở dữ liệu."
            )

        result = await db.execute(
            select(PromptTemplate.content)
            .where(
                PromptTemplate.type == template_type,
                PromptTemplate.is_active.is_(True),
            )
            .order_by(PromptTemplate.version.desc(), PromptTemplate.id.desc())
            .limit(1)
        )
        content = result.scalar_one_or_none()
        if not content:
            raise RuntimeError(
                f"Chưa có PromptTemplate đang hoạt động cho loại '{template_type}' trong BE."
            )
        return content

    @classmethod
    async def render(
        cls,
        db: Optional[AsyncSession],
        template_type: str,
        fallback: str,
        context: Optional[Mapping[str, object]] = None,
    ) -> str:
        content = await cls.get_active_content(db, template_type, fallback)
        if not context:
            return content
        # Replace only declared placeholders. Unlike ``str.format``, this keeps
        # ordinary JSON braces in an Admin-edited prompt untouched.
        rendered = content
        for key, value in context.items():
            rendered = rendered.replace("{" + str(key) + "}", str(value))
        # Built-in CAD templates historically escaped JSON braces for
        # ``str.format``; normalize those when they are used as fallbacks.
        return rendered.replace("{{", "{").replace("}}", "}")
