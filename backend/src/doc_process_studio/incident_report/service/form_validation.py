from typing import Any

from ..schemas.common import VALID_SEVERITIES, VALID_STATUSES


REQUIRED_FIELDS_FOR_SUBMIT = [
    "manual_reference_no",
    "manual_fault_date",
    "manual_reporting_person",
    "manual_site_id",
    "manual_system",
    "manual_fault_symptom",
    "manual_severity",
]


def validate_form_data_for_submit(form_data: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    for field_id in REQUIRED_FIELDS_FOR_SUBMIT:
        value = form_data.get(field_id)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing.append(field_id)
    return missing


def validate_severity(severity: str | None) -> str | None:
    if severity is None:
        return None
    if severity not in VALID_SEVERITIES:
        raise ValueError(f"无效的严重级别: {severity}，有效值: {', '.join(VALID_SEVERITIES)}")
    return severity


def validate_status(status: str | None) -> str | None:
    if status is None:
        return None
    if status not in VALID_STATUSES:
        raise ValueError(f"无效的状态: {status}，有效值: {', '.join(VALID_STATUSES)}")
    return status


def validate_report_data(report_data: dict[str, Any] | None) -> list[str]:
    errors: list[str] = []
    if report_data is None:
        return errors
    severity = report_data.get("severity")
    if severity and severity not in VALID_SEVERITIES:
        errors.append(f"无效的严重级别: {severity}")
    status = report_data.get("status")
    if status and status not in VALID_STATUSES:
        errors.append(f"无效的状态: {status}")
    return errors
