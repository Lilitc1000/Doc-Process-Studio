"""sync_not_null_constraints

Revision ID: 51262756392c
Revises: c4d5e6f7a8b9
Create Date: 2026-09-14 09:41:05.571126

修正 10 处列的 NOT NULL 约束（users / chat_sessions / incident_* 系列）。

知识库（项目 / 文件夹 / 文档）已改为以 RAGFlow 为唯一真相源，
本迁移**不再创建任何 kb_* 表**；若库里仍存在历史遗留的 kb_* 表，
按下方"可选清理"说明处理即可，不影响应用运行。

收紧 NOT NULL 前先回填存量 NULL：b3f2a1c4d5e6 的 RBAC seed 未写入 created_at，
而历史 create_all 建的列允许 NULL，直接 SET NOT NULL 会因存量数据失败。

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '51262756392c'
down_revision: Union[str, Sequence[str], None] = 'c4d5e6f7a8b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 回填存量 NULL，避免 SET NOT NULL 失败
    op.execute("UPDATE users SET created_at = now() WHERE created_at IS NULL")
    op.execute("UPDATE users SET updated_at = now() WHERE updated_at IS NULL")
    op.execute("UPDATE chat_sessions SET created_at = now() WHERE created_at IS NULL")
    op.execute("UPDATE chat_sessions SET updated_at = now() WHERE updated_at IS NULL")
    op.execute("UPDATE incident_comments SET created_at = now() WHERE created_at IS NULL")
    op.execute("UPDATE incident_reports SET created_at = now() WHERE created_at IS NULL")
    op.execute("UPDATE incident_reports SET updated_at = now() WHERE updated_at IS NULL")
    op.execute("UPDATE incident_reports SET form_data = '{}'::jsonb WHERE form_data IS NULL")
    op.execute(
        "UPDATE incident_report_role_definitions SET created_at = now() WHERE created_at IS NULL"
    )
    op.execute(
        "UPDATE incident_report_user_roles SET assigned_at = now() WHERE assigned_at IS NULL"
    )

    op.alter_column('chat_sessions', 'created_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=False,
               existing_server_default=sa.text('now()'))
    op.alter_column('chat_sessions', 'updated_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=False,
               existing_server_default=sa.text('now()'))
    op.alter_column('incident_comments', 'created_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=False,
               existing_server_default=sa.text('now()'))
    op.alter_column('incident_report_role_definitions', 'created_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=False)
    op.alter_column('incident_report_user_roles', 'assigned_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=False)
    op.alter_column('incident_reports', 'form_data',
               existing_type=postgresql.JSONB(astext_type=sa.Text()),
               nullable=False)
    op.alter_column('incident_reports', 'created_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=False,
               existing_server_default=sa.text('now()'))
    op.alter_column('incident_reports', 'updated_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=False,
               existing_server_default=sa.text('now()'))
    op.alter_column('users', 'created_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=False,
               existing_server_default=sa.text('now()'))
    op.alter_column('users', 'updated_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=False,
               existing_server_default=sa.text('now()'))


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('users', 'updated_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=True,
               existing_server_default=sa.text('now()'))
    op.alter_column('users', 'created_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=True,
               existing_server_default=sa.text('now()'))
    op.alter_column('incident_reports', 'updated_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=True,
               existing_server_default=sa.text('now()'))
    op.alter_column('incident_reports', 'created_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=True,
               existing_server_default=sa.text('now()'))
    op.alter_column('incident_reports', 'form_data',
               existing_type=postgresql.JSONB(astext_type=sa.Text()),
               nullable=True)
    op.alter_column('incident_report_user_roles', 'assigned_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=True)
    op.alter_column('incident_report_role_definitions', 'created_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=True)
    op.alter_column('incident_comments', 'created_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=True,
               existing_server_default=sa.text('now()'))
    op.alter_column('chat_sessions', 'updated_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=True,
               existing_server_default=sa.text('now()'))
    op.alter_column('chat_sessions', 'created_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=True,
               existing_server_default=sa.text('now()'))
