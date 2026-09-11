from doc_process_studio.incident_report.domain.values.form_schema import (
    INCIDENT_REPORT_FORM_SCHEMA,
    FormFieldSchema,
    FormSchemaDefinition,
    FormStepSchema,
)


def _step_by_id(step_id: str) -> FormStepSchema:
    """按 step_id 取步骤，避免步骤顺序调整导致测试连锁失败。"""
    step = next((s for s in INCIDENT_REPORT_FORM_SCHEMA.steps if s.step_id == step_id), None)
    assert step is not None, f"missing step: {step_id}"
    return step


def test_form_schema_definition_structure() -> None:
    assert INCIDENT_REPORT_FORM_SCHEMA.version == 1
    assert len(INCIDENT_REPORT_FORM_SCHEMA.steps) == 6


def test_form_schema_steps_have_ids() -> None:
    step_ids = [step.step_id for step in INCIDENT_REPORT_FORM_SCHEMA.steps]
    assert step_ids == ["basic_info", "clearance", "closeout", "description", "timeline", "appendix"]


def test_form_schema_step_ids_are_unique() -> None:
    step_ids = [step.step_id for step in INCIDENT_REPORT_FORM_SCHEMA.steps]
    assert len(step_ids) == len(set(step_ids))


def test_form_schema_field_ids_are_unique() -> None:
    field_ids = [f.field_id for step in INCIDENT_REPORT_FORM_SCHEMA.steps for f in step.fields]
    assert len(field_ids) == len(set(field_ids))


def test_form_schema_basic_info_step() -> None:
    step = _step_by_id("basic_info")
    assert step.title == "基本信息"
    assert step.description is not None
    required_fields = [f for f in step.fields if f.required]
    assert len(required_fields) >= 5


def test_basic_info_covers_section_a_manual_fields() -> None:
    step = _step_by_id("basic_info")
    field_ids = [f.field_id for f in step.fields]
    for expected in (
        "manual_reference_no",
        "manual_fault_date",
        "manual_fault_time",
        "manual_reporting_person",
        "manual_verified_by",
        "manual_site_id",
        "manual_system",
        "manual_location",
        "manual_fault_symptom",
    ):
        assert expected in field_ids, f"missing field: {expected}"


def test_form_schema_clearance_step() -> None:
    """Section B（Contractor 填写）的九个字段必须全部暴露。"""
    step = _step_by_id("clearance")
    assert step.title == "故障清除"
    field_ids = [f.field_id for f in step.fields]
    for expected in (
        "manual_arrival_datetime",
        "manual_clearance_datetime",
        "manual_service_person",
        "manual_fault_cause",
        "manual_materials_used",
        "manual_repair_details",
        "manual_contractor_staff",
        "manual_contractor_signature",
        "manual_contractor_date",
    ):
        assert expected in field_ids, f"missing field: {expected}"
    assert len(field_ids) == 9


def test_clearance_datetime_fields_use_datetime_type() -> None:
    step = _step_by_id("clearance")
    types = {f.field_id: f.field_type for f in step.fields}
    assert types["manual_arrival_datetime"] == "datetime"
    assert types["manual_clearance_datetime"] == "datetime"
    assert types["manual_repair_details"] == "textarea"


def test_form_schema_closeout_step() -> None:
    """Section C（Employer 填写）的五个字段必须全部暴露。"""
    step = _step_by_id("closeout")
    assert step.title == "报告关闭"
    field_ids = [f.field_id for f in step.fields]
    for expected in (
        "manual_status_ref_no",
        "manual_comments",
        "manual_employer_rep",
        "manual_employer_signature",
        "manual_closeout_date",
    ):
        assert expected in field_ids, f"missing field: {expected}"
    assert len(field_ids) == 5


def test_form_schema_description_step() -> None:
    step = _step_by_id("description")
    field_ids = [f.field_id for f in step.fields]
    assert "quick_narrative" in field_ids
    assert "body_description" in field_ids


def test_form_schema_timeline_step() -> None:
    step = _step_by_id("timeline")
    field_ids = [f.field_id for f in step.fields]
    assert "body_timeline" in field_ids


def test_form_schema_appendix_step() -> None:
    step = _step_by_id("appendix")
    field_ids = [f.field_id for f in step.fields]
    assert "appendix_content" in field_ids
    assert "appendix_attachments" in field_ids


def test_form_field_schema_creation() -> None:
    field = FormFieldSchema(
        field_id="test_field",
        label="测试字段",
        field_type="text",
        required=True,
        placeholder="输入",
    )
    assert field.field_id == "test_field"
    assert field.required is True
    assert field.options is None


def test_form_step_schema_creation() -> None:
    step = FormStepSchema(
        step_id="test_step",
        title="测试步骤",
        fields=[],
    )
    assert step.step_id == "test_step"
    assert step.fields == []


def test_form_schema_definition_creation() -> None:
    schema = FormSchemaDefinition(version=2, steps=[])
    assert schema.version == 2
    assert schema.steps == []


def test_basic_info_has_severity_options() -> None:
    step = _step_by_id("basic_info")
    severity_field = next(f for f in step.fields if f.field_id == "manual_severity")
    assert severity_field.options is not None
    assert len(severity_field.options) == 4
    values = [opt["value"] for opt in severity_field.options]
    assert "P0" in values
    assert "P3" in values


def test_basic_info_has_status_options() -> None:
    step = _step_by_id("basic_info")
    status_field = next(f for f in step.fields if f.field_id == "manual_status")
    assert status_field.options is not None
    assert len(status_field.options) == 3
