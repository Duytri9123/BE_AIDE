"""Migrate existing Codex connections to official Codex App Server.

Revision ID: f7c2b16e4a31
Revises: c4f1a8e79d20
Create Date: 2026-09-10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f7c2b16e4a31"
down_revision: Union[str, None] = "c4f1a8e79d20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


MODELS = (
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
        sa.column("api_type", sa.String),
        sa.column("base_url", sa.String),
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
    connections = sa.table(
        "ai_connections",
        sa.column("provider", sa.String),
        sa.column("name", sa.String),
        sa.column("auth_type", sa.String),
        sa.column("api_key", sa.String),
        sa.column("selected_model", sa.String),
    )

    connection.execute(
        providers.update().where(providers.c.id == "codex").values(
            name="Codex (ChatGPT OAuth)",
            api_type="codex_app_server",
            base_url=None,
            description="Codex App Server chính thức, đăng nhập ChatGPT bằng device code",
        )
    )
    connection.execute(
        models.delete().where(
            models.c.provider_id == "codex", models.c.model_key.like("cx/%")
        )
    )
    for model_key, label, sort_order in MODELS:
        exists = connection.execute(
            sa.select(models.c.model_key).where(
                models.c.provider_id == "codex", models.c.model_key == model_key
            )
        ).first()
        if not exists:
            connection.execute(
                models.insert().values(
                    provider_id="codex",
                    model_key=model_key,
                    label=label,
                    is_active=True,
                    sort_order=sort_order,
                )
            )
    connection.execute(
        connections.update().where(connections.c.provider == "codex").values(
            auth_type="chatgpt_oauth", api_key="__codex_app_server__"
        )
    )
    connection.execute(
        connections.update()
        .where(connections.c.provider == "codex", connections.c.name.like("%9router%"))
        .values(name="Codex OAuth (App Server)")
    )
    for model_key, _, _ in MODELS:
        connection.execute(
            connections.update()
            .where(
                connections.c.provider == "codex",
                connections.c.selected_model == f"cx/{model_key}",
            )
            .values(selected_model=model_key)
        )


def downgrade() -> None:
    # The proxy carried credentials outside AIDE.  Do not recreate that unsafe
    # dependency automatically; retain the official provider configuration.
    pass
