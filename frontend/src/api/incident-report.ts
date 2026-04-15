import { apiClient } from './client';
import type {
  IncidentFormSchemaPayload,
  IncidentGenerateResponse,
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

export const generateIncidentAttachment = async (
  sessionId: string,
  payload: {
    model: string;
    reranker_model?: string;
    output_name?: string;
  },
  options?: {
    signal?: AbortSignal;
  },
) => {
  const response = await apiClient.post<IncidentGenerateResponse>(
    `/incident-report/sessions/${sessionId}/generate`,
    payload,
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
