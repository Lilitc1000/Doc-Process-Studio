import { apiClient } from './request';
import type {
  IncidentReportBodyGenerateResponse,
  IncidentReportFormSchemaPayload,
  IncidentReportPreviewResponse,
  IncidentReportSessionDetail,
  IncidentReportSessionSummary,
  IncidentReportSnapshot,
} from '../types/incident-report/incident-report';

export const fetchIncidentReportFormSchema =
  async (): Promise<IncidentReportFormSchemaPayload> => {
    const response = await apiClient.get<IncidentReportFormSchemaPayload>(
      '/incident-report/schema',
    );
    return response.data;
  };

export const fetchIncidentReportSessionSummaries = async (): Promise<
  IncidentReportSessionSummary[]
> => {
  const response = await apiClient.get<{
    sessions: IncidentReportSessionSummary[];
  }>('/incident-report/sessions');
  return response.data.sessions ?? [];
};

export const createIncidentReportSession = async (payload: {
  title: string;
}): Promise<IncidentReportSessionSummary> => {
  const response = await apiClient.post<IncidentReportSessionSummary>(
    '/incident-report/sessions',
    payload,
  );
  return response.data;
};

export const fetchIncidentReportSessionDetail = async (
  sessionId: string,
): Promise<IncidentReportSessionDetail> => {
  const response = await apiClient.get<IncidentReportSessionDetail>(
    `/incident-report/sessions/${sessionId}`,
  );
  return response.data;
};

export const saveIncidentReportSessionSnapshot = async (
  sessionId: string,
  snapshot: IncidentReportSnapshot,
): Promise<IncidentReportSessionDetail> => {
  const response = await apiClient.put<IncidentReportSessionDetail>(
    `/incident-report/sessions/${sessionId}/snapshot`,
    { snapshot },
  );
  return response.data;
};

export const quickGenerateIncidentReportBody = async (
  sessionId: string,
  payload: { model: string; rerankerModel?: string },
  options?: { signal?: AbortSignal },
): Promise<IncidentReportBodyGenerateResponse> => {
  const response = await apiClient.post<IncidentReportBodyGenerateResponse>(
    `/incident-report/sessions/${sessionId}/quick-generate`,
    payload,
    { signal: options?.signal },
  );
  return response.data;
};

export const generateIncidentReportBodySection = async (
  sessionId: string,
  payload: {
    model: string;
    rerankerModel?: string;
    sectionId: string;
    timelineIndex?: number;
  },
  options?: { signal?: AbortSignal },
): Promise<IncidentReportBodyGenerateResponse> => {
  const response = await apiClient.post<IncidentReportBodyGenerateResponse>(
    `/incident-report/sessions/${sessionId}/generate-section`,
    payload,
    { signal: options?.signal },
  );
  return response.data;
};

export const previewIncidentReportAttachment = async (
  sessionId: string,
  payload: {
    version?: number;
    model?: string;
    rerankerModel?: string;
  },
  options?: { signal?: AbortSignal },
): Promise<IncidentReportPreviewResponse> => {
  const response = await apiClient.post<IncidentReportPreviewResponse>(
    `/incident-report/sessions/${sessionId}/preview`,
    payload,
    { signal: options?.signal },
  );
  return response.data;
};

export const renameIncidentReportSession = async (
  sessionId: string,
  title: string,
): Promise<IncidentReportSessionSummary> => {
  const response = await apiClient.patch<IncidentReportSessionSummary>(
    `/incident-report/sessions/${sessionId}`,
    { title },
  );
  return response.data;
};

export const removeIncidentReportSession = async (
  sessionId: string,
): Promise<void> => {
  await apiClient.delete(`/incident-report/sessions/${sessionId}`);
};
