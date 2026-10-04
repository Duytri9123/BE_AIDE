"""Add articles for website content.

Revision ID: b1a4c9206d81
Revises: a91d3e7c5b42
"""
from alembic import op
import sqlalchemy as sa

revision = "b1a4c9206d81"
down_revision = "a91d3e7c5b42"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "articles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("content_html", sa.Text(), nullable=False),
        sa.Column("cover_image_url", sa.String(2000), nullable=True),
        sa.Column("category", sa.String(255), nullable=True),
        sa.Column("meta_description", sa.String(500), nullable=True),
        sa.Column("source_url", sa.String(2000), nullable=True),
        sa.Column("published", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("slug"), sa.UniqueConstraint("source_url"),
    )
    op.create_index("ix_articles_slug", "articles", ["slug"])
    op.create_index("ix_articles_category", "articles", ["category"])
    op.create_index("ix_articles_published", "articles", ["published"])


def downgrade():
    op.drop_index("ix_articles_published", table_name="articles")
    op.drop_index("ix_articles_category", table_name="articles")
    op.drop_index("ix_articles_slug", table_name="articles")
    op.drop_table("articles")
