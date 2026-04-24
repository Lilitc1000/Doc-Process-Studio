import type {
  ChatSessionDetail,
  ChatSessionSnapshotPayload,
  ChatSessionSummary,
} from '../types/chat/session';
import { apiClient } from './request';

export const fetchSessionSummaries = async () => {
  const response = await apiClient.get<{
    sessions?: ChatSessionSummary[];
  }>('/chat-sessions');

  return response.data.sessions ?? [];
};

export const saveSession = async (
  sessionId: string,
  payload: {
    title: string;
    titleSourceMessages: string[];
    snapshot: ChatSessionSnapshotPayload;
  },
) => {
  const response = await apiClient.put<ChatSessionSummary>(
    `/chat-sessions/${sessionId}`,
    payload,
  );

  return response.data;
};

export const fetchSessionDetail = async (sessionId: string) => {
  const response = await apiClient.get<ChatSessionDetail>(
    `/chat-sessions/${sessionId}`,
  );

  return response.data;
};

export const renameSession = async (sessionId: string, title: string) => {
  const response = await apiClient.patch<ChatSessionSummary>(
    `/chat-sessions/${sessionId}/title`,
    { title },
  );

  return response.data;
};

export const removeSession = async (sessionId: string) => {
  await apiClient.delete(`/chat-sessions/${sessionId}`);
};
