"""ENV=prod 下 JWT_SECRET_KEY 的启动期校验。

密钥文件由 ``scripts/ensure_env.py`` 自动生成，这里验证最后一道防线：
即使有人绕过脚本、在 prod 下回落到仓库占位值/弱值，应用也必须拒绝启动。
"""

import pytest
from pydantic import ValidationError

from doc_process_studio.common.infrastructure.config import Settings

_PROD_PLACEHOLDER = "your-super-secret-key-change-in-production-min-32-chars"


def _build(*, jwt_secret_key: str) -> Settings:
    # _env_file=None：屏蔽 .env.dev / .env.dev.local，只看显式入参与进程环境
    return Settings(_env_file=None, jwt_secret_key=jwt_secret_key)  # type: ignore[call-arg]


def test_prod_rejects_placeholder(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV", "prod")
    with pytest.raises(ValidationError, match="JWT_SECRET_KEY"):
        _build(jwt_secret_key=_PROD_PLACEHOLDER)


def test_prod_rejects_short_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV", "prod")
    with pytest.raises(ValidationError, match="JWT_SECRET_KEY"):
        _build(jwt_secret_key="short")


def test_prod_accepts_strong_random_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV", "prod")
    settings = _build(jwt_secret_key="x" * 48)
    assert settings.jwt_secret_key == "x" * 48


def test_dev_does_not_enforce(monkeypatch: pytest.MonkeyPatch) -> None:
    """dev 保持宽松：占位值/弱值仍可用（真实密钥由 ensure_env.py 生成）。"""
    monkeypatch.setenv("ENV", "dev")
    settings = _build(jwt_secret_key="short")
    assert settings.jwt_secret_key == "short"
