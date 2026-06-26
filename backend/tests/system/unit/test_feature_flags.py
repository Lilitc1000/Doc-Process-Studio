from doc_process_studio.system.infrastructure.utils.feature_flags import is_feature_enabled_for_key


def test_feature_flag_rollout_ratio_boundary() -> None:
    assert (
        is_feature_enabled_for_key(
            feature_name="planner",
            key="tenant-a:conv-1",
            enabled=True,
            rollout_ratio=0.0,
        )
        is False
    )
    assert (
        is_feature_enabled_for_key(
            feature_name="planner",
            key="tenant-a:conv-1",
            enabled=True,
            rollout_ratio=1.0,
        )
        is True
    )


def test_feature_flag_is_stable_for_same_key() -> None:
    first = is_feature_enabled_for_key(
        feature_name="executor",
        key="tenant-a:conv-9",
        enabled=True,
        rollout_ratio=0.25,
    )
    second = is_feature_enabled_for_key(
        feature_name="executor",
        key="tenant-a:conv-9",
        enabled=True,
        rollout_ratio=0.25,
    )
    assert first is second


def test_feature_flag_can_be_hard_disabled() -> None:
    assert (
        is_feature_enabled_for_key(
            feature_name="executor",
            key="tenant-b:conv-1",
            enabled=False,
            rollout_ratio=1.0,
        )
        is False
    )
