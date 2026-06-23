import hashlib


def is_feature_enabled_for_key(
    *,
    feature_name: str,
    key: str,
    enabled: bool,
    rollout_ratio: float,
) -> bool:
    """按稳定哈希桶做灰度判断。"""
    if not enabled:
        return False

    normalized_ratio = max(0.0, min(1.0, float(rollout_ratio)))
    if normalized_ratio >= 1.0:
        return True
    if normalized_ratio <= 0.0:
        return False

    normalized_key = key.strip() or "default"
    digest = hashlib.sha256(f"{feature_name}:{normalized_key}".encode()).hexdigest()
    # 取前 8 位十六进制，映射到 [0, 1)
    bucket = int(digest[:8], 16) / 0xFFFFFFFF
    return bucket < normalized_ratio
