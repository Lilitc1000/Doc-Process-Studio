"""事故报告表单校验规则。

提供提交完整性校验逻辑。
仅包含领域校验，HTTP 层的 severity/status 校验在 application 层处理。
"""

from typing import Any

# 提交审核时必填的字段列表
REQUIRED_FIELDS_FOR_SUBMIT: list[str] = [
    "manual_fault_date",
    "manual_reporting_person",
    "manual_site_id",
    "manual_system",
    "manual_fault_symptom",
]


def find_missing_submit_fields(form_data: dict[str, Any]) -> list[str]:
    """返回提交时缺失的必填字段，空列表表示可提交。"""
    missing: list[str] = []
    for field_id in REQUIRED_FIELDS_FOR_SUBMIT:
        value = form_data.get(field_id)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing.append(field_id)
    return missing
