"""Switch Codex provider to direct OpenAI API key authentication.

Revision ID: a91d3e7c5b42
Revises: f7c2b16e4a31
Create Date: 2026-09-10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a91d3e7c5b42"
down_revision: Union[str, None] = "f7c2b16e4a31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


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
    connections = sa.table(
        "ai_connections",
        sa.column("provider", sa.String),
        sa.column("name", sa.String),
        sa.column("auth_type", sa.String),
        sa.column("api_key", sa.String),
        sa.column("tag", sa.String),
    )

    connection.execute(
        providers.update().where(providers.c.id == "codex").values(
            name="Codex / OpenAI API",
            api_type="openai_compatible",
            base_url="https://api.openai.com/v1",
            description="Kết nối trực tiếp OpenAI API bằng Project API Key",
        )
    )
    connection.execute(
        connections.update().where(connections.c.provider == "codex").values(
            name="Codex / OpenAI API",
            auth_type="api_key",
            api_key=None,
            tag="OpenAI API",
        )
    )


def downgrade() -> None:
    pass
