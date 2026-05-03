"""add_report_edit_all_permission

Revision ID: c4d5e6f7a8b9
Revises: b3f2a1c4d5e6
Create Date: 2026-05-03 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'c4d5e6f7a8b9'
down_revision: Union[str, Sequence[str], None] = 'b3f2a1c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _permission_exists(permission_key: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT EXISTS ("
            "SELECT 1 FROM incident_report_permissions "
            "WHERE permission_key = :key"
            ")"
        ),
        {"key": permission_key},
    )
    return result.scalar()


def _role_permission_exists(role_key: str, permission_key: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT EXISTS ("
            "SELECT 1 FROM incident_report_role_permissions "
            "WHERE role_key = :role AND permission_key = :perm"
            ")"
        ),
        {"role": role_key, "perm": permission_key},
    )
    return result.scalar()


def upgrade() -> None:
    if not _permission_exists("report:edit_all"):
        op.execute(
            "INSERT INTO incident_report_permissions (permission_key, permission_name, description, category) "
            "VALUES ('report:edit_all', '编辑所有报告', '编辑任意状态的任意报告', 'report')"
        )

    if not _role_permission_exists("admin", "report:edit_all"):
        op.execute(
            "INSERT INTO incident_report_role_permissions (role_key, permission_key) "
            "VALUES ('admin', 'report:edit_all')"
        )


def downgrade() -> None:
    op.execute(
        "DELETE FROM incident_report_role_permissions "
        "WHERE permission_key = 'report:edit_all'"
    )
    op.execute(
        "DELETE FROM incident_report_permissions "
        "WHERE permission_key = 'report:edit_all'"
    )
