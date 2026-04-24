export const MANUAL_REFERENCE_NO = 'manual_reference_no';
export const MANUAL_FAULT_DATE = 'manual_fault_date';
export const MANUAL_FAULT_TIME = 'manual_fault_time';
export const MANUAL_REPORTING_PERSON = 'manual_reporting_person';
export const MANUAL_VERIFIED_BY = 'manual_verified_by';
export const MANUAL_SITE_ID = 'manual_site_id';
export const MANUAL_SYSTEM = 'manual_system';
export const MANUAL_LOCATION = 'manual_location';
export const MANUAL_FAULT_SYMPTOM = 'manual_fault_symptom';
export const MANUAL_ARRIVAL_DATETIME = 'manual_arrival_datetime';
export const MANUAL_CLEARANCE_DATETIME = 'manual_clearance_datetime';
export const MANUAL_SERVICE_PERSON = 'manual_service_person';
export const MANUAL_FAULT_CAUSE = 'manual_fault_cause';
export const MANUAL_MATERIALS_USED = 'manual_materials_used';
export const MANUAL_REPAIR_DETAILS = 'manual_repair_details';
export const MANUAL_CONTRACTOR_STAFF = 'manual_contractor_staff';
export const MANUAL_CONTRACTOR_SIGNATURE = 'manual_contractor_signature';
export const MANUAL_CONTRACTOR_DATE = 'manual_contractor_date';
export const MANUAL_STATUS = 'manual_status';
export const MANUAL_STATUS_REF_NO = 'manual_status_ref_no';
export const MANUAL_SEVERITY = 'manual_severity';
export const MANUAL_COMMENTS = 'manual_comments';
export const MANUAL_EMPLOYER_REP = 'manual_employer_rep';
export const MANUAL_EMPLOYER_SIGNATURE = 'manual_employer_signature';
export const MANUAL_CLOSEOUT_DATE = 'manual_closeout_date';
export const QUICK_NARRATIVE = 'quick_narrative';
export const BODY_DESCRIPTION = 'body_description';
export const BODY_AFFECTED_DATE = 'body_affected_date';
export const BODY_TIMELINE = 'body_timeline';
export const BODY_IMPACT_SCOPE = 'body_impact_scope';
export const BODY_IMPACT_SEVERITY = 'body_impact_severity';
export const BODY_BUSINESS_IMPACT = 'body_business_impact';
export const BODY_TRIGGER = 'body_trigger';
export const BODY_ROOT_CAUSE = 'body_root_cause';
export const BODY_FOLLOW_UP = 'body_follow_up';
export const APPENDIX_NOTES = 'appendix_notes';
export const APPENDIX_IMAGES = 'appendix_images';

export const PREVIEW_REQUIRED_FIELDS = [
  MANUAL_FAULT_DATE,
  MANUAL_FAULT_TIME,
  MANUAL_REPORTING_PERSON,
  MANUAL_SITE_ID,
  MANUAL_SYSTEM,
  MANUAL_LOCATION,
  MANUAL_FAULT_SYMPTOM,
  BODY_DESCRIPTION,
  BODY_TIMELINE,
  BODY_IMPACT_SCOPE,
  BODY_IMPACT_SEVERITY,
  BODY_ROOT_CAUSE,
  BODY_FOLLOW_UP,
];

export const STATUS_OPTION_FOLLOW_UP_ACTION_REQUIRED =
  'follow_up_action_required';
export const STATUS_OPTION_CLOSED = 'closed';

export const statusOptions = [
  { value: STATUS_OPTION_FOLLOW_UP_ACTION_REQUIRED, label: '跟进中' },
  { value: STATUS_OPTION_CLOSED, label: '已关闭' },
];

export const normalizeStatusOption = (value: string) => {
  const option = statusOptions.find(
    (item) => item.value === value || item.label === value,
  );
  return option?.value ?? value;
};

export const SEVERITY_OPTION_MINOR = 'minor';
export const SEVERITY_OPTION_MAJOR = 'major';
export const SEVERITY_OPTION_CRITICAL = 'critical';

export const severityOptions = [
  { value: SEVERITY_OPTION_MINOR, label: '一般' },
  { value: SEVERITY_OPTION_MAJOR, label: '严重' },
  { value: SEVERITY_OPTION_CRITICAL, label: '致命' },
];

export const normalizeSeverityOption = (value: string) => {
  const option = severityOptions.find(
    (item) => item.value === value || item.label === value,
  );
  return option?.value ?? value;
};

export const DOCX_SAFE_IMAGE_MIME_TYPES = new Set([
  'image/png',
  'image/jpeg',
  'image/gif',
  'image/bmp',
  'image/tiff',
]);
