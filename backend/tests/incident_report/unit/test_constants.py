from doc_process_studio.incident_report.service.constants import (
    BODY_AFFECTED_DATE,
    BODY_BUSINESS_IMPACT,
    BODY_DESCRIPTION,
    BODY_FOLLOW_UP,
    BODY_IMPACT_SCOPE,
    BODY_IMPACT_SEVERITY,
    BODY_ROOT_CAUSE,
    BODY_TIMELINE,
    BODY_TRIGGER,
    INCIDENT_REPORT_DOCX_MIME_TYPE,
    INCIDENT_REPORT_SKILL_ID,
    MANUAL_FAULT_DATE,
    MANUAL_FAULT_TIME,
    MANUAL_REPORTING_PERSON,
    MANUAL_SEVERITY,
    MANUAL_SITE_ID,
    MANUAL_SYSTEM,
    QUICK_FOLLOW_UP_ACTION,
    QUICK_IMPACT_SCOPE,
    QUICK_IMPACT_SEVERITY,
    QUICK_NARRATIVE,
    QUICK_ROOT_CAUSE_GUESS,
    QUICK_TIMELINE,
    SEVERITY_OPTION_MAJOR,
    SEVERITY_OPTION_MINOR,
    SEVERITY_OPTION_NOT_APPLICABLE,
    STATUS_OPTION_FAULT_CLEARED,
    STATUS_OPTION_FOLLOW_UP_ACTION_REQUIRED,
    STATUS_OPTION_TEMPORARILY_FIXED,
    _CJK_CHAR_PATTERN,
    _TRANSLATION_SKIP_KEYS,
)


def test_incident_report_skill_id():
    assert INCIDENT_REPORT_SKILL_ID == "incident-report"


def test_docx_mime_type():
    assert INCIDENT_REPORT_DOCX_MIME_TYPE == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def test_manual_field_constants():
    assert MANUAL_FAULT_DATE == "manual_fault_date"
    assert MANUAL_FAULT_TIME == "manual_fault_time"
    assert MANUAL_REPORTING_PERSON == "manual_reporting_person"
    assert MANUAL_SITE_ID == "manual_site_id"
    assert MANUAL_SYSTEM == "manual_system"
    assert MANUAL_SEVERITY == "manual_severity"


def test_body_field_constants():
    assert BODY_DESCRIPTION == "body_description"
    assert BODY_AFFECTED_DATE == "body_affected_date_summary"
    assert BODY_TIMELINE == "body_timeline"
    assert BODY_IMPACT_SCOPE == "body_impact_scope"
    assert BODY_IMPACT_SEVERITY == "body_impact_severity"
    assert BODY_BUSINESS_IMPACT == "body_business_impact"
    assert BODY_TRIGGER == "body_trigger"
    assert BODY_ROOT_CAUSE == "body_root_cause"
    assert BODY_FOLLOW_UP == "body_follow_up_actions"


def test_quick_field_constants():
    assert QUICK_NARRATIVE == "quick_narrative"
    assert QUICK_TIMELINE == "quick_timeline"
    assert QUICK_IMPACT_SCOPE == "quick_impact_scope"
    assert QUICK_IMPACT_SEVERITY == "quick_impact_severity"
    assert QUICK_ROOT_CAUSE_GUESS == "quick_root_cause_guess"
    assert QUICK_FOLLOW_UP_ACTION == "quick_follow_up_action"


def test_status_options():
    assert STATUS_OPTION_FAULT_CLEARED == "fault_cleared"
    assert STATUS_OPTION_TEMPORARILY_FIXED == "temporarily_fixed"
    assert STATUS_OPTION_FOLLOW_UP_ACTION_REQUIRED == "follow_up_action_required"


def test_severity_options():
    assert SEVERITY_OPTION_NOT_APPLICABLE == "not_applicable"
    assert SEVERITY_OPTION_MINOR == "minor"
    assert SEVERITY_OPTION_MAJOR == "major"


def test_cjk_pattern_matches_chinese():
    assert _CJK_CHAR_PATTERN.search("中文") is not None


def test_cjk_pattern_no_match_english():
    assert _CJK_CHAR_PATTERN.search("English") is None


def test_translation_skip_keys():
    assert "reference_no" in _TRANSLATION_SKIP_KEYS
    assert "fault_date" in _TRANSLATION_SKIP_KEYS
    assert "data_url" in _TRANSLATION_SKIP_KEYS
