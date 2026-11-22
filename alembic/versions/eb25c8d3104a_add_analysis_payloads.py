"""Lossless compressed read copies of saved takeoff results.

Revision ID: eb25c8d3104a
Revises: ea14b7c2093f
"""
from alembic import op
import sqlalchemy as sa

revision = 'eb25c8d3104a'
down_revision = 'ea14b7c2093f'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('analysis_payloads',
        sa.Column('id', sa.Integer(), sa.ForeignKey('analysis_iterations.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('payload', sa.LargeBinary(), nullable=False))


def downgrade():
    op.drop_table('analysis_payloads')
