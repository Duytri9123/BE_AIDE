"""Compact, transactionally maintained takeoff history metadata.

Revision ID: e93c7a102b64
Revises: d82f1a6b903e
"""
from alembic import op
import sqlalchemy as sa

revision = 'e93c7a102b64'
down_revision = 'd82f1a6b903e'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('analysis_summaries',
        sa.Column('id', sa.Integer(), sa.ForeignKey('analysis_iterations.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('session_id', sa.UUID(), nullable=False),
        sa.Column('iteration_number', sa.Integer(), nullable=False),
        sa.Column('trigger_type', sa.String(100), nullable=False),
        sa.Column('user_message', sa.Text()),
        sa.Column('files_analyzed', sa.JSON()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('has_devices', sa.Boolean(), nullable=False),
        sa.Column('devices', sa.JSON(), nullable=False),
        sa.Column('confidence', sa.JSON(), nullable=False))
    op.create_index('ix_summary_session_status_created_id', 'analysis_summaries',
                    ['session_id', 'status', 'created_at', 'id'])


def downgrade():
    op.drop_table('analysis_summaries')
