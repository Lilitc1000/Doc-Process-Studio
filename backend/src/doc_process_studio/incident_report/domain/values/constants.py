from pathlib import Path

INCIDENT_REPORT_SCRIPT_PATH = (
    Path(__file__).resolve().parents[3] / "skills" / "incident-report" / "scripts" / "generate_incident_report.py"
)
INCIDENT_REPORT_SKILL_DIR = Path(__file__).resolve().parents[3] / "skills" / "incident-report"
INCIDENT_REPORT_SKILL_MD_PATH = INCIDENT_REPORT_SKILL_DIR / "SKILL.md"
INCIDENT_REPORT_REFERENCE_DIR = INCIDENT_REPORT_SKILL_DIR / "references"
INCIDENT_REPORT_BODY_REFERENCE_DIR = INCIDENT_REPORT_REFERENCE_DIR / "body-sections"
INCIDENT_REPORT_REFERENCE_SELECT_LIMIT = 6

# ---------------------------------------------------------------------------
# section → 必加载规范文件（写作契约的确定性保障）
#
# 背景：参考文档原先完全交由 LLM 规划器挑选，规划器一旦返回多于显式项的结果，
# 就会整体覆盖启发式的确定性匹配（见 infrastructure/adapters/reference_context.py）。
# 实测后果：quick 模式（要一次生成全部字段）只加载 common.md(10 行) 与
# quick-mode.md(16 行)，而最详细的 impact.md / root-cause.md / follow-up.md
# 进不了 prompt —— 同一份报告两次生成质量不同，根因就在这里。
#
# 因此这里把「每个 section 必须读到哪些规范」固化下来：
# - 必加载项优先占位，规划器只能在剩余预算内补充，不再覆盖；
# - quick 生成全部字段，所以必须带上 impact / root-cause / follow-up 三份详细契约。
# ---------------------------------------------------------------------------
INCIDENT_REPORT_COMMON_REFERENCE = "body-sections/common.md"

INCIDENT_REPORT_SECTION_REFERENCE_MAP: dict[str, tuple[str, ...]] = {
    # quick 一次生成全部字段，因此覆盖三个最详细的章节契约
    "quick": (
        INCIDENT_REPORT_COMMON_REFERENCE,
        "body-sections/quick-mode.md",
        "body-sections/impact.md",
        "body-sections/root-cause.md",
        "body-sections/follow-up.md",
    ),
    "description": (INCIDENT_REPORT_COMMON_REFERENCE, "body-sections/description.md"),
    "timeline": (INCIDENT_REPORT_COMMON_REFERENCE, "body-sections/timeline.md"),
    "timeline_item": (INCIDENT_REPORT_COMMON_REFERENCE, "body-sections/timeline-item.md"),
    "impact": (INCIDENT_REPORT_COMMON_REFERENCE, "body-sections/impact.md"),
    "root_cause": (INCIDENT_REPORT_COMMON_REFERENCE, "body-sections/root-cause.md"),
    "follow_up": (INCIDENT_REPORT_COMMON_REFERENCE, "body-sections/follow-up.md"),
}

# ---------------------------------------------------------------------------
# 表单 system 字段 → 检索域关键词
#
# 背景：检索 query 原先只从 context_json 里正则抽取 ASCII token，中文口语输入
# 几乎抽不出任何东西，query 退化为纯主题词，导致检索与本次事故无关。
# 表单的 manual_system 是结构化的、可靠的检索键，优先用它定位事故所属域，
# 这样「数据库事故」只检索数据库域语料，不会召回存储域的因果链。
# 映射值：(检索域词, 命中关键字集合)；关键字同时收录中英文写法。
# ---------------------------------------------------------------------------
INCIDENT_SYSTEM_DOMAIN_MAP: dict[str, tuple[str, tuple[str, ...]]] = {
    "database": (
        "database",
        ("database", "db", "mysql", "oracle", "postgres", "postgresql", "sql", "資料庫", "数据库"),
    ),
    "storage": (
        "storage",
        ("storage", "nas", "synology", "san", "nfs", "smb", "disk", "array", "存儲", "存储"),
    ),
    "network": (
        "network",
        ("network", "switch", "router", "firewall", "vpn", "link", "dns", "網路", "网络"),
    ),
    "toll": (
        "toll",
        ("toll", "lane", "gantry", "etag", "tag", "收費", "收费", "閘機", "闸机"),
    ),
}

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
BODY_FOLLOW_UP = "body_follow_up"

APPENDIX_NOTES = "appendix_notes"
APPENDIX_IMAGES = "appendix_images"

SYSTEM_DOCUMENT_SKILL_ID = "document-assistant"

STATUS_OPTION_FAULT_CLEARED = "fault_cleared"
STATUS_OPTION_TEMPORARILY_FIXED = "temporarily_fixed"
STATUS_OPTION_FOLLOW_UP_ACTION_REQUIRED = "follow_up_action_required"

SEVERITY_OPTION_NOT_APPLICABLE = "not_applicable"
SEVERITY_OPTION_MINOR = "minor"
SEVERITY_OPTION_MAJOR = "major"

SEVERITY_P0 = "P0"
SEVERITY_P1 = "P1"
SEVERITY_P2 = "P2"
SEVERITY_P3 = "P3"
