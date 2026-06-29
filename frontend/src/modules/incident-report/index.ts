// incident-report 模块桶文件：统一导出事故报告域公共 API

// --- Store ---
export { useIncidentReportStore } from './store/incident-report';

// --- API ---
export {
  fetchIncidentReportList,
  fetchIncidentReportDetail,
  createIncidentReport,
  updateIncidentReport,
  deleteIncidentReport,
  submitIncidentReport,
  approveIncidentReport,
  rejectIncidentReport,
  assignIncidentReport,
  closeIncidentReport,
  reopenIncidentReport,
  fetchIncidentReportAuditLogs,
  fetchIncidentReportComments,
  createIncidentReportComment,
  fetchIncidentAnalyticsOverview,
  fetchIncidentAnalyticsTrend,
  fetchUserIncidentRolesAndPermissions,
  fetchUsersWithRoles,
  assignIncidentRole,
  revokeIncidentRole,
  previewIncidentReport,
  quickGenerateIncidentReportBody,
  generateIncidentReportBodySection,
} from './api/incident-report';

// --- Types ---
export type {
  IncidentReportStatus,
  IncidentSeverity,
  IncidentReportFormAnswer,
  IncidentReportPreviewResponse,
  IncidentBodyGenerateResponse,
  IncidentReportSummaryItem,
  IncidentReportDetailItem,
  IncidentReportListResponse,
  IncidentAuditLogEntry,
  IncidentCommentEntry,
  IncidentAnalyticsOverview,
  IncidentAnalyticsTrend,
  IncidentUserRolesResponse,
  IncidentRoleEntry,
  IncidentUserWithRolesEntry,
  IncidentUserWithRolesListResponse,
} from './types/incident-report';
export {
  INCIDENT_ROLE_LABELS,
  INCIDENT_STATUS_LABELS,
  INCIDENT_SEVERITY_LABELS,
} from './types/incident-report';

// --- Utils ---
export { statusOptions, severityOptions } from './utils/constants';
