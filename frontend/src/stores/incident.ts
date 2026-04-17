import { defineStore } from 'pinia';
import { computed, ref } from 'vue';
import type {
  IncidentFormSchemaPayload,
  IncidentSessionDetail,
  IncidentSessionSummary,
} from '../types/incident-report';
import type { ChatSessionSummary } from '../types/session';

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

export const useIncidentStore = defineStore('incident', () => {
  const incidentSessionSummaries = ref<IncidentSessionSummary[]>([]);
  const activeIncidentSessionId = ref<string | null>(null);
  const activeIncidentSession = ref<IncidentSessionDetail | null>(null);
  const incidentSchema = ref<IncidentFormSchemaPayload | null>(null);
  const isIncidentGenerating = ref(false);
  const generationState = ref<'idle' | 'generating' | 'done'>('idle');
  const incidentErrorMessage = ref('');
  const incidentGenerationTraceId = ref('');
  const incidentGenerationProgress = ref<string[]>([]);

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

  const clearActiveIncidentSession = () => {
    activeIncidentSessionId.value = null;
    activeIncidentSession.value = null;
  };

  const resetGenerationState = () => {
    generationState.value = 'idle';
    incidentErrorMessage.value = '';
    incidentGenerationTraceId.value = '';
    incidentGenerationProgress.value = [];
    isIncidentGenerating.value = false;
  };

  return {
    activeIncidentSession,
    activeIncidentSessionId,
    applyIncidentDetail,
    clearActiveIncidentSession,
    generationState,
    incidentErrorMessage,
    incidentGenerationProgress,
    incidentGenerationTraceId,
    incidentSchema,
    incidentSessionSummaries,
    incidentSidebarSessions,
    isIncidentGenerating,
    mergeSummary,
    resetGenerationState,
  };
});
