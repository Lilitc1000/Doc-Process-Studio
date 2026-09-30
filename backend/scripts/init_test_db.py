"""创建（或重置）后端持久化测试用的独立数据库 dps_test。

用法：
    uv run python scripts/init_test_db.py --drop    # 先删后建（库结构脏了时用）

说明：
- 目标库名取自 DPS_TEST_DATABASE_URL（必须设置；.env.dev 已由 scripts/ensure_env.py 生成）
- **常规路径已不需要本脚本**：pytest 会话夹具检测到测试库不存在时会自动创建
  （仅限本地/开发库 host，见 tests/conftest.py 的 ensure_test_database）
- 本脚本保留的用途：--drop 重置一个脏了的测试库
- 建库动作必须连到维护库（默认同实例的 postgres 库）执行
- 测试表的创建/销毁由 pytest 夹具负责（会话开始 create_all、结束 drop_all），本脚本不建表
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

import asyncpg

MAINT_DB = "postgres"


def _normalize(dsn: str) -> str:
    """asyncpg 不认 sqlalchemy 的 +asyncpg 方言后缀。"""
    return dsn.replace("postgresql+asyncpg://", "postgresql://").replace("postgres+asyncpg://", "postgresql://")


def _maint_dsn(test_dsn: str) -> str:
    """把 DSN 的库名替换为维护库名。"""
    head, _, _ = test_dsn.rpartition("/")
    return f"{head}/{MAINT_DB}"


async def _ensure_database(test_dsn: str, drop: bool) -> None:
    db_name = test_dsn.rpartition("/")[2]
    if not db_name:
        raise SystemExit(f"无法从 DSN 解析数据库名：{test_dsn}")

    conn = await asyncpg.connect(_maint_dsn(test_dsn))
    try:
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", db_name)
        if exists and drop:
            await conn.execute(f'DROP DATABASE "{db_name}" WITH (FORCE)')
            exists = None
            print(f"[init_test_db] 已删除数据库 {db_name}")
        if exists:
            print(f"[init_test_db] 数据库 {db_name} 已存在，跳过创建")
        else:
            await conn.execute(f'CREATE DATABASE "{db_name}"')
            print(f"[init_test_db] 已创建数据库 {db_name}")
    finally:
        await conn.close()


def _resolve_test_dsn() -> str:
    """解析测试库 DSN：进程环境变量优先，其次 backend/.env.dev（脚本裸跑时的兜底）。"""
    from_env = os.getenv("DPS_TEST_DATABASE_URL", "").strip()
    if from_env:
        return from_env
    env_file = Path(__file__).resolve().parents[1] / ".env.dev"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("DPS_TEST_DATABASE_URL="):
                return line.split("=", 1)[1].strip()
    return ""


def _redact(dsn: str) -> str:
    """隐藏 DSN 中的密码段，用于日志/提示输出。"""
    head, sep, tail = dsn.rpartition("@")
    if not sep:
        return dsn
    scheme_end = head.find("://")
    prefix = head[: scheme_end + 3] if scheme_end != -1 else ""
    creds = head[scheme_end + 3 :] if scheme_end != -1 else head
    user = creds.split(":", 1)[0]
    return f"{prefix}{user}:***@{tail}"


async def _main(drop: bool) -> None:
    test_dsn = _normalize(_resolve_test_dsn())
    if not test_dsn:
        raise SystemExit(
            "未设置 DPS_TEST_DATABASE_URL，且 backend/.env.dev 中也没有该键"
            "（.env.dev 由 scripts/ensure_env.py 生成）。"
        )
    await _ensure_database(test_dsn, drop)
    sqlalchemy_dsn = test_dsn.replace("postgresql://", "postgresql+asyncpg://")
    print("[init_test_db] 运行持久化测试：")
    print(f'  DPS_TEST_DATABASE_URL="{_redact(sqlalchemy_dsn)}" uv run pytest tests/persistence -m db')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="创建/重置后端测试数据库")
    parser.add_argument("--drop", action="store_true", help="先删除已有测试库再重建")
    args = parser.parse_args()
    try:
        asyncio.run(_main(args.drop))
    except OSError as exc:
        print(f"[init_test_db] 连接失败：{exc}", file=sys.stderr)
        raise SystemExit(1) from exc
