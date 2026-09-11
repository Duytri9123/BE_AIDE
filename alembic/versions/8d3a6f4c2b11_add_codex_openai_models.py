"""Add the OpenAI models exposed by Codex.

Revision ID: 8d3a6f4c2b11
Revises: e7562d5af48f
Create Date: 2026-09-09
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8d3a6f4c2b11"
down_revision: Union[str, None] = "e7562d5af48f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


OPENAI_MODELS = (
    ("gpt-6-astra", "GPT-6 Astra", 1),
    ("gpt-5.6-sol", "GPT-5.6 Sol", 2),
    ("gpt-5.6-terra", "GPT-5.6 Terra", 3),
    ("gpt-5.6-luna", "GPT-5.6 Luna", 4),
    ("gpt-5.5", "GPT-5.5", 5),
)

LEGACY_OPENAI_MODELS = ("gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "o3-mini")


def upgrade() -> None:
    connection = op.get_bind()
    provider = sa.table(
        "ai_providers",
        sa.column("id", sa.String),
        sa.column("description", sa.String),
    )
    models = sa.table(
        "ai_provider_models",
        sa.column("provider_id", sa.String),
        sa.column("model_key", sa.String),
        sa.column("label", sa.String),
        sa.column("is_active", sa.Boolean),
        sa.column("sort_order", sa.Integer),
    )

    connection.execute(
        provider.update()
        .where(provider.c.id == "openai")
        .values(description="Các model OpenAI dùng trong Codex — hỗ trợ suy luận, lập trình, hình ảnh và tài liệu kỹ thuật")
    )
    connection.execute(
        models.update()
        .where(models.c.provider_id == "openai")
        .where(models.c.model_key.in_(LEGACY_OPENAI_MODELS))
        .values(is_active=False)
    )

    for model_key, label, sort_order in OPENAI_MODELS:
        result = connection.execute(
            sa.select(models.c.model_key)
            .where(models.c.provider_id == "openai")
            .where(models.c.model_key == model_key)
        ).first()
        values = {"label": label, "is_active": True, "sort_order": sort_order}
        if result:
            connection.execute(
                models.update()
                .where(models.c.provider_id == "openai")
                .where(models.c.model_key == model_key)
                .values(**values)
            )
        else:
            connection.execute(
                models.insert().values(
                    provider_id="openai",
                    model_key=model_key,
                    **values,
                )
            )


def downgrade() -> None:
    connection = op.get_bind()
    models = sa.table(
        "ai_provider_models",
        sa.column("provider_id", sa.String),
        sa.column("model_key", sa.String),
        sa.column("is_active", sa.Boolean),
    )
    connection.execute(
        models.delete()
        .where(models.c.provider_id == "openai")
        .where(models.c.model_key.in_(tuple(model[0] for model in OPENAI_MODELS)))
    )
    connection.execute(
        models.update()
        .where(models.c.provider_id == "openai")
        .where(models.c.model_key.in_(LEGACY_OPENAI_MODELS))
        .values(is_active=True)
    )
