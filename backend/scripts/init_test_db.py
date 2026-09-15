"""创建（或重置）后端持久化测试用的独立数据库 dps_test。

用法：
    uv run python scripts/init_test_db.py           # 不存在则创建
    uv run python scripts/init_test_db.py --drop    # 先删后建（库结构脏了时用）

说明：
- 目标库名取自 DPS_TEST_DATABASE_URL（默认 postgresql://admin:postgres_password@db:5432/dps_test）
- 建库动作必须连到维护库（默认同实例的 postgres 库）执行
- 测试表的创建/销毁由 pytest 夹具负责（会话开始 create_all、结束 drop_all），本脚本不建表
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

import asyncpg

DEFAULT_TEST_DSN = "postgresql://admin:postgres_password@db:5432/dps_test"
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


async def _main(drop: bool) -> None:
    test_dsn = _normalize(os.getenv("DPS_TEST_DATABASE_URL", DEFAULT_TEST_DSN))
    await _ensure_database(test_dsn, drop)
    sqlalchemy_dsn = test_dsn.replace("postgresql://", "postgresql+asyncpg://")
    print("[init_test_db] 运行持久化测试：")
    print(f'  DPS_TEST_DATABASE_URL="{sqlalchemy_dsn}" uv run pytest tests/persistence -m db')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="创建/重置后端测试数据库")
    parser.add_argument("--drop", action="store_true", help="先删除已有测试库再重建")
    args = parser.parse_args()
    try:
        asyncio.run(_main(args.drop))
    except OSError as exc:
        print(f"[init_test_db] 连接失败：{exc}", file=sys.stderr)
        raise SystemExit(1) from exc
