import re
from pathlib import Path
from typing import Any

INCIDENT_REPORT_SKILL_ID = "incident-report"
INCIDENT_REPORT_DOCX_MIME_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)
INCIDENT_REPORT_SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "skills"
    / "incident-report"
    / "scripts"
    / "generate_incident_report.py"
)
INCIDENT_REPORT_SKILL_DIR = (
    Path(__file__).resolve().parents[2]
    / "skills"
    / "incident-report"
)
INCIDENT_REPORT_SKILL_MD_PATH = INCIDENT_REPORT_SKILL_DIR / "SKILL.md"
INCIDENT_REPORT_REFERENCE_DIR = INCIDENT_REPORT_SKILL_DIR / "references"
INCIDENT_REPORT_BODY_REFERENCE_DIR = INCIDENT_REPORT_REFERENCE_DIR / "body-sections"
INCIDENT_REPORT_REFERENCE_SELECT_LIMIT = 4

MANUAL_REFERENCE_NO = "manual_reference_no"
MANUAL_FAULT_DATE = "manual_fault_date"
MANUAL_FAULT_TIME = "manual_fault_time"
MANUAL_REPORTING_PERSON = "manual_reporting_person"
MANUAL_VERIFIED_BY = "manual_verified_by"
MANUAL_SITE_ID = "manual_site_id"
MANUAL_SYSTEM = "manual_system"
MANUAL_LOCATION = "manual_location"
MANUAL_FAULT_SYMPTOM = "manual_fault_symptom"
MANUAL_ARRIVAL_DATETIME = "manual_arrival_datetime"
MANUAL_CLEARANCE_DATETIME = "manual_clearance_datetime"
MANUAL_SERVICE_PERSON = "manual_service_person"
MANUAL_FAULT_CAUSE = "manual_fault_cause"
MANUAL_MATERIALS_USED = "manual_materials_used"
MANUAL_REPAIR_DETAILS = "manual_repair_details"
MANUAL_CONTRACTOR_STAFF = "manual_contractor_staff"
MANUAL_CONTRACTOR_SIGNATURE = "manual_contractor_signature"
MANUAL_CONTRACTOR_DATE = "manual_contractor_date"
MANUAL_STATUS = "manual_status"
MANUAL_STATUS_REF_NO = "manual_status_ref_no"
MANUAL_SEVERITY = "manual_severity"
MANUAL_COMMENTS = "manual_comments"
MANUAL_EMPLOYER_REP = "manual_employer_rep"
MANUAL_EMPLOYER_SIGNATURE = "manual_employer_signature"
MANUAL_CLOSEOUT_DATE = "manual_closeout_date"

QUICK_NARRATIVE = "quick_narrative"
QUICK_TIMELINE = "quick_timeline"
QUICK_IMPACT_SCOPE = "quick_impact_scope"
QUICK_IMPACT_SEVERITY = "quick_impact_severity"
QUICK_ROOT_CAUSE_GUESS = "quick_root_cause_guess"
QUICK_FOLLOW_UP_ACTION = "quick_follow_up_action"

BODY_DESCRIPTION = "body_description"
BODY_AFFECTED_DATE = "body_affected_date_summary"
BODY_TIMELINE = "body_timeline"
BODY_IMPACT_SCOPE = "body_impact_scope"
BODY_IMPACT_SEVERITY = "body_impact_severity"
BODY_BUSINESS_IMPACT = "body_business_impact"
BODY_TRIGGER = "body_trigger"
BODY_ROOT_CAUSE = "body_root_cause"
BODY_FOLLOW_UP = "body_follow_up_actions"

APPENDIX_NOTES = "appendix_notes"
APPENDIX_IMAGES = "appendix_images"

INCIDENT_REPORT_SCHEMA_INTRO = (
    "欢迎使用事故报告专区。支持快填生成正文、完整分段润色、附录富文本编辑与多版本附件历史。"
)
SYSTEM_DOCUMENT_SKILL_ID = "document-assistant"

STATUS_OPTION_FAULT_CLEARED = "fault_cleared"
STATUS_OPTION_TEMPORARILY_FIXED = "temporarily_fixed"
STATUS_OPTION_FOLLOW_UP_ACTION_REQUIRED = "follow_up_action_required"

SEVERITY_OPTION_NOT_APPLICABLE = "not_applicable"
SEVERITY_OPTION_MINOR = "minor"
SEVERITY_OPTION_MAJOR = "major"

_CJK_CHAR_PATTERN = re.compile(r"[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF\u3000-\u303F]")

_TRANSLATION_SKIP_KEYS = {
    "reference_no",
    "fault_date",
    "fault_time",
    "arrival_datetime",
    "clearance_datetime",
    "contractor_date",
    "closeout_date",
    "start_time",
    "detection_time",
    "resolution_time",
    "total_duration",
    "time",
    "date",
    "data_url",
    "download_url",
    "attachment_id",
    "mime_type",
    "size_label",
    "version",
    "generated_at",
}
