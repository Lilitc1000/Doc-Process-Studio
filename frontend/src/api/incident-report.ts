import { apiClient } from './request';
import type {
  IncidentReportFormSchemaPayload,
  IncidentReportPreviewResponse,
  IncidentReportListResponse,
  IncidentReportDetailItem,
  IncidentAuditLogEntry,
  IncidentCommentEntry,
  IncidentAnalyticsOverview,
  IncidentAnalyticsTrend,
  IncidentUserRolesResponse,
  IncidentRoleEntry,
} from '../types/incident-report/incident-report';

export const fetchIncidentReportFormSchema =
  async (): Promise<IncidentReportFormSchemaPayload> => {
    const response = await apiClient.get<IncidentReportFormSchemaPayload>(
      '/incident-report/schema',
    );
    return response.data;
  };

export const fetchIncidentReportSchema = async (): Promise<Record<string, unknown>> => {
  const response = await apiClient.get<Record<string, unknown>>(
    '/incident-report/reports/schema',
  );
  return response.data;
};

export const fetchIncidentReportList = async (params: {
  page?: number;
  pageSize?: number;
  status?: string;
  severity?: string;
  search?: string;
  startDate?: string;
  endDate?: string;
}): Promise<IncidentReportListResponse> => {
  const response = await apiClient.get<IncidentReportListResponse>(
    '/incident-report/reports',
    { params },
  );
  return response.data;
};

export const fetchIncidentReportDetail = async (
  reportId: string,
): Promise<IncidentReportDetailItem> => {
  const response = await apiClient.get<IncidentReportDetailItem>(
    `/incident-report/reports/${reportId}`,
  );
  return response.data;
};

export const createIncidentReport = async (payload: {
  title: string;
  severity?: string;
  system?: string;
  site_id?: string;
  fault_date?: string;
  form_data?: Record<string, unknown>;
}): Promise<IncidentReportDetailItem> => {
  const response = await apiClient.post<IncidentReportDetailItem>(
    '/incident-report/reports',
    payload,
  );
  return response.data;
};

export const updateIncidentReport = async (
  reportId: string,
  payload: {
    title?: string;
    severity?: string;
    system?: string;
    site_id?: string;
    fault_date?: string;
    form_data?: Record<string, unknown>;
  },
): Promise<IncidentReportDetailItem> => {
  const response = await apiClient.put<IncidentReportDetailItem>(
    `/incident-report/reports/${reportId}`,
    payload,
  );
  return response.data;
};

export const deleteIncidentReport = async (
  reportId: string,
): Promise<void> => {
  await apiClient.delete(`/incident-report/reports/${reportId}`);
};

export const submitIncidentReport = async (
  reportId: string,
  comment?: string,
): Promise<IncidentReportDetailItem> => {
  const response = await apiClient.post<IncidentReportDetailItem>(
    `/incident-report/reports/${reportId}/submit`,
    { comment },
  );
  return response.data;
};

export const approveIncidentReport = async (
  reportId: string,
  comment: string,
): Promise<IncidentReportDetailItem> => {
  const response = await apiClient.post<IncidentReportDetailItem>(
    `/incident-report/reports/${reportId}/approve`,
    { comment },
  );
  return response.data;
};

export const rejectIncidentReport = async (
  reportId: string,
  comment: string,
): Promise<IncidentReportDetailItem> => {
  const response = await apiClient.post<IncidentReportDetailItem>(
    `/incident-report/reports/${reportId}/reject`,
    { comment },
  );
  return response.data;
};

export const assignIncidentReport = async (
  reportId: string,
  assigneeId: string,
): Promise<IncidentReportDetailItem> => {
  const response = await apiClient.post<IncidentReportDetailItem>(
    `/incident-report/reports/${reportId}/assign`,
    { assignee_id: assigneeId },
  );
  return response.data;
};

export const closeIncidentReport = async (
  reportId: string,
  comment?: string,
): Promise<IncidentReportDetailItem> => {
  const response = await apiClient.post<IncidentReportDetailItem>(
    `/incident-report/reports/${reportId}/close`,
    { comment },
  );
  return response.data;
};

export const reopenIncidentReport = async (
  reportId: string,
  comment?: string,
): Promise<IncidentReportDetailItem> => {
  const response = await apiClient.post<IncidentReportDetailItem>(
    `/incident-report/reports/${reportId}/reopen`,
    { comment },
  );
  return response.data;
};

export const fetchIncidentReportAuditLogs = async (
  reportId: string,
): Promise<IncidentAuditLogEntry[]> => {
  const response = await apiClient.get<IncidentAuditLogEntry[]>(
    `/incident-report/reports/${reportId}/audit-logs`,
  );
  return response.data;
};

export const fetchIncidentReportComments = async (
  reportId: string,
): Promise<IncidentCommentEntry[]> => {
  const response = await apiClient.get<IncidentCommentEntry[]>(
    `/incident-report/reports/${reportId}/comments`,
  );
  return response.data;
};

export const createIncidentReportComment = async (
  reportId: string,
  payload: { content: string; parent_id?: string },
): Promise<IncidentCommentEntry> => {
  const response = await apiClient.post<IncidentCommentEntry>(
    `/incident-report/reports/${reportId}/comments`,
    payload,
  );
  return response.data;
};

export const fetchIncidentAnalyticsOverview =
  async (): Promise<IncidentAnalyticsOverview> => {
    const response = await apiClient.get<IncidentAnalyticsOverview>(
      '/incident-report/analytics/overview',
    );
    return response.data;
  };

export const fetchIncidentAnalyticsTrend = async (
  days?: number,
): Promise<IncidentAnalyticsTrend[]> => {
  const response = await apiClient.get<IncidentAnalyticsTrend[]>(
    '/incident-report/analytics/trend',
    { params: { days } },
  );
  return response.data;
};

export const fetchUserIncidentRoles = async (): Promise<string[]> => {
  const response = await apiClient.get<IncidentUserRolesResponse>(
    '/incident-report/roles/me',
  );
  return response.data.roles ?? [];
};

export const fetchAllIncidentRoles = async (): Promise<IncidentRoleEntry[]> => {
  const response = await apiClient.get<{ items: IncidentRoleEntry[] }>(
    '/incident-report/roles',
  );
  return response.data.items ?? [];
};

export const assignIncidentRole = async (payload: {
  user_id: string;
  role: string;
}): Promise<IncidentRoleEntry> => {
  const response = await apiClient.post<IncidentRoleEntry>(
    '/incident-report/roles',
    payload,
  );
  return response.data;
};

export const revokeIncidentRole = async (
  userId: string,
  role: string,
): Promise<void> => {
  await apiClient.delete(`/incident-report/roles/${userId}/${role}`);
};

export const previewIncidentReport = async (
  reportId: string,
  payload: {
    version?: number;
    model?: string;
    rerankerModel?: string;
  },
  options?: { signal?: AbortSignal },
): Promise<IncidentReportPreviewResponse> => {
  const response = await apiClient.post<IncidentReportPreviewResponse>(
    `/incident-report/reports/${reportId}/preview`,
    payload,
    { signal: options?.signal },
  );
  return response.data;
};
