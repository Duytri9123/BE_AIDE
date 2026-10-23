"""Indexes matching relational API filters and stable pagination.

Revision ID: d82f1a6b903e
Revises: b1a4c9206d81
"""
from alembic import op

revision = 'd82f1a6b903e'
down_revision = 'b1a4c9206d81'
branch_labels = None
depends_on = None

INDEXES = [
    ('ix_sessions_project_created_id','conversation_sessions',['project_id','created_at','id']),
    ('ix_iterations_session_status_created_id','analysis_iterations',['session_id','status','created_at','id']),
    ('ix_iterations_session_number_id','analysis_iterations',['session_id','iteration_number','id']),
    ('ix_files_project_created_id','project_files',['project_id','created_at','id']),
    ('ix_payments_user_created_id','payments',['user_id','created_at','id']),
]


def upgrade():
    for name, table, columns in INDEXES:
        op.create_index(name, table, columns)


def downgrade():
    for name, table, columns in reversed(INDEXES):
        op.drop_index(name, table_name=table)
