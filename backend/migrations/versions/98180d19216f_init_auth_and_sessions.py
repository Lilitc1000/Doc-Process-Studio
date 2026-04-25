"""init_auth_and_sessions

Revision ID: 98180d19216f
Revises:
Create Date: 2026-04-24 20:12:36.580512

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '98180d19216f'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('chat_sessions', 'snapshot',
               existing_type=sa.VARCHAR(),
               type_=postgresql.JSONB(astext_type=sa.Text()),
               existing_nullable=True,
               postgresql_using='snapshot::jsonb')
    op.create_index('idx_chat_sessions_updated_at', 'chat_sessions', ['updated_at'], unique=False)
    op.create_index('idx_chat_sessions_user_id', 'chat_sessions', ['user_id'], unique=False)
    op.create_foreign_key(None, 'chat_sessions', 'users', ['user_id'], ['user_id'], ondelete='CASCADE')
    op.alter_column('incident_report_sessions', 'snapshot',
               existing_type=sa.VARCHAR(),
               type_=postgresql.JSONB(astext_type=sa.Text()),
               existing_nullable=True,
               postgresql_using='snapshot::jsonb')
    op.create_index('idx_incident_report_sessions_updated_at', 'incident_report_sessions', ['updated_at'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_incident_report_sessions_updated_at', table_name='incident_report_sessions')
    op.alter_column('incident_report_sessions', 'snapshot',
               existing_type=postgresql.JSONB(astext_type=sa.Text()),
               type_=sa.VARCHAR(),
               existing_nullable=True)
    op.drop_constraint(None, 'chat_sessions', type_='foreignkey')
    op.drop_index('idx_chat_sessions_user_id', table_name='chat_sessions')
    op.drop_index('idx_chat_sessions_updated_at', table_name='chat_sessions')
    op.alter_column('chat_sessions', 'snapshot',
               existing_type=postgresql.JSONB(astext_type=sa.Text()),
               type_=sa.VARCHAR(),
               existing_nullable=True)
