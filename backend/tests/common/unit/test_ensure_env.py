"""ensure_env.py（部署引导脚本）的单元测试。

脚本位于仓库根 scripts/ 下、必须能用系统 python3 运行（不依赖任何第三方包），
因此这里用 importlib 按路径加载后测试其行为。
"""

import base64
import importlib.util
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
_SCRIPT = REPO_ROOT / "scripts" / "ensure_env.py"


def _load_script() -> Any:
    spec = importlib.util.spec_from_file_location("ensure_env_under_test", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def ensure_env() -> Any:
    return _load_script()


def _read(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        values[key.strip()] = value.strip()
    return values


def test_secret_generators_produce_strong_values(ensure_env: Any) -> None:
    gen = ensure_env.SECRET_GENERATORS
    assert len(gen["JWT_SECRET_KEY"]()) >= 32
    assert len(base64.b64decode(gen["SETTINGS_ENCRYPTION_KEY"]())) == 32
    assert len(gen["POSTGRES_PASSWORD"]()) >= 16
    assert len(gen["REDIS_PASSWORD"]()) >= 16


def test_prod_fills_missing_and_keeps_existing(ensure_env: Any, tmp_path: Path) -> None:
    target = tmp_path / "opt" / "dps" / ".env"
    target.parent.mkdir(parents=True)
    target.write_text("POSTGRES_PASSWORD=keep_me_unchanged\n", encoding="utf-8")

    assert ensure_env.ensure_prod(target) == 0

    values = _read(target)
    assert values["POSTGRES_PASSWORD"] == "keep_me_unchanged"  # 已有键绝不动
    assert len(values["JWT_SECRET_KEY"]) >= 32
    assert len(values["REDIS_PASSWORD"]) >= 16
    assert len(base64.b64decode(values["SETTINGS_ENCRYPTION_KEY"])) == 32


def test_prod_is_idempotent(ensure_env: Any, tmp_path: Path) -> None:
    target = tmp_path / ".env"
    ensure_env.ensure_prod(target)
    first = target.read_text(encoding="utf-8")

    ensure_env.ensure_prod(target)
    assert target.read_text(encoding="utf-8") == first  # 重复执行零改动


def test_prod_requires_path(ensure_env: Any) -> None:
    with pytest.raises(SystemExit):
        ensure_env.main(["--env", "prod"])


def test_dev_generates_two_files_with_same_passwords(ensure_env: Any, tmp_path: Path) -> None:
    ensure_env.ensure_dev(tmp_path)

    devcontainer = _read(tmp_path / ".devcontainer" / ".env")
    backend = _read(tmp_path / "backend" / ".env.dev")

    assert backend["REDIS_PASSWORD"] == devcontainer["REDIS_PASSWORD"]
    assert backend["REDIS_URL"] == f"redis://:{devcontainer['REDIS_PASSWORD']}@redis:6379"
    assert backend["DATABASE_URL"] == f"postgresql+asyncpg://admin:{devcontainer['POSTGRES_PASSWORD']}@db:5432/master"
    assert (
        backend["DPS_TEST_DATABASE_URL"]
        == f"postgresql+asyncpg://admin:{devcontainer['POSTGRES_PASSWORD']}@db:5432/dps_test"
    )
    assert len(base64.b64decode(backend["SETTINGS_ENCRYPTION_KEY"])) == 32


def test_dev_persists_jwt_key_across_runs(ensure_env: Any, tmp_path: Path) -> None:
    """JWT/ENCRYPTION 密钥必须持久化：重复运行不得重新生成（否则令牌全部失效）。"""
    ensure_env.ensure_dev(tmp_path)
    first = _read(tmp_path / "backend" / ".env.dev")

    ensure_env.ensure_dev(tmp_path)
    second = _read(tmp_path / "backend" / ".env.dev")

    assert second["JWT_SECRET_KEY"] == first["JWT_SECRET_KEY"]
    assert second["SETTINGS_ENCRYPTION_KEY"] == first["SETTINGS_ENCRYPTION_KEY"]
    assert second["DATABASE_URL"] == first["DATABASE_URL"]


def test_dev_preserves_ollama_base_url(ensure_env: Any, tmp_path: Path) -> None:
    backend_env = tmp_path / "backend" / ".env.dev"
    backend_env.parent.mkdir(parents=True)
    backend_env.write_text("OLLAMA_BASE_URL=http://ollama.local:11434\n", encoding="utf-8")

    ensure_env.ensure_dev(tmp_path)

    assert _read(backend_env)["OLLAMA_BASE_URL"] == "http://ollama.local:11434"
