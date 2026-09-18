"""settings 模块 ORM 映射包。

**必须在这里 re-export**：`migrations/env.py` 与 `tests/conftest.py` 都是靠
`import doc_process_studio.settings.infrastructure.persistence` 这一行来完成
`Base.metadata` 注册的。少了这段导出，`alembic revision --autogenerate` 会把
`system_settings` / `system_secrets` / `user_settings` 三张表误判成
"库里多出来的表"，直接生成 `drop_table`（已实测复现过）。
"""

from .models import SystemSecret, SystemSetting, UserSettings

__all__ = [
    "SystemSecret",
    "SystemSetting",
    "UserSettings",
]
