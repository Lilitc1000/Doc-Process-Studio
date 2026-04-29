"""rbac_role_management

Revision ID: b3f2a1c4d5e6
Revises: 8aaa922367cf
Create Date: 2026-04-27 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'b3f2a1c4d5e6'
down_revision: Union[str, Sequence[str], None] = '8aaa922367cf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table_name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT EXISTS ("
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name=:name"
            ")"
        ),
        {"name": table_name},
    )
    return result.scalar()


def _table_has_rows(table_name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(sa.text(f"SELECT EXISTS (SELECT 1 FROM {table_name} LIMIT 1)"))
    return result.scalar()


def upgrade() -> None:
    if not _table_exists("incident_report_role_definitions"):
        op.create_table('incident_report_role_definitions',
            sa.Column('role_key', sa.String(length=20), nullable=False),
            sa.Column('role_name', sa.String(length=50), nullable=False),
            sa.Column('description', sa.String(length=200), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint('role_key'),
        )

    if not _table_exists("incident_report_permissions"):
        op.create_table('incident_report_permissions',
            sa.Column('permission_key', sa.String(length=50), nullable=False),
            sa.Column('permission_name', sa.String(length=50), nullable=False),
            sa.Column('description', sa.String(length=200), nullable=True),
            sa.Column('category', sa.String(length=20), nullable=False),
            sa.PrimaryKeyConstraint('permission_key'),
        )

    if not _table_exists("incident_report_user_roles"):
        op.create_table('incident_report_user_roles',
            sa.Column('id', sa.String(length=32), nullable=False),
            sa.Column('user_id', sa.String(length=32), nullable=False),
            sa.Column('role_key', sa.String(length=20), nullable=False),
            sa.Column('assigned_by', sa.String(length=32), nullable=True),
            sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ),
            sa.ForeignKeyConstraint(['assigned_by'], ['users.user_id'], ),
            sa.ForeignKeyConstraint(['role_key'], ['incident_report_role_definitions.role_key'], ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('user_id', 'role_key', name='uq_user_role'),
        )

    if not _table_exists("incident_report_role_permissions"):
        op.create_table('incident_report_role_permissions',
            sa.Column('role_key', sa.String(length=20), nullable=False),
            sa.Column('permission_key', sa.String(length=50), nullable=False),
            sa.ForeignKeyConstraint(['role_key'], ['incident_report_role_definitions.role_key'], ),
            sa.ForeignKeyConstraint(['permission_key'], ['incident_report_permissions.permission_key'], ),
            sa.PrimaryKeyConstraint('role_key', 'permission_key'),
        )

    if not _table_has_rows("incident_report_role_definitions"):
        op.execute(
            "INSERT INTO incident_report_role_definitions (role_key, role_name, description) VALUES "
            "('admin', '管理员', '所有权限 + 角色分配 + 系统配置 + 数据导出'), "
            "('verifier', '审核人', '审核待审核报告、查看所有报告、分配处理人'), "
            "('handler', '处理人', '查看分配给自己的报告、更新处理进度、关闭报告'), "
            "('reporter', '报告人', '创建报告、编辑自己的草稿/被驳回报告、提交审核'), "
            "('viewer', '观察者', '仅查看报告列表和详情，无操作权限')"
        )

    if not _table_has_rows("incident_report_permissions"):
        op.execute(
            "INSERT INTO incident_report_permissions (permission_key, permission_name, description, category) VALUES "
            "('report:create', '创建报告', '创建新的事故报告', 'report'), "
            "('report:edit_own', '编辑自己的报告', '编辑自己创建的草稿或被驳回的报告', 'report'), "
            "('report:submit', '提交审核', '将报告提交审核', 'report'), "
            "('report:view', '查看报告', '查看报告列表和详情', 'report'), "
            "('report:view_all', '查看所有报告', '查看所有用户的报告', 'report'), "
            "('report:edit_assigned', '编辑被指派的报告', '编辑被指派给自己处理的报告', 'report'), "
            "('report:close_assigned', '关闭被指派的报告', '关闭被指派给自己处理的报告', 'report'), "
            "('report:audit', '审核报告', '审核待审核报告（批准/驳回）', 'report'), "
            "('report:assign', '分配处理人', '为已批准的报告分配处理人', 'report'), "
            "('report:delete', '删除报告', '删除任意状态的报告', 'report'), "
            "('report:reopen', '重新打开报告', '重新打开已关闭的报告', 'report'), "
            "('role:manage', '角色管理', '分配和撤销用户角色', 'role'), "
            "('system:config', '系统配置', '事故报告系统配置管理', 'system'), "
            "('data:export', '数据导出', '导出事故报告数据', 'data'), "
            "('analytics:view', '查看统计分析', '查看事故报告统计分析数据', 'analytics')"
        )

    if not _table_has_rows("incident_report_role_permissions"):
        op.execute(
            "INSERT INTO incident_report_role_permissions (role_key, permission_key) VALUES "
            "('viewer', 'report:view'), "
            "('viewer', 'analytics:view'), "
            "('reporter', 'report:view'), "
            "('reporter', 'report:create'), "
            "('reporter', 'report:edit_own'), "
            "('reporter', 'report:submit'), "
            "('reporter', 'analytics:view'), "
            "('handler', 'report:view'), "
            "('handler', 'report:view_all'), "
            "('handler', 'report:edit_assigned'), "
            "('handler', 'report:close_assigned'), "
            "('handler', 'analytics:view'), "
            "('verifier', 'report:view'), "
            "('verifier', 'report:view_all'), "
            "('verifier', 'report:audit'), "
            "('verifier', 'report:assign'), "
            "('verifier', 'analytics:view'), "
            "('admin', 'report:create'), "
            "('admin', 'report:edit_own'), "
            "('admin', 'report:submit'), "
            "('admin', 'report:view'), "
            "('admin', 'report:view_all'), "
            "('admin', 'report:edit_assigned'), "
            "('admin', 'report:close_assigned'), "
            "('admin', 'report:audit'), "
            "('admin', 'report:assign'), "
            "('admin', 'report:delete'), "
            "('admin', 'report:reopen'), "
            "('admin', 'role:manage'), "
            "('admin', 'system:config'), "
            "('admin', 'data:export'), "
            "('admin', 'analytics:view')"
        )

    if _table_exists("incident_report_roles"):
        conn = op.get_bind()
        result = conn.execute(sa.text("SELECT EXISTS (SELECT 1 FROM incident_report_roles LIMIT 1)"))
        has_old_data = result.scalar()
        if has_old_data:
            op.execute(
                "INSERT INTO incident_report_user_roles (id, user_id, role_key, assigned_by, assigned_at) "
                "SELECT 'migrated_' || user_id || '_' || role, user_id, role, assigned_by, assigned_at "
                "FROM incident_report_roles "
                "ON CONFLICT DO NOTHING"
            )
        op.drop_table('incident_report_roles')


def downgrade() -> None:
    op.create_table('incident_report_roles',
        sa.Column('user_id', sa.String(length=32), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('assigned_by', sa.String(length=32), nullable=True),
        sa.Column('assigned_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['assigned_by'], ['users.user_id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ),
        sa.PrimaryKeyConstraint('user_id', 'role'),
    )

    op.execute(
        "INSERT INTO incident_report_roles (user_id, role, assigned_by, assigned_at) "
        "SELECT user_id, role_key, assigned_by, assigned_at "
        "FROM incident_report_user_roles"
    )

    op.drop_table('incident_report_role_permissions')
    op.drop_table('incident_report_user_roles')
    op.drop_table('incident_report_permissions')
    op.drop_table('incident_report_role_definitions')
