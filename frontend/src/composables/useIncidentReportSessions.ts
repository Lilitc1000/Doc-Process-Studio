import {
  createIncidentSession,
  fetchIncidentSessionDetail,
  fetchIncidentSessionSummaries,
  removeIncidentSession,
  renameIncidentSession,
} from '../api/incident-report';
import { useIncidentStore } from '../stores/incident';
import { useIncidentForm } from './useIncidentForm';
import { useIncidentGeneration } from './useIncidentGeneration';

const buildIncidentSessionTitle = () => {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  const hour = String(now.getHours()).padStart(2, '0');
  const minute = String(now.getMinutes()).padStart(2, '0');
  return `事故报告-${year}/${month}/${day} ${hour}:${minute}`;
};

export const useIncidentReportSessions = () => {
  const incidentStore = useIncidentStore();

  const form = useIncidentForm();

  const generation = useIncidentGeneration({
    flushSaveIncidentSnapshot: form.flushSaveIncidentSnapshot,
  });

  const loadIncidentSessionSummaries = async () => {
    try {
      const sessions = await fetchIncidentSessionSummaries();
      incidentStore.incidentSessionSummaries = [...sessions].sort(
        (left, right) => {
          return (
            new Date(right.updated_at).getTime() -
            new Date(left.updated_at).getTime()
          );
        },
      );
    } catch (error) {
      console.error('加载事故报告历史会话失败。', error);
    }
  };

  const loadIncidentSession = async (sessionId: string) => {
    try {
      if (
        incidentStore.activeIncidentSessionId &&
        incidentStore.activeIncidentSessionId !== sessionId
      ) {
        try {
          await form.flushSaveIncidentSnapshot();
        } catch (error) {
          console.error('切换会话前保存当前事故报告失败。', error);
        }
        form.clearFormTimers();
      }
      const detail = await fetchIncidentSessionDetail(sessionId);
      incidentStore.activeIncidentSessionId = sessionId;
      incidentStore.applyIncidentDetail(detail);
      generation.resetGenerationState();
    } catch (error) {
      console.error('加载事故报告会话失败。', error);
      incidentStore.incidentErrorMessage =
        error instanceof Error ? error.message : '加载会话失败';
    }
  };

  const clearActiveIncidentSession = () => {
    form.clearFormTimers();
    generation.resetGenerationState();
    incidentStore.clearActiveIncidentSession();
  };

  const startIncidentSession = async () => {
    if (incidentStore.activeIncidentSessionId) {
      try {
        await form.flushSaveIncidentSnapshot();
      } catch (error) {
        console.error('新建会话前保存当前事故报告失败。', error);
      }
      form.clearFormTimers();
    }
    const summary = await createIncidentSession({
      title: buildIncidentSessionTitle(),
    });
    incidentStore.mergeSummary(summary);
    await loadIncidentSession(summary.id);
  };

  const renameIncident = async (sessionId: string, title: string) => {
    const summary = await renameIncidentSession(sessionId, title);
    incidentStore.mergeSummary(summary);
    if (incidentStore.activeIncidentSession?.id === sessionId) {
      incidentStore.activeIncidentSession = {
        ...incidentStore.activeIncidentSession,
        title: summary.title,
        updated_at: summary.updated_at,
      };
    }
  };

  const deleteIncident = async (sessionId: string) => {
    await removeIncidentSession(sessionId);
    incidentStore.incidentSessionSummaries =
      incidentStore.incidentSessionSummaries.filter(
        (item) => item.id !== sessionId,
      );
    if (incidentStore.activeIncidentSessionId === sessionId) {
      clearActiveIncidentSession();
    }
  };

  return {
    cancelIncidentPreview: generation.cancelIncidentPreview,
    clearActiveIncidentSession,
    deleteIncident,
    downloadIncidentPreviewDocx: generation.downloadIncidentPreviewDocx,
    flushSaveIncidentSnapshot: form.flushSaveIncidentSnapshot,
    generateBodySection: generation.generateBodySection,
    loadIncidentPreview: generation.loadIncidentPreview,
    quickGenerateBody: generation.quickGenerateBody,
    loadIncidentSchema: form.loadIncidentSchema,
    loadIncidentSession,
    loadIncidentSessionSummaries,
    renameIncident,
    startIncidentSession,
    stopIncidentGeneration: generation.stopIncidentGeneration,
    updateIncidentAnswers: form.updateIncidentAnswers,
  };
};
