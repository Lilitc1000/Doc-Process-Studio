export type IncidentReportStatus =
  | 'draft'
  | 'pending'
  | 'approved'
  | 'rejected'
  | 'in_progress'
  | 'closed';

export type IncidentSeverity = 'P0' | 'P1' | 'P2' | 'P3';

export interface IncidentReportFormAnswer {
  value?: unknown;
  customValue?: string;
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
  totalCount: number;
  draftCount: number;
  pendingCount: number;
  rejectedCount: number;
  approvedCount: number;
  inProgressCount: number;
  closedCount: number;
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
  assignedByName: string | null;
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

export interface IncidentUserWithRolesEntry {
  userId: string;
  username: string;
  roles: string[];
}

export interface IncidentUserWithRolesListResponse {
  items: IncidentUserWithRolesEntry[];
}

export const INCIDENT_ROLE_LABELS: Record<string, string> = {
  admin: '管理员',
  verifier: '审核人',
  handler: '处理人',
  reporter: '报告人',
  viewer: '观察者',
};

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
