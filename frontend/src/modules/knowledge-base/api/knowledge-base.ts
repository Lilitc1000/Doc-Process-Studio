import { apiClient } from '@shared/api/request';
import type {
  KBProject,
  KBDocument,
  KBTreeResponse,
  KBProjectSimple,
} from '../types/knowledge-base';

export const listKBProjects = async (): Promise<KBProject[]> => {
  const response = await apiClient.get<{ projects: KBProject[] }>(
    '/knowledge-base/projects',
  );
  return response.data.projects;
};

export const createKBProject = async (
  name: string,
  description = '',
): Promise<KBProject> => {
  const response = await apiClient.post<KBProject>('/knowledge-base/projects', {
    name,
    description,
  });
  return response.data;
};

export const renameKBProject = async (
  projectId: string,
  name: string,
): Promise<KBProject> => {
  const response = await apiClient.put<KBProject>(
    `/knowledge-base/projects/${projectId}/rename`,
    { name },
  );
  return response.data;
};

export const deleteKBProject = async (projectId: string): Promise<void> => {
  await apiClient.delete(`/knowledge-base/projects/${projectId}`);
};

export const getKBTree = async (projectId: string): Promise<KBTreeResponse> => {
  const response = await apiClient.get<KBTreeResponse>(
    `/knowledge-base/projects/${projectId}/tree`,
  );
  return response.data;
};

export const uploadKBDocument = async (
  projectId: string,
  file: File,
): Promise<KBDocument> => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await apiClient.post<KBDocument>(
    `/knowledge-base/projects/${projectId}/documents/upload`,
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  );
  return response.data;
};

export const deleteKBDocument = async (documentId: string): Promise<void> => {
  await apiClient.delete(`/knowledge-base/documents/${documentId}`);
};

export const listKBProjectsSimple = async (): Promise<KBProjectSimple[]> => {
  const response = await apiClient.get<{ projects: KBProjectSimple[] }>(
    '/knowledge-base/projects-simple',
  );
  return response.data.projects;
};
