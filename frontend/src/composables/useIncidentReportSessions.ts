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
      const detail = await fetchIncidentSessionDetail(sessionId);
      incidentStore.activeIncidentSessionId = sessionId;
      incidentStore.applyIncidentDetail(detail);
      generation.resetGenerationState();

      incidentStore.incidentGenerationTraceId = (
        detail.snapshot.generated_trace_id ?? ''
      ).trim();
      if (incidentStore.incidentGenerationTraceId) {
        await generation.refreshGenerationTraceProgress(
          incidentStore.incidentGenerationTraceId,
        );
      } else {
        incidentStore.incidentGenerationProgress = [];
      }

      generation.resumeGenerationMonitorIfNeeded(sessionId, detail.status);
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
    clearActiveIncidentSession,
    closeGenerationNotice: generation.closeGenerationNotice,
    deleteIncident,
    downloadGeneratedIncidentAttachment:
      generation.downloadGeneratedIncidentAttachment,
    flushSaveIncidentSnapshot: form.flushSaveIncidentSnapshot,
    generateIncident: generation.generateIncident,
    loadIncidentSchema: form.loadIncidentSchema,
    loadIncidentSession,
    loadIncidentSessionSummaries,
    renameIncident,
    startIncidentSession,
    stopIncidentGeneration: generation.stopIncidentGeneration,
    updateIncidentAnswers: form.updateIncidentAnswers,
  };
};
