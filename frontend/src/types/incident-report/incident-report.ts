export type IncidentReportStatus =
  | 'draft'
  | 'pending'
  | 'approved'
  | 'rejected'
  | 'in_progress'
  | 'closed';

export type IncidentSeverity = 'P0' | 'P1' | 'P2' | 'P3';

export interface IncidentReportFormOption {
  value: string;
  label: string;
  description?: string | null;
}

export type IncidentReportFormKind = 'single_select' | 'multi_select' | 'text';

export interface IncidentReportFormStep {
  id: string;
  title: string;
  prompt: string;
  fieldPath: string;
  kind: IncidentReportFormKind;
  options: IncidentReportFormOption[];
  allowCustom: boolean;
  required: boolean;
  placeholder?: string | null;
}

export interface IncidentReportFormAnswer {
  value?: unknown;
  customValue?: string;
}

export interface IncidentReportFormSchemaPayload {
  introMessage: string;
  steps: IncidentReportFormStep[];
}

export interface IncidentReportPreviewResponse {
  source: 'draft' | 'version';
  version?: number | null;
  label: string;
  html: string;
  docxBase64?: string | null;
  docxFileName?: string | null;
  pdfBase64?: string | null;
  warnings: string[];
}

export interface IncidentReportSummaryItem {
  id: string;
  ref_no: string;
  title: string;
  status: IncidentReportStatus;
  severity: IncidentSeverity | null;
  reporter_id: string;
  reporter_name: string | null;
  assignee_id: string | null;
  assignee_name: string | null;
  verifier_id: string | null;
  verifier_name: string | null;
  fault_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface IncidentReportDetailItem extends IncidentReportSummaryItem {
  system: string | null;
  site_id: string | null;
  form_data: Record<string, unknown>;
  report_data: Record<string, unknown> | null;
  submitted_at: string | null;
  approved_at: string | null;
  closed_at: string | null;
  resolution_date: string | null;
}

export interface IncidentReportListResponse {
  total: number;
  items: IncidentReportSummaryItem[];
}

export interface IncidentAuditLogEntry {
  id: string;
  action: string;
  actor_id: string;
  actor_name: string | null;
  from_status: string | null;
  to_status: string | null;
  comment: string | null;
  created_at: string;
}

export interface IncidentCommentEntry {
  id: string;
  report_id: string;
  author_id: string;
  author_name: string | null;
  content: string;
  parent_id: string | null;
  created_at: string;
}

export interface IncidentAnalyticsOverview {
  total_this_month: number;
  pending_count: number;
  in_progress_count: number;
  closed_this_month: number;
  avg_resolution_hours: number | null;
}

export interface IncidentAnalyticsTrend {
  date: string;
  count: number;
}

export interface IncidentUserRolesResponse {
  user_id: string;
  roles: string[];
}

export interface IncidentRoleEntry {
  user_id: string;
  role: string;
  assigned_by: string | null;
  assigned_at: string | null;
}

export const INCIDENT_STATUS_LABELS: Record<IncidentReportStatus, string> = {
  draft: '草稿',
  pending: '待审核',
  approved: '已批准',
  rejected: '已驳回',
  in_progress: '处理中',
  closed: '已关闭',
};

export const INCIDENT_SEVERITY_LABELS: Record<IncidentSeverity, string> = {
  P0: 'P0 - 紧急',
  P1: 'P1 - 严重',
  P2: 'P2 - 一般',
  P3: 'P3 - 轻微',
};
