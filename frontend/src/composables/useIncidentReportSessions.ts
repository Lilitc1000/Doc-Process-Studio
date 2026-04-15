import { computed, ref } from 'vue';
import {
  createIncidentSession,
  fetchIncidentSessionDetail,
  fetchIncidentSessionSummaries,
  removeIncidentSession,
  renameIncidentSession,
} from '../api/incident-report';
import type { ChatSessionSummary } from '../types/session';
import type {
  IncidentSessionDetail,
  IncidentSessionSummary,
} from '../types/incident-report';
import { useIncidentForm } from './useIncidentForm';
import { useIncidentGeneration } from './useIncidentGeneration';

const formatIncidentStatusLabel = (
  status: IncidentSessionSummary['status'],
) => {
  if (status === 'generated') {
    return '已生成';
  }
  if (status === 'generating') {
    return '生成中';
  }
  if (status === 'failed') {
    return '失败';
  }
  return '未生成';
};

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
  const incidentSessionSummaries = ref<IncidentSessionSummary[]>([]);
  const activeIncidentSessionId = ref<string | null>(null);
  const activeIncidentSession = ref<IncidentSessionDetail | null>(null);

  const mergeSummary = (summary: IncidentSessionSummary) => {
    const next = incidentSessionSummaries.value.filter((item) => {
      return item.id !== summary.id;
    });
    next.unshift(summary);
    next.sort((left, right) => {
      return (
        new Date(right.updated_at).getTime() -
        new Date(left.updated_at).getTime()
      );
    });
    incidentSessionSummaries.value = next;
  };

  const incidentSidebarSessions = computed<ChatSessionSummary[]>(() => {
    return incidentSessionSummaries.value.map((summary) => ({
      id: summary.id,
      title: summary.title,
      status: summary.status,
      status_label: formatIncidentStatusLabel(summary.status),
      created_at: summary.created_at,
      updated_at: summary.updated_at,
      selected_model: '',
      selected_reranker_model: null,
    }));
  });

  const applyIncidentDetail = (detail: IncidentSessionDetail) => {
    if (activeIncidentSessionId.value !== detail.id) {
      return;
    }
    activeIncidentSession.value = detail;
    mergeSummary({
      id: detail.id,
      title: detail.title,
      status: detail.status,
      created_at: detail.created_at,
      updated_at: detail.updated_at,
    });
  };

  const form = useIncidentForm({
    activeIncidentSessionId,
    activeIncidentSession,
    mergeSummary,
  });

  const generation = useIncidentGeneration({
    activeIncidentSessionId,
    activeIncidentSession,
    applyIncidentDetail,
    mergeSummary,
    flushSaveIncidentSnapshot: form.flushSaveIncidentSnapshot,
  });

  const loadIncidentSessionSummaries = async () => {
    try {
      const sessions = await fetchIncidentSessionSummaries();
      incidentSessionSummaries.value = [...sessions].sort((left, right) => {
        return (
          new Date(right.updated_at).getTime() -
          new Date(left.updated_at).getTime()
        );
      });
    } catch (error) {
      console.error('加载事故报告历史会话失败。', error);
    }
  };

  const loadIncidentSession = async (sessionId: string) => {
    try {
      const detail = await fetchIncidentSessionDetail(sessionId);
      activeIncidentSessionId.value = sessionId;
      applyIncidentDetail(detail);
      generation.resetGenerationState();

      generation.incidentGenerationTraceId.value = (
        detail.snapshot.generated_trace_id ?? ''
      ).trim();
      if (generation.incidentGenerationTraceId.value) {
        await generation.refreshGenerationTraceProgress(
          generation.incidentGenerationTraceId.value,
        );
      } else {
        generation.incidentGenerationProgress.value = [];
      }

      generation.resumeGenerationMonitorIfNeeded(sessionId, detail.status);
    } catch (error) {
      console.error('加载事故报告会话失败。', error);
      generation.incidentErrorMessage.value =
        error instanceof Error ? error.message : '加载会话失败';
    }
  };

  const clearActiveIncidentSession = () => {
    form.clearFormTimers();
    generation.resetGenerationState();
    activeIncidentSessionId.value = null;
    activeIncidentSession.value = null;
  };

  const startIncidentSession = async () => {
    const summary = await createIncidentSession({
      title: buildIncidentSessionTitle(),
    });
    mergeSummary(summary);
    await loadIncidentSession(summary.id);
  };

  const renameIncident = async (sessionId: string, title: string) => {
    const summary = await renameIncidentSession(sessionId, title);
    mergeSummary(summary);
    if (activeIncidentSession.value?.id === sessionId) {
      activeIncidentSession.value = {
        ...activeIncidentSession.value,
        title: summary.title,
        updated_at: summary.updated_at,
      };
    }
  };

  const deleteIncident = async (sessionId: string) => {
    await removeIncidentSession(sessionId);
    incidentSessionSummaries.value = incidentSessionSummaries.value.filter(
      (item) => item.id !== sessionId,
    );
    if (activeIncidentSessionId.value === sessionId) {
      clearActiveIncidentSession();
    }
  };

  return {
    activeIncidentSession,
    activeIncidentSessionId,
    clearActiveIncidentSession,
    closeGenerationNotice: generation.closeGenerationNotice,
    deleteIncident,
    downloadGeneratedIncidentAttachment:
      generation.downloadGeneratedIncidentAttachment,
    flushSaveIncidentSnapshot: form.flushSaveIncidentSnapshot,
    generateIncident: generation.generateIncident,
    generationState: generation.generationState,
    incidentErrorMessage: generation.incidentErrorMessage,
    incidentGenerationProgress: generation.incidentGenerationProgress,
    incidentGenerationTraceId: generation.incidentGenerationTraceId,
    incidentSchema: form.incidentSchema,
    incidentSessionSummaries,
    incidentSidebarSessions,
    isIncidentGenerating: generation.isIncidentGenerating,
    loadIncidentSchema: form.loadIncidentSchema,
    loadIncidentSession,
    loadIncidentSessionSummaries,
    renameIncident,
    startIncidentSession,
    stopIncidentGeneration: generation.stopIncidentGeneration,
    updateIncidentAnswers: form.updateIncidentAnswers,
  };
};
