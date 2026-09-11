"""P0 回归：表单 Schema 声明的每个字段，其取值都必须能落到导出载荷。

背景
----
P0 把 Schema 扩到 6 步 33 字段。字段「声明了」和「值真的能走到导出文档里」
是两回事——`form_schema.py` 的 `field_id` 与 `report_data.py` 实际读取的
form key 分处两地，没有强制约束，容易各改各的。

为什么用「哨兵值」而不是比对 key 字符串
--------------------------------------
直接做「字段名是否是源码里的子串」这种检查会误判：Schema 的 `body_impact`
恰好是真实 key `body_impact_scope` 的前缀子串，会被错判成已映射。
本测试改为**功能验证**：给每个字段塞一个唯一哨兵值，跑一遍
`build_report_data_from_snapshot()`，断言哨兵出现在导出载荷里。

已知漂移
--------
Schema 的 `field_id` 与前后端真实使用的 form key 在以下字段上不一致
（前端 `useReportForm.ts` 与后端 `constants.py` 互相一致，错的只有 Schema 声明）：

- `body_impact`      → 真实 key 是 `body_impact_scope`
- `appendix_content` → 真实 key 是 `appendix_notes`

它们登记在 `_KNOWN_KEY_DRIFT`：测试断言其**真实 key 仍然有效**，
这样既固化现状不会误报红灯，又能在真实链路被改坏时立刻报警。
若日后修正 Schema，请同步从该表移除对应条目。
"""

from __future__ import annotations

from typing import Any

import pytest

from doc_process_studio.incident_report.domain.values.form_schema import (
    INCIDENT_REPORT_FORM_SCHEMA,
)
from doc_process_studio.incident_report.infrastructure.utils.generation import (
    _build_snapshot_from_form_data,
)
from doc_process_studio.incident_report.infrastructure.utils.report_data import (
    build_report_data_from_snapshot,
)

# select 类字段经选项白名单归一化，非法值会被丢弃，哨兵法不适用。
_OPTION_NORMALIZED_FIELDS = frozenset({"manual_status", "manual_severity"})
# attachment 由附件体系承载，不进 report_data。
_NOT_IN_REPORT_DATA_FIELDS = frozenset({"appendix_attachments"})
# Schema field_id → 前后端真实使用的 form key（已知漂移，见模块文档字符串）。
_KNOWN_KEY_DRIFT: dict[str, tuple[str, ...]] = {
    "body_impact": ("body_impact_scope",),
    "appendix_content": ("appendix_notes",),
}


def _schema_fields() -> list[tuple[str, str, str]]:
    data = INCIDENT_REPORT_FORM_SCHEMA.model_dump()
    return [
        (step["step_id"], field["field_id"], field["field_type"]) for step in data["steps"] for field in step["fields"]
    ]


def _contains(blob: Any, needle: str) -> bool:
    if isinstance(blob, str):
        return needle in blob
    if isinstance(blob, dict):
        return any(_contains(value, needle) for value in blob.values())
    if isinstance(blob, list):
        return any(_contains(value, needle) for value in blob)
    return False


def _reaches_payload(field_id: str, field_type: str, *, key: str | None = None) -> bool:
    """把哨兵值塞进 key（默认用 field_id），看它能否走到导出载荷。"""
    sentinel = f"ZZ{field_id.upper()}ZZ"
    if field_type == "timeline":
        value: Any = [{"time": "10:00", "event": sentinel}]
    else:
        value = sentinel

    snapshot = _build_snapshot_from_form_data({key or field_id: value})
    payload, _missing = build_report_data_from_snapshot(
        snapshot,
        strict_required=False,
    )
    return payload is not None and _contains(payload, sentinel)


_DIRECT_FIELDS = [
    (step, field_id, field_type)
    for step, field_id, field_type in _schema_fields()
    if field_id not in _OPTION_NORMALIZED_FIELDS
    and field_id not in _NOT_IN_REPORT_DATA_FIELDS
    and field_id not in _KNOWN_KEY_DRIFT
]


@pytest.mark.parametrize(
    ("step_id", "field_id", "field_type"),
    _DIRECT_FIELDS,
    ids=[f"{step}__{field}" for step, field, _ in _DIRECT_FIELDS],
)
def test_schema_field_reaches_export_payload(
    step_id: str,
    field_id: str,
    field_type: str,
) -> None:
    del step_id
    assert _reaches_payload(field_id, field_type), (
        f"字段 {field_id}（{field_type}）的取值没有进入导出载荷，"
        f"请核对 form_schema.field_id 与 report_data 实际读取的 form key 是否一致"
    )


@pytest.mark.parametrize(
    ("schema_field_id", "real_keys"),
    sorted(_KNOWN_KEY_DRIFT.items()),
    ids=sorted(_KNOWN_KEY_DRIFT),
)
def test_known_drift_real_keys_still_reach_payload(
    schema_field_id: str,
    real_keys: tuple[str, ...],
) -> None:
    """已知漂移：Schema 声明有误，此处断言「真实 key 仍可用」以免链路静默失效。"""
    type_by_id = {field_id: field_type for _, field_id, field_type in _schema_fields()}
    field_type = type_by_id[schema_field_id]
    unreachable = [key for key in real_keys if not _reaches_payload(schema_field_id, field_type, key=key)]
    assert unreachable == [], (
        f"已知漂移字段的真实 key 无法到达导出载荷：{unreachable}。这意味着修复前的补偿路径也已经不通，属于数据丢失"
    )


def test_option_normalized_fields_reach_payload_with_valid_option() -> None:
    """select 类字段只有合法选项值能通过归一化，用合法值单独验证。"""
    snapshot = _build_snapshot_from_form_data(
        {"manual_status": "fault_cleared", "manual_severity": "major"},
    )
    payload, _missing = build_report_data_from_snapshot(
        snapshot,
        strict_required=False,
    )

    assert payload is not None
    assert payload["status_option"] == "fault_cleared"
    assert payload["status"], "状态选项应被映射为可读文本"
    assert payload["severity_option"] == "major"
    assert payload["severity"], "严重级别选项应被映射为可读文本"


def test_exclusion_tables_still_reference_existing_schema_fields() -> None:
    """防止排除表里留下拼错或已删除的字段名，导致真漂移被漏掉。"""
    known = {field_id for _, field_id, _ in _schema_fields()}
    stale = (_OPTION_NORMALIZED_FIELDS | _NOT_IN_REPORT_DATA_FIELDS | set(_KNOWN_KEY_DRIFT)) - known
    assert stale == set(), f"排除表中存在 Schema 里已没有的字段：{sorted(stale)}"
