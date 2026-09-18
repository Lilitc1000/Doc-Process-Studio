import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

from doc_process_studio.common.infrastructure.database import Base
import doc_process_studio.auth.infrastructure.persistence  # noqa: F401
import doc_process_studio.chat.infrastructure.persistence  # noqa: F401
import doc_process_studio.incident_report.infrastructure.persistence  # noqa: F401
# settings 模块：system_settings / system_secrets / user_settings 三张表。
# 少了这一行，autogenerate 看不到它们，会误判成库里多出来的表并生成 drop。
import doc_process_studio.settings.infrastructure.persistence  # noqa: F401

config = context.config

# 允许用环境变量覆盖 alembic.ini 里硬编码的连接串（迁移到测试库时必需）
if os.getenv("DATABASE_URL"):
    config.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    import asyncio

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
