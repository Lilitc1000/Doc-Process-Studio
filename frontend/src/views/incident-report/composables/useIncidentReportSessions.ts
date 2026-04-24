import {
  createIncidentReportSession,
  fetchIncidentReportSessionDetail,
  fetchIncidentReportSessionSummaries,
  removeIncidentReportSession,
  renameIncidentReportSession,
} from '../../../api/incident-report';
import { useIncidentReportStore } from '../../../stores/incident-report';
import { useIncidentReportForm } from './useIncidentReportForm';
import { useIncidentReportGeneration } from './useIncidentReportGeneration';
import { getErrorMessage } from '../../../utils/common/error';

const buildIncidentReportSessionTitle = () => {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  const hour = String(now.getHours()).padStart(2, '0');
  const minute = String(now.getMinutes()).padStart(2, '0');
  return `事故报告-${year}/${month}/${day} ${hour}:${minute}`;
};

export const useIncidentReportSessions = () => {
  const incidentReportStore = useIncidentReportStore();

  const form = useIncidentReportForm();

  const generation = useIncidentReportGeneration({
    flushSaveIncidentReportSnapshot: form.flushSaveIncidentReportSnapshot,
  });

  const loadIncidentReportSessionSummaries = async () => {
    try {
      const sessions = await fetchIncidentReportSessionSummaries();
      incidentReportStore.incidentReportSessionSummaries = [...sessions].sort(
        (left, right) => {
          return (
            new Date(right.createdAt).getTime() -
            new Date(left.createdAt).getTime()
          );
        },
      );
    } catch (error) {
      console.error('加载事故报告历史会话失败。', error);
    }
  };

  const loadIncidentReportSession = async (sessionId: string) => {
    try {
      if (
        incidentReportStore.activeIncidentReportSessionId &&
        incidentReportStore.activeIncidentReportSessionId !== sessionId
      ) {
        try {
          await form.flushSaveIncidentReportSnapshot();
        } catch (error) {
          console.error('切换会话前保存当前事故报告失败。', error);
        }
        form.clearFormTimers();
      }
      const detail = await fetchIncidentReportSessionDetail(sessionId);
      incidentReportStore.activeIncidentReportSessionId = sessionId;
      incidentReportStore.applyIncidentReportDetail(detail);
      generation.resetGenerationState();
    } catch (error) {
      console.error('加载事故报告会话失败。', error);
      incidentReportStore.incidentReportErrorMessage = getErrorMessage(
        error,
        '加载会话失败',
      );
    }
  };

  const clearActiveIncidentReportSession = () => {
    form.clearFormTimers();
    generation.resetGenerationState();
    incidentReportStore.clearActiveIncidentReportSession();
  };

  const startIncidentReportSession = async () => {
    if (incidentReportStore.activeIncidentReportSessionId) {
      try {
        await form.flushSaveIncidentReportSnapshot();
      } catch (error) {
        console.error('新建会话前保存当前事故报告失败。', error);
      }
      form.clearFormTimers();
    }
    const summary = await createIncidentReportSession({
      title: buildIncidentReportSessionTitle(),
    });
    incidentReportStore.mergeSummary(summary);
    await loadIncidentReportSession(summary.id);
  };

  const renameIncidentReport = async (sessionId: string, title: string) => {
    const summary = await renameIncidentReportSession(sessionId, title);
    incidentReportStore.mergeSummary(summary);
    if (incidentReportStore.activeIncidentReportSession?.id === sessionId) {
      incidentReportStore.activeIncidentReportSession = {
        ...incidentReportStore.activeIncidentReportSession,
        title: summary.title,
        updatedAt: summary.updatedAt,
      };
    }
  };

  const deleteIncidentReport = async (sessionId: string) => {
    await removeIncidentReportSession(sessionId);
    incidentReportStore.incidentReportSessionSummaries =
      incidentReportStore.incidentReportSessionSummaries.filter(
        (item) => item.id !== sessionId,
      );
    if (incidentReportStore.activeIncidentReportSessionId === sessionId) {
      clearActiveIncidentReportSession();
    }
  };

  return {
    cancelIncidentReportPreview: generation.cancelIncidentReportPreview,
    clearActiveIncidentReportSession,
    deleteIncidentReport,
    downloadIncidentReportPreviewDocx:
      generation.downloadIncidentReportPreviewDocx,
    flushSaveIncidentReportSnapshot: form.flushSaveIncidentReportSnapshot,
    generateBodySection: generation.generateBodySection,
    loadIncidentReportPreview: generation.loadIncidentReportPreview,
    quickGenerateBody: generation.quickGenerateBody,
    loadIncidentReportSchema: form.loadIncidentReportSchema,
    loadIncidentReportSession,
    loadIncidentReportSessionSummaries,
    renameIncidentReport,
    startIncidentReportSession,
    stopIncidentReportGeneration: generation.stopIncidentReportGeneration,
    updateIncidentReportAnswers: form.updateIncidentReportAnswers,
  };
};
