from doc_process_studio.incident_report.service.form_schema import (
    INCIDENT_REPORT_FORM_SCHEMA,
    FormFieldSchema,
    FormSchemaDefinition,
    FormStepSchema,
)


def test_form_schema_definition_structure():
    assert INCIDENT_REPORT_FORM_SCHEMA.version == 1
    assert len(INCIDENT_REPORT_FORM_SCHEMA.steps) == 4


def test_form_schema_steps_have_ids():
    step_ids = [step.step_id for step in INCIDENT_REPORT_FORM_SCHEMA.steps]
    assert step_ids == ["basic_info", "description", "timeline", "appendix"]


def test_form_schema_basic_info_step():
    step = INCIDENT_REPORT_FORM_SCHEMA.steps[0]
    assert step.title == "基本信息"
    assert step.description is not None
    required_fields = [f for f in step.fields if f.required]
    assert len(required_fields) >= 5


def test_form_schema_description_step():
    step = INCIDENT_REPORT_FORM_SCHEMA.steps[1]
    assert step.step_id == "description"
    field_ids = [f.field_id for f in step.fields]
    assert "quick_narrative" in field_ids
    assert "body_description" in field_ids


def test_form_schema_timeline_step():
    step = INCIDENT_REPORT_FORM_SCHEMA.steps[2]
    assert step.step_id == "timeline"
    field_ids = [f.field_id for f in step.fields]
    assert "body_timeline" in field_ids


def test_form_schema_appendix_step():
    step = INCIDENT_REPORT_FORM_SCHEMA.steps[3]
    assert step.step_id == "appendix"
    field_ids = [f.field_id for f in step.fields]
    assert "appendix_content" in field_ids
    assert "appendix_attachments" in field_ids


def test_form_field_schema_creation():
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


def test_form_step_schema_creation():
    step = FormStepSchema(
        step_id="test_step",
        title="测试步骤",
        fields=[],
    )
    assert step.step_id == "test_step"
    assert step.fields == []


def test_form_schema_definition_creation():
    schema = FormSchemaDefinition(version=2, steps=[])
    assert schema.version == 2
    assert schema.steps == []


def test_basic_info_has_severity_options():
    step = INCIDENT_REPORT_FORM_SCHEMA.steps[0]
    severity_field = next(f for f in step.fields if f.field_id == "manual_severity")
    assert severity_field.options is not None
    assert len(severity_field.options) == 4
    values = [opt["value"] for opt in severity_field.options]
    assert "P0" in values
    assert "P3" in values


def test_basic_info_has_status_options():
    step = INCIDENT_REPORT_FORM_SCHEMA.steps[0]
    status_field = next(f for f in step.fields if f.field_id == "manual_status")
    assert status_field.options is not None
    assert len(status_field.options) == 3
