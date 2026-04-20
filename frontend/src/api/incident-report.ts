import { apiClient } from './client';
import type {
  IncidentBodyGenerateResponse,
  IncidentFormSchemaPayload,
  IncidentPreviewResponse,
  IncidentSessionDetail,
  IncidentSessionSummary,
  IncidentSnapshot,
} from '../types/incident-report';

export const fetchIncidentFormSchema =
  async (): Promise<IncidentFormSchemaPayload> => {
    const response = await apiClient.get<IncidentFormSchemaPayload>(
      '/incident-report/schema',
    );
    return response.data;
  };

export const fetchIncidentSessionSummaries = async (): Promise<
  IncidentSessionSummary[]
> => {
  const response = await apiClient.get<{
    sessions?: IncidentSessionSummary[];
  }>('/incident-report/sessions');
  return response.data.sessions ?? [];
};

export const createIncidentSession = async (payload: { title: string }) => {
  const response = await apiClient.post<IncidentSessionSummary>(
    '/incident-report/sessions',
    payload,
  );
  return response.data;
};

export const fetchIncidentSessionDetail = async (sessionId: string) => {
  const response = await apiClient.get<IncidentSessionDetail>(
    `/incident-report/sessions/${sessionId}`,
  );
  return response.data;
};

export const saveIncidentSessionSnapshot = async (
  sessionId: string,
  snapshot: IncidentSnapshot,
) => {
  const response = await apiClient.put<IncidentSessionDetail>(
    `/incident-report/sessions/${sessionId}`,
    { snapshot },
  );
  return response.data;
};

export const quickGenerateIncidentBody = async (
  sessionId: string,
  payload: {
    model: string;
    reranker_model?: string;
  },
  options?: {
    signal?: AbortSignal;
  },
) => {
  const response = await apiClient.post<IncidentBodyGenerateResponse>(
    `/incident-report/sessions/${sessionId}/body/quick-generate`,
    payload,
    {
      signal: options?.signal,
    },
  );
  return response.data;
};

export const generateIncidentBodySection = async (
  sessionId: string,
  payload: {
    model: string;
    reranker_model?: string;
    section_id: string;
    timeline_index?: number;
  },
  options?: {
    signal?: AbortSignal;
  },
) => {
  const response = await apiClient.post<IncidentBodyGenerateResponse>(
    `/incident-report/sessions/${sessionId}/body/section-generate`,
    payload,
    {
      signal: options?.signal,
    },
  );
  return response.data;
};

export const previewIncidentAttachment = async (
  sessionId: string,
  payload?: {
    version?: number;
    model?: string;
    reranker_model?: string;
  },
  options?: {
    signal?: AbortSignal;
  },
) => {
  const response = await apiClient.post<IncidentPreviewResponse>(
    `/incident-report/sessions/${sessionId}/preview`,
    {
      version: payload?.version ?? null,
      model: payload?.model ?? null,
      reranker_model: payload?.reranker_model ?? null,
    },
    {
      signal: options?.signal,
    },
  );
  return response.data;
};

export const renameIncidentSession = async (
  sessionId: string,
  title: string,
) => {
  const response = await apiClient.patch<IncidentSessionSummary>(
    `/incident-report/sessions/${sessionId}/title`,
    { title },
  );
  return response.data;
};

export const removeIncidentSession = async (sessionId: string) => {
  await apiClient.delete(`/incident-report/sessions/${sessionId}`);
};
