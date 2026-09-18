"""敏感凭据的对称加密工具（AES-256-GCM / AEAD）。

用途：把系统级凭据（如 RAGFlow API Key）加密后落库，避免"脱库即明文"。

密文格式（自描述，为将来主密钥轮换预留）::

    v1:<key_id>:<nonce_b64url>:<ciphertext_b64url>

- ``v1``         格式版本；将来换算法时新增 ``v2``，旧密文仍可解
- ``key_id``     主密钥标识，解密时据此选密钥，从而支持多密钥并存
- ``nonce``      12 字节随机数（GCM 标准长度），每次加密都重新生成
- ``ciphertext`` 密文 + 16 字节 GCM 认证标签

为什么选 AES-256-GCM 而不是 Fernet：

- GCM 是 AEAD 且支持 AAD。本项目把"这条密文属于哪个逻辑位置"（如
  ``ragflow.api_key``）作为 AAD 绑进认证，密文被搬运到别的行、或有人手工
  UPDATE 改归属，解密会直接失败。Fernet 没有 AAD，要达到同样效果只能自己
  再叠一层 HMAC。
- 避开 Fernet 的 AES-128-CBC 与 32-bit 时间戳设计债。

**能力边界（不要误解）**：这是对称加密，服务端必须能解出明文才能调用 RAGFlow。
因此它防的是"数据库脱库 / 备份泄露后直接读到密钥"，防不住"拿到服务器权限的人"。
"""

from __future__ import annotations

import base64
import binascii
import logging
import os
import re
from functools import lru_cache

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

logger = logging.getLogger(__name__)

_VERSION = "v1"
_NONCE_BYTES = 12
_KEY_BYTES = 32
_KEY_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,16}$")
_HEX_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")

# dev 兜底派生用的固定 salt。改动它会让既有 dev 密文全部解不开。
_DEV_KDF_SALT = b"doc-process-studio/settings-encryption/v1"
_DEV_KDF_INFO = b"settings-encryption-master-key"

# 掩码只保留尾 4 位，且仅当明文足够长时才保留（短密钥不给 hint，避免泄露比例过高）
HINT_MIN_PLAINTEXT_LENGTH = 24
HINT_SUFFIX_LENGTH = 4
MASK_PREFIX = "\u2022" * 8


class SecretCipherError(Exception):
    """加密层基础异常。"""


class SecretCipherConfigError(SecretCipherError):
    """主密钥缺失或非法。属于启动期错误，应 fail fast。"""


class SecretDecryptError(SecretCipherError):
    """密文无法解密：格式非法 / 被篡改 / AAD 不匹配 / 缺少对应主密钥。"""


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64decode(text: str) -> bytes:
    padding = "=" * (-len(text) % 4)
    try:
        return base64.urlsafe_b64decode(text + padding)
    except (binascii.Error, ValueError) as exc:
        raise SecretDecryptError("密文 base64 解码失败") from exc


def decode_master_key(raw: str) -> bytes:
    """把配置里的主密钥解析成 32 字节。

    接受两种写法：
    - base64（推荐，``python -c "import base64,os;print(base64.b64encode(os.urandom(32)).decode())"``）
    - 64 位 hex
    """
    value = (raw or "").strip()
    if not value:
        raise SecretCipherConfigError("主密钥为空")

    if _HEX_PATTERN.match(value):
        material = bytes.fromhex(value)
    else:
        padding = "=" * (-len(value) % 4)
        try:
            material = base64.urlsafe_b64decode(value + padding)
        except (binascii.Error, ValueError) as exc:
            raise SecretCipherConfigError("主密钥既不是 64 位 hex，也不是合法 base64") from exc

    if len(material) != _KEY_BYTES:
        raise SecretCipherConfigError(f"主密钥解码后应为 {_KEY_BYTES} 字节，实际 {len(material)} 字节")
    return material


def derive_key_from_secret(secret: str) -> bytes:
    """从任意口令经 HKDF-SHA256 确定性派生 32 字节主密钥。

    仅用于开发环境兜底：所有开发从同一份 ``.env.<env>`` 的 ``jwt_secret_key``
    派生出的主密钥完全一致，因此即使共用同一个 dev 数据库也能互相解密，
    不需要传递任何密钥文件。生产环境必须显式配置 ``settings_encryption_key``。
    """
    if not secret:
        raise SecretCipherConfigError("用于派生主密钥的口令为空")
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=_KEY_BYTES,
        salt=_DEV_KDF_SALT,
        info=_DEV_KDF_INFO,
    )
    return hkdf.derive(secret.encode("utf-8"))


def build_secret_hint(plaintext: str) -> str | None:
    """给出用于掩码展示的尾串。

    只在明文长度 >= ``HINT_MIN_PLAINTEXT_LENGTH`` 时返回尾 4 位，短密钥一律返回
    None（只显示固定掩码），避免"掩码本身泄露了大部分内容"。
    """
    text = plaintext or ""
    if len(text) < HINT_MIN_PLAINTEXT_LENGTH:
        return None
    return text[-HINT_SUFFIX_LENGTH:]


def mask_secret_hint(hint: str | None) -> str:
    """把 hint 渲染成前端直接可用的掩码串。"""
    suffix = (hint or "").strip()
    return f"{MASK_PREFIX}{suffix}" if suffix else MASK_PREFIX


class SecretCipher:
    """AES-256-GCM 加解密器。

    ``keys`` 允许同时持有多个主密钥（key_id → 32 字节），解密时按密文自带的
    key_id 选密钥；``active_key_id`` 决定加密用哪一把。这是主密钥轮换的基础：
    新增一把密钥并切换 active，旧密文仍可解。
    """

    def __init__(self, *, keys: dict[str, bytes], active_key_id: str) -> None:
        if not keys:
            raise SecretCipherConfigError("至少需要一把主密钥")
        if active_key_id not in keys:
            raise SecretCipherConfigError(f"active_key_id={active_key_id!r} 不在主密钥集合中")
        for key_id, material in keys.items():
            if not _KEY_ID_PATTERN.match(key_id):
                raise SecretCipherConfigError(f"key_id={key_id!r} 非法（只允许字母数字下划线短横，1~16 位）")
            if len(material) != _KEY_BYTES:
                raise SecretCipherConfigError(f"key_id={key_id!r} 的密钥长度应为 {_KEY_BYTES} 字节")
        self._keys = dict(keys)
        self._active_key_id = active_key_id

    @property
    def active_key_id(self) -> str:
        return self._active_key_id

    def encrypt(self, plaintext: str, *, aad: str) -> str:
        """加密并返回 ``v1:<key_id>:<nonce>:<ciphertext>``。

        ``aad`` 是附加认证数据：不参与加密，但参与完整性校验。解密时必须传入
        完全相同的值，因此可以用它把密文"钉"在某个逻辑位置上。
        """
        material = self._keys[self._active_key_id]
        nonce = os.urandom(_NONCE_BYTES)
        sealed = AESGCM(material).encrypt(nonce, plaintext.encode("utf-8"), aad.encode("utf-8"))
        return f"{_VERSION}:{self._active_key_id}:{_b64encode(nonce)}:{_b64encode(sealed)}"

    def decrypt(self, token: str, *, aad: str) -> str:
        """解密 ``encrypt()`` 产出的密文；任何问题都抛 :class:`SecretDecryptError`。"""
        parts = (token or "").split(":")
        if len(parts) != 4:
            raise SecretDecryptError("密文格式非法：应为 v1:<key_id>:<nonce>:<ciphertext>")

        version, key_id, nonce_text, ciphertext_text = parts
        if version != _VERSION:
            raise SecretDecryptError(f"不支持的密文版本：{version!r}")

        material = self._keys.get(key_id)
        if material is None:
            raise SecretDecryptError(f"缺少主密钥 {key_id!r}，无法解密")

        nonce = _b64decode(nonce_text)
        if len(nonce) != _NONCE_BYTES:
            raise SecretDecryptError(f"nonce 长度应为 {_NONCE_BYTES} 字节，实际 {len(nonce)} 字节")

        sealed = _b64decode(ciphertext_text)
        try:
            raw = AESGCM(material).decrypt(nonce, sealed, aad.encode("utf-8"))
        except Exception as exc:  # noqa: BLE001 - InvalidTag 等一律翻译成本层异常
            raise SecretDecryptError("解密失败：密文被篡改，或 AAD 与写入时不匹配") from exc
        return raw.decode("utf-8")


@lru_cache(maxsize=1)
def get_secret_cipher() -> SecretCipher:
    """按配置构建全局加密器。

    主密钥来源优先级：

    1. ``SETTINGS_ENCRYPTION_KEY``（显式配置，生产唯一合法来源）
    2. ``env != "prod"`` 且允许兜底时，从 ``jwt_secret_key`` 经 HKDF 派生

    生产环境未显式配置且不允许派生时抛 :class:`SecretCipherConfigError`，
    由启动流程 fail fast —— 不给"以为加密了其实没有"留任何口子。
    """
    from ..infrastructure.config import settings

    key_id = (settings.settings_encryption_key_id or "").strip() or "k1"
    raw_key = (settings.settings_encryption_key or "").strip()

    if raw_key:
        return SecretCipher(keys={key_id: decode_master_key(raw_key)}, active_key_id=key_id)

    if settings.env == "prod":
        raise SecretCipherConfigError("生产环境必须显式配置 SETTINGS_ENCRYPTION_KEY（base64 的 32 字节或 64 位 hex）。")

    if not settings.settings_encryption_allow_dev_kdf:
        raise SecretCipherConfigError("未配置 SETTINGS_ENCRYPTION_KEY 且已禁用开发环境派生兜底，无法启动。")

    logger.warning(
        "未配置 SETTINGS_ENCRYPTION_KEY，正从 JWT_SECRET_KEY 经 HKDF-SHA256 派生主密钥"
        "（仅开发环境兜底）。该派生强度等于 JWT_SECRET_KEY 的强度，"
        "不要在生产环境依赖它。"
    )
    return SecretCipher(keys={key_id: derive_key_from_secret(settings.jwt_secret_key)}, active_key_id=key_id)
