#!/usr/bin/env python3
"""部署引导：确保环境密钥文件存在且完整（缺失的键自动生成，已有的键绝不覆盖）。

用法（在仓库根目录，用系统 python3 即可，无需任何第三方依赖）：
  生产（部署机，文件须在 rsync 同步目录之外）:
      python3 scripts/ensure_env.py --env prod --path /opt/dps/.env
  开发（一次生成两份：compose 插值文件 + 应用配置文件）:
      python3 scripts/ensure_env.py --env dev

原则（红线）：
- **只补缺，绝不覆盖**：文件里已有的键一个字节都不动。生成后的文件是唯一真相源，
  删除后重新生成会导致密码与既有数据卷错位（postgres 密码只在数据卷首次初始化时生效）。
  请像备份私钥一样备份这些文件。
- 随机源使用 secrets（CSPRNG）；日志只打印"生成了哪些键"，绝不打印值。
- 原子写（临时文件 + rename），POSIX 下权限 600。

dev 模式说明：
- ``.devcontainer/.env``      —— compose 插值用（VS Code 在该目录执行 compose，自动读取），
                                只含 db/redis 需要的基础设施密码。
- ``backend/.env.dev``        —— 应用配置，**派生文件**：每次运行按 .devcontainer/.env 中的
                                密码重新渲染（含拼好密码的 DATABASE_URL / REDIS_URL）。
                                不要手工编辑它——手工定制请用 ``backend/.env.dev.local``
                                （pydantic 两段式加载中 .local 优先级更高，且不入库）。
"""

from __future__ import annotations

import argparse
import base64
import os
import secrets
import stat
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# 生成后写进密钥文件的基础设施密钥（键名 -> 生成函数）
SECRET_GENERATORS = {
    "POSTGRES_PASSWORD": lambda: secrets.token_urlsafe(24),
    "REDIS_PASSWORD": lambda: secrets.token_urlsafe(24),
    "JWT_SECRET_KEY": lambda: secrets.token_urlsafe(48),
    "SETTINGS_ENCRYPTION_KEY": lambda: base64.b64encode(os.urandom(32)).decode(),
}

# dev 的 backend/.env.dev 渲染模板（值里的 {POSTGRES_PASSWORD}/{REDIS_PASSWORD}/
# {JWT_SECRET_KEY}/{SETTINGS_ENCRYPTION_KEY} 取自 .devcontainer/.env，同源一致）
DEV_BACKEND_TEMPLATE = """\
# 本文件由 scripts/ensure_env.py 生成（派生自 .devcontainer/.env），不要手工编辑；
# 手工定制请用 backend/.env.dev.local（不入库，且优先级更高）。
OLLAMA_BASE_URL={ollama_base_url}
REDIS_URL=redis://:{redis_password}@redis:6379
REDIS_PASSWORD={redis_password}
DATABASE_URL=postgresql+asyncpg://admin:{postgres_password}@db:5432/master
DPS_TEST_DATABASE_URL=postgresql+asyncpg://admin:{postgres_password}@db:5432/dps_test
JWT_SECRET_KEY={jwt_secret_key}
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
SETTINGS_ENCRYPTION_KEY={settings_encryption_key}
"""

DEFAULT_DEV_OLLAMA_BASE_URL = "http://59.152.224.254:8081"


def parse_env_keys(path: Path) -> set[str]:
    """收集 env 文件中已存在的键名（忽略注释与空行）。"""
    keys: set[str] = set()
    if not path.exists():
        return keys
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        keys.add(stripped.split("=", 1)[0].strip())
    return keys


def append_missing(path: Path, needed: list[str], generated: dict[str, str]) -> list[str]:
    """把文件中缺失的键追加到文件末尾；返回本次新生成的键名列表。

    文件里已有的键保持原样（连同一行都不改），这是"只补缺"红线的实现。
    """
    existing = parse_env_keys(path)
    missing = [key for key in needed if key not in existing]
    if not missing:
        return []

    existed_before = path.exists()
    if not existed_before:
        path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    if existed_before and path.read_text(encoding="utf-8").strip():
        lines.append("")
    for key in missing:
        generated[key] = SECRET_GENERATORS[key]()
        lines.append(f"{key}={generated[key]}")
    with path.open("a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    _restrict_permissions(path)
    return missing


def write_atomic(path: Path, content: str) -> None:
    """原子写：先写临时文件再 rename，避免半截文件被消费。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)
    _restrict_permissions(path)


def _restrict_permissions(path: Path) -> None:
    """POSIX 下收紧为 600；Windows 无 chmod 语义，静默跳过。"""
    if os.name == "posix":
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)


def ensure_prod(path: Path) -> int:
    """生产模式：向部署机 .env 补齐 4 个基础设施密钥（缺失才生成）。"""
    generated: dict[str, str] = {}
    missing = append_missing(
        path,
        needed=list(SECRET_GENERATORS),
        generated=generated,
    )
    print(f"[ensure_env] 文件: {path}")
    if missing:
        print(f"[ensure_env] 本次生成: {', '.join(missing)}")
    else:
        print("[ensure_env] 全部密钥已存在，未做任何修改")
    print("[ensure_env] 红线：该文件是唯一真相源，请备份且切勿删除后重新生成。")
    return 0


def ensure_dev(repo_root: Path) -> int:
    """开发模式：生成 .devcontainer/.env（compose 插值 + 密钥真相源）并派生 backend/.env.dev。

    4 个密钥全部以 .devcontainer/.env 为真相源（JWT/ENCRYPTION 虽然 compose 不消费，
    但必须持久化在这里，否则每次运行会重新生成、令牌全部失效）。
    """
    devcontainer_env = repo_root / ".devcontainer" / ".env"
    backend_env = repo_root / "backend" / ".env.dev"

    generated: dict[str, str] = {}
    missing = append_missing(
        devcontainer_env,
        needed=list(SECRET_GENERATORS),
        generated=generated,
    )
    print(f"[ensure_env] 文件: {devcontainer_env}")
    if missing:
        print(f"[ensure_env] 本次生成: {', '.join(missing)}")
    else:
        print("[ensure_env] 全部密钥已存在，未做任何修改")

    # 渲染 backend/.env.dev（派生文件：整文件重写，密码与 compose 插值同源）
    values = _read_env_file(devcontainer_env)
    ollama_base_url = DEFAULT_DEV_OLLAMA_BASE_URL
    if backend_env.exists():
        for line in backend_env.read_text(encoding="utf-8").splitlines():
            if line.startswith("OLLAMA_BASE_URL="):
                ollama_base_url = line.split("=", 1)[1].strip() or ollama_base_url
    content = DEV_BACKEND_TEMPLATE.format(
        ollama_base_url=ollama_base_url,
        postgres_password=values["POSTGRES_PASSWORD"],
        redis_password=values["REDIS_PASSWORD"],
        jwt_secret_key=values["JWT_SECRET_KEY"],
        settings_encryption_key=values["SETTINGS_ENCRYPTION_KEY"],
    )
    write_atomic(backend_env, content)
    print(f"[ensure_env] 文件: {backend_env}（派生重写，密码同源）")
    print("[ensure_env] 提示：若 postgres 数据卷已用旧密码初始化，需执行一次")
    print("[ensure_env]   ALTER USER 同步卷内密码（见 docs）；redis 密码重启容器即生效。")
    return 0


def _read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        values[key.strip()] = value.strip()
    return values


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成/补齐环境密钥文件（只补缺，绝不覆盖）")
    parser.add_argument("--env", choices=["prod", "dev"], required=True, help="目标环境")
    parser.add_argument("--path", type=Path, default=None, help="生产密钥文件路径（prod 必填）")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT, help="仓库根目录（dev 用，默认自动定位）")
    args = parser.parse_args(argv)

    if args.env == "prod":
        if args.path is None:
            parser.error("--env prod 需要显式指定 --path（如 /opt/dps/.env，务必放在 rsync 目录之外）")
        return ensure_prod(args.path)
    return ensure_dev(args.repo_root)


if __name__ == "__main__":
    sys.exit(main())
