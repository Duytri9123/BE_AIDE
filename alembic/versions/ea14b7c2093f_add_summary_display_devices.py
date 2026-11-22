"""Text-only saved devices for historical chat tables.

Revision ID: ea14b7c2093f
Revises: e93c7a102b64
"""
from alembic import op
import sqlalchemy as sa

revision = 'ea14b7c2093f'
down_revision = 'e93c7a102b64'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('analysis_summaries', sa.Column('display_devices', sa.JSON(),
                                               nullable=False, server_default='[]'))


def downgrade():
    op.drop_column('analysis_summaries', 'display_devices')
