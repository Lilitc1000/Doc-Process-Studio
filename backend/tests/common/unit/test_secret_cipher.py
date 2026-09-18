"""AES-256-GCM 加密层单元测试。

重点覆盖"改错了会静默变不安全"的几处：

- 同一明文两次加密必须密文不同（nonce 随机），否则等于 ECB
- AAD 不匹配必须解密失败 —— 这是"密文被搬到别的行"的防线
- 密文/掩码里绝不出现明文
- 主密钥轮换后旧密文仍可解、但换错密钥一定解不开
"""

from __future__ import annotations

import base64
import os

import pytest

from doc_process_studio.common.security.secret_cipher import (
    HINT_MIN_PLAINTEXT_LENGTH,
    MASK_PREFIX,
    SecretCipher,
    SecretCipherConfigError,
    SecretDecryptError,
    build_secret_hint,
    decode_master_key,
    derive_key_from_secret,
    mask_secret_hint,
)

KEY_A = os.urandom(32)
KEY_B = os.urandom(32)
AAD = "ragflow.api_key"


def _cipher(key: bytes = KEY_A, key_id: str = "k1") -> SecretCipher:
    return SecretCipher(keys={key_id: key}, active_key_id=key_id)


# ------------------------------------------------------------------ 往返与格式


@pytest.mark.parametrize(
    "plaintext",
    ["", "short", "ragflow-testkey-0123456789abcdefghijklmnopqrstuvtkYQ", "含中文的密钥 abc-123", "x" * 4096],
)
def test_encrypt_decrypt_roundtrip(plaintext: str) -> None:
    cipher = _cipher()
    token = cipher.encrypt(plaintext, aad=AAD)
    assert cipher.decrypt(token, aad=AAD) == plaintext


def test_ciphertext_shape_and_no_plaintext_leak() -> None:
    plaintext = "ragflow-SECRET-VALUE-1234567890"
    token = _cipher().encrypt(plaintext, aad=AAD)

    parts = token.split(":")
    assert len(parts) == 4
    assert parts[0] == "v1"
    assert parts[1] == "k1"
    assert plaintext not in token
    # nonce 12 字节 -> base64url 16 字符（无 padding）
    assert len(base64.urlsafe_b64decode(parts[2] + "==")) == 12


def test_nonce_is_random_per_call() -> None:
    cipher = _cipher()
    first = cipher.encrypt("same-plaintext", aad=AAD)
    second = cipher.encrypt("same-plaintext", aad=AAD)
    assert first != second, "同一明文两次加密得到相同密文，nonce 没有随机化"
    assert cipher.decrypt(first, aad=AAD) == cipher.decrypt(second, aad=AAD) == "same-plaintext"


# ------------------------------------------------------------------ 完整性防线


def test_aad_mismatch_raises() -> None:
    """AAD 绑定的是"这条密文属于哪个逻辑位置"，换位置必须解不开。"""
    cipher = _cipher()
    token = cipher.encrypt("value", aad="ragflow.api_key")
    with pytest.raises(SecretDecryptError):
        cipher.decrypt(token, aad="some.other.key")


def test_tampered_ciphertext_raises() -> None:
    cipher = _cipher()
    version, key_id, nonce, ciphertext = cipher.encrypt("value", aad=AAD).split(":")
    flipped = ("A" if ciphertext[0] != "A" else "B") + ciphertext[1:]
    with pytest.raises(SecretDecryptError):
        cipher.decrypt(f"{version}:{key_id}:{nonce}:{flipped}", aad=AAD)


def test_tampered_nonce_raises() -> None:
    cipher = _cipher()
    version, key_id, nonce, ciphertext = cipher.encrypt("value", aad=AAD).split(":")
    flipped = ("A" if nonce[0] != "A" else "B") + nonce[1:]
    with pytest.raises(SecretDecryptError):
        cipher.decrypt(f"{version}:{key_id}:{flipped}:{ciphertext}", aad=AAD)


@pytest.mark.parametrize(
    "token",
    [
        "",
        "not-a-token",
        "v1:k1:onlythreeparts",
        "v2:k1:AAAAAAAAAAAAAAAA:AAAAAAAAAAAAAAAA",  # 未知版本
        "v1:missing:AAAAAAAAAAAAAAAA:AAAAAAAAAAAAAAAA",  # 未知 key_id
        "v1:k1:!!!!!!!!!!!!!!!!:AAAAAAAAAAAAAAAA",  # 非法 base64
        "v1:k1:AAAA:AAAAAAAAAAAAAAAA",  # nonce 长度不对
    ],
)
def test_malformed_tokens_raise(token: str) -> None:
    with pytest.raises(SecretDecryptError):
        _cipher().decrypt(token, aad=AAD)


def test_wrong_master_key_raises() -> None:
    token = _cipher(KEY_A).encrypt("value", aad=AAD)
    with pytest.raises(SecretDecryptError):
        _cipher(KEY_B).decrypt(token, aad=AAD)


# ------------------------------------------------------------------ 主密钥轮换


def test_rotation_keeps_old_ciphertext_readable() -> None:
    """轮换只换"加密用"的密钥，已存密文仍必须能解 —— 否则线上数据全废。"""
    legacy_token = SecretCipher(keys={"k1": KEY_A}, active_key_id="k1").encrypt("legacy", aad=AAD)

    rotated = SecretCipher(keys={"k1": KEY_A, "k2": KEY_B}, active_key_id="k2")
    assert rotated.decrypt(legacy_token, aad=AAD) == "legacy"
    assert rotated.encrypt("fresh", aad=AAD).startswith("v1:k2:")
    assert rotated.active_key_id == "k2"


def test_dropping_old_key_breaks_old_ciphertext() -> None:
    """反向确认：真把旧密钥扔掉，旧密文就解不开（说明轮换不是"看起来生效"）。"""
    legacy_token = SecretCipher(keys={"k1": KEY_A}, active_key_id="k1").encrypt("legacy", aad=AAD)
    with pytest.raises(SecretDecryptError):
        SecretCipher(keys={"k2": KEY_B}, active_key_id="k2").decrypt(legacy_token, aad=AAD)


# ------------------------------------------------------------------ 主密钥解析


def test_decode_master_key_accepts_base64_and_hex() -> None:
    assert decode_master_key(base64.b64encode(KEY_A).decode()) == KEY_A
    assert decode_master_key(KEY_A.hex()) == KEY_A
    assert decode_master_key(f"  {KEY_A.hex()}  ") == KEY_A


@pytest.mark.parametrize("raw", ["", "   ", "too-short", base64.b64encode(os.urandom(16)).decode(), "z" * 64])
def test_decode_master_key_rejects_bad_input(raw: str) -> None:
    with pytest.raises(SecretCipherConfigError):
        decode_master_key(raw)


def test_derive_key_is_deterministic_and_distinct() -> None:
    """dev 兜底派生必须确定性 —— 否则共用同一个 dev 库的同事互相解不开。"""
    assert derive_key_from_secret("same-secret") == derive_key_from_secret("same-secret")
    assert derive_key_from_secret("secret-a") != derive_key_from_secret("secret-b")
    assert len(derive_key_from_secret("x")) == 32
    with pytest.raises(SecretCipherConfigError):
        derive_key_from_secret("")


# ------------------------------------------------------------------ 构造校验


def test_cipher_rejects_invalid_configuration() -> None:
    with pytest.raises(SecretCipherConfigError):
        SecretCipher(keys={}, active_key_id="k1")
    with pytest.raises(SecretCipherConfigError):
        SecretCipher(keys={"k1": KEY_A}, active_key_id="k2")
    with pytest.raises(SecretCipherConfigError):
        SecretCipher(keys={"k1": os.urandom(16)}, active_key_id="k1")
    with pytest.raises(SecretCipherConfigError):
        SecretCipher(keys={"bad key id!": KEY_A}, active_key_id="bad key id!")


# ------------------------------------------------------------------ 掩码


def test_hint_only_for_long_enough_secrets() -> None:
    assert build_secret_hint("x" * (HINT_MIN_PLAINTEXT_LENGTH - 1)) is None
    assert build_secret_hint("x" * HINT_MIN_PLAINTEXT_LENGTH) == "xxxx"
    assert build_secret_hint("ragflow-testkey-0123456789abcdefghijklmnopqrstuvtkYQ") == "tkYQ"


def test_mask_hides_everything_but_hint() -> None:
    masked = mask_secret_hint("tkYQ")
    assert masked == f"{MASK_PREFIX}tkYQ"
    assert mask_secret_hint(None) == MASK_PREFIX
    assert mask_secret_hint("") == MASK_PREFIX
    assert mask_secret_hint("   ") == MASK_PREFIX


def test_short_secret_never_leaks_suffix() -> None:
    """短密钥不给 hint —— 否则"掩码"本身就把大部分内容交代了。"""
    short = "abc123"
    hint = build_secret_hint(short)
    assert hint is None
    assert mask_secret_hint(hint) == MASK_PREFIX
    assert short not in mask_secret_hint(hint)
