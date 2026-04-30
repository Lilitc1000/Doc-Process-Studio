from doc_process_studio.incident_report.service.form_validation import (
    validate_form_data_for_submit,
    validate_severity,
    validate_status,
    validate_report_data,
)


def test_validate_form_data_missing_required_fields():
    form_data = {
        "manual_reference_no": "DAS-001",
    }
    missing = validate_form_data_for_submit(form_data)
    assert "manual_fault_date" in missing
    assert "manual_reporting_person" in missing
    assert "manual_site_id" in missing
    assert "manual_system" in missing
    assert "manual_fault_symptom" in missing


def test_validate_form_data_all_fields_present():
    form_data = {
        "manual_reference_no": "DAS-001",
        "manual_fault_date": "2026-04-20",
        "manual_reporting_person": "张三",
        "manual_site_id": "SITE-01",
        "manual_system": "数据库",
        "manual_fault_symptom": "服务中断",
    }
    missing = validate_form_data_for_submit(form_data)
    assert len(missing) == 0


def test_validate_form_data_empty_string_treated_as_missing():
    form_data = {
        "manual_reference_no": "DAS-001",
        "manual_fault_date": "",
        "manual_reporting_person": "   ",
    }
    missing = validate_form_data_for_submit(form_data)
    assert "manual_fault_date" in missing
    assert "manual_reporting_person" in missing


def test_validate_severity_valid():
    assert validate_severity("P0") == "P0"
    assert validate_severity("P1") == "P1"
    assert validate_severity("P2") == "P2"
    assert validate_severity("P3") == "P3"
    assert validate_severity(None) is None


def test_validate_severity_invalid():
    try:
        validate_severity("P4")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "无效的严重级别" in str(e)


def test_validate_status_valid():
    assert validate_status("draft") == "draft"
    assert validate_status("pending") == "pending"
    assert validate_status("closed") == "closed"
    assert validate_status(None) is None


def test_validate_status_invalid():
    try:
        validate_status("unknown")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "无效的状态" in str(e)


def test_validate_report_data_with_errors():
    report_data = {
        "severity": "P4",
        "status": "unknown",
    }
    errors = validate_report_data(report_data)
    assert len(errors) == 2


def test_validate_report_data_none():
    errors = validate_report_data(None)
    assert len(errors) == 0
