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

export interface IncidentBodyGenerateResponse {
  reportId: string;
  formAnswers: Record<string, IncidentReportFormAnswer>;
  traceId: string;
  sectionId: string;
  timelineIndex: number | null;
}

export interface IncidentReportSummaryItem {
  id: string;
  refNo: string;
  title: string;
  status: IncidentReportStatus;
  severity: IncidentSeverity | null;
  reporterId: string;
  reporterName: string | null;
  assigneeId: string | null;
  assigneeName: string | null;
  verifierId: string | null;
  verifierName: string | null;
  faultDate: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface IncidentReportDetailItem extends IncidentReportSummaryItem {
  system: string | null;
  siteId: string | null;
  formData: Record<string, unknown>;
  reportData: Record<string, unknown> | null;
  submittedAt: string | null;
  approvedAt: string | null;
  closedAt: string | null;
  resolutionDate: string | null;
}

export interface IncidentReportListResponse {
  total: number;
  items: IncidentReportSummaryItem[];
}

export interface IncidentAuditLogEntry {
  id: string;
  action: string;
  actorId: string;
  actorName: string | null;
  fromStatus: string | null;
  toStatus: string | null;
  comment: string | null;
  createdAt: string;
}

export interface IncidentCommentEntry {
  id: string;
  reportId: string;
  authorId: string;
  authorName: string | null;
  content: string;
  parentId: string | null;
  createdAt: string;
}

export interface IncidentAnalyticsOverview {
  totalThisMonth: number;
  pendingCount: number;
  inProgressCount: number;
  closedThisMonth: number;
  avgResolutionHours: number | null;
}

export interface IncidentAnalyticsTrend {
  date: string;
  count: number;
}

export interface IncidentUserRolesResponse {
  userId: string;
  roles: string[];
  permissions: string[];
}

export interface IncidentRoleEntry {
  userId: string;
  role: string;
  assignedBy: string | null;
  assignedAt: string | null;
}

export interface IncidentRoleDefinitionEntry {
  roleKey: string;
  roleName: string;
  description: string | null;
  permissions: string[];
}

export interface IncidentRoleDefinitionListResponse {
  items: IncidentRoleDefinitionEntry[];
}

export interface IncidentPermissionEntry {
  permissionKey: string;
  permissionName: string;
  description: string | null;
  category: string;
}

export interface IncidentPermissionListResponse {
  items: IncidentPermissionEntry[];
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
