"""user_role_and_settings_tables

Revision ID: d7f3a91b4c22
Revises: 51262756392c
Create Date: 2026-09-18 11:30:00.000000

为「系统级 RAGFlow 共享凭据 + 用户级偏好」建立存储：

1. ``users.role``      —— 全局角色（此前全局层没有任何角色概念）。
                          默认 ``member``，backfill ``username='admin'`` 为 ``admin``。
2. ``system_settings`` —— 系统级**非敏感**配置（key → JSON 标量/对象）。
3. ``system_secrets``  —— 系统级**密文**凭据（AES-256-GCM 密文 + key_id + 掩码尾串）。
                          与 system_settings 分表，是为了让"敏感值不可能被误序列化进 API 响应"
                          成为结构保证，而不是靠代码纪律。
4. ``user_settings``   —— 用户级**非敏感**偏好（JSONB），按 user_id 隔离。

不加唯一 admin 之外的角色：一期只需要区分 admin / 普通用户，用 ``role`` 列而非布尔，
是为了将来加 ``operator`` / ``auditor`` 时不必再迁移。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "d7f3a91b4c22"
down_revision: str | Sequence[str] | None = "51262756392c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ADMIN_ROLE = "admin"
MEMBER_ROLE = "member"


def _table_exists(table_name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name=:name)"
        ),
        {"name": table_name},
    )
    return bool(result.scalar())


def _column_exists(table_name: str, column_name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT EXISTS ("
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name=:t AND column_name=:c"
            ")"
        ),
        {"t": table_name, "c": column_name},
    )
    return bool(result.scalar())


def upgrade() -> None:
    """Upgrade schema."""
    # ---------------------------------------------------------------- users.role
    if not _column_exists("users", "role"):
        op.add_column(
            "users",
            sa.Column("role", sa.String(length=20), nullable=False, server_default=MEMBER_ROLE),
        )
        # 已有数据全部回落为 member（server_default 已保证），再把既有管理员账号提上来。
        op.execute(f"UPDATE users SET role = '{MEMBER_ROLE}' WHERE role IS NULL")
        op.execute(f"UPDATE users SET role = '{ADMIN_ROLE}' WHERE username = 'admin'")

    # ---------------------------------------------------------------- system_settings
    if not _table_exists("system_settings"):
        op.create_table(
            "system_settings",
            sa.Column("setting_key", sa.String(length=64), nullable=False),
            sa.Column("value_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.PrimaryKeyConstraint("setting_key"),
        )

    # ---------------------------------------------------------------- system_secrets
    if not _table_exists("system_secrets"):
        op.create_table(
            "system_secrets",
            sa.Column("secret_key", sa.String(length=64), nullable=False),
            # 格式：v1:<key_id>:<nonce_b64url>:<ciphertext_b64url>
            sa.Column("ciphertext", sa.Text(), nullable=False),
            sa.Column("key_id", sa.String(length=16), nullable=False),
            # 掩码展示用的尾串（仅当明文 >= 24 字符时写入），明文永不落库
            sa.Column("hint", sa.String(length=8), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.PrimaryKeyConstraint("secret_key"),
        )

    # ---------------------------------------------------------------- user_settings
    if not _table_exists("user_settings"):
        op.create_table(
            "user_settings",
            sa.Column("user_id", sa.String(length=32), nullable=False),
            sa.Column(
                "preferences",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
            # 每次写入 +1，作为「配置已变更」的信号（缓存失效 / 变更追踪）
            sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("user_id"),
        )


def downgrade() -> None:
    """Downgrade schema."""
    if _table_exists("user_settings"):
        op.drop_table("user_settings")
    if _table_exists("system_secrets"):
        op.drop_table("system_secrets")
    if _table_exists("system_settings"):
        op.drop_table("system_settings")
    if _column_exists("users", "role"):
        op.drop_column("users", "role")
