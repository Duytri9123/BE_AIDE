"""Add the official Codex App Server OAuth provider.

Revision ID: c4f1a8e79d20
Revises: 8d3a6f4c2b11
Create Date: 2026-09-09
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c4f1a8e79d20"
down_revision: Union[str, None] = "8d3a6f4c2b11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CODEX_MODELS = (
    ("gpt-6-astra", "GPT-6 Astra", 1),
    ("gpt-5.6-sol", "GPT-5.6 Sol", 2),
    ("gpt-5.6-terra", "GPT-5.6 Terra", 3),
    ("gpt-5.6-luna", "GPT-5.6 Luna", 4),
    ("gpt-5.5", "GPT-5.5", 5),
)


def upgrade() -> None:
    connection = op.get_bind()
    providers = sa.table(
        "ai_providers",
        sa.column("id", sa.String),
        sa.column("name", sa.String),
        sa.column("slug", sa.String),
        sa.column("api_type", sa.String),
        sa.column("base_url", sa.String),
        sa.column("description", sa.String),
        sa.column("icon", sa.String),
        sa.column("is_active", sa.Boolean),
        sa.column("sort_order", sa.Integer),
    )
    models = sa.table(
        "ai_provider_models",
        sa.column("provider_id", sa.String),
        sa.column("model_key", sa.String),
        sa.column("label", sa.String),
        sa.column("is_active", sa.Boolean),
        sa.column("sort_order", sa.Integer),
    )

    existing = connection.execute(
        sa.select(providers.c.id).where(providers.c.id == "codex")
    ).first()
    values = {
        "name": "Codex (ChatGPT OAuth)",
        "slug": "codex",
        "api_type": "codex_app_server",
        "base_url": None,
        "description": "Codex App Server chính thức, đăng nhập ChatGPT bằng device code",
        "icon": "/admin/static/providers/codex.png",
        "is_active": True,
        "sort_order": 1,
    }
    if existing:
        connection.execute(providers.update().where(providers.c.id == "codex").values(**values))
    else:
        connection.execute(providers.insert().values(id="codex", **values))

    for model_key, label, sort_order in CODEX_MODELS:
        model_exists = connection.execute(
            sa.select(models.c.model_key)
            .where(models.c.provider_id == "codex")
            .where(models.c.model_key == model_key)
        ).first()
        model_values = {"label": label, "is_active": True, "sort_order": sort_order}
        if model_exists:
            connection.execute(
                models.update()
                .where(models.c.provider_id == "codex")
                .where(models.c.model_key == model_key)
                .values(**model_values)
            )
        else:
            connection.execute(models.insert().values(provider_id="codex", model_key=model_key, **model_values))


def downgrade() -> None:
    connection = op.get_bind()
    providers = sa.table("ai_providers", sa.column("id", sa.String))
    connection.execute(providers.delete().where(providers.c.id == "codex"))
