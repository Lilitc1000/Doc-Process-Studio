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
  return '';
};

export const useIncidentStore = defineStore('incident', () => {
  const incidentSessionSummaries = ref<IncidentSessionSummary[]>([]);
  const activeIncidentSessionId = ref<string | null>(null);
  const activeIncidentSession = ref<IncidentSessionDetail | null>(null);
  const incidentSchema = ref<IncidentFormSchemaPayload | null>(null);
  const isIncidentGenerating = ref(false);
  const generationState = ref<'idle' | 'generating' | 'done'>('idle');
  const generationTask = ref<'none' | 'attachment' | 'quick-body' | 'section'>(
    'none',
  );
  const incidentErrorMessage = ref('');
  const incidentGenerationTraceId = ref('');
  const incidentGenerationProgress = ref<string[]>([]);
  const incidentPreviewHtml = ref('');
  const incidentPreviewPdfBase64 = ref('');
  const incidentPreviewSource = ref<'draft' | 'version' | ''>('');
  const incidentPreviewDocxBase64 = ref('');
  const incidentPreviewDocxFileName = ref('');
  const incidentPreviewLoading = ref(false);
  const incidentPreviewError = ref('');
  const incidentPreviewVersion = ref<number | null>(null);

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
    const index = incidentSessionSummaries.value.findIndex(
      (item) => item.id === summary.id,
    );
    if (index >= 0) {
      incidentSessionSummaries.value[index] = summary;
    } else {
      incidentSessionSummaries.value.push(summary);
      incidentSessionSummaries.value.sort((left, right) => {
        return (
          new Date(right.created_at).getTime() -
          new Date(left.created_at).getTime()
        );
      });
    }
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
    incidentPreviewHtml.value = '';
    incidentPreviewPdfBase64.value = '';
    incidentPreviewSource.value = '';
    incidentPreviewDocxBase64.value = '';
    incidentPreviewDocxFileName.value = '';
    incidentPreviewLoading.value = false;
    incidentPreviewError.value = '';
    incidentPreviewVersion.value = null;
  };

  const resetGenerationState = () => {
    generationState.value = 'idle';
    generationTask.value = 'none';
    incidentErrorMessage.value = '';
    incidentGenerationTraceId.value = '';
    incidentGenerationProgress.value = [];
    isIncidentGenerating.value = false;
  };

  const resetPreviewState = () => {
    incidentPreviewHtml.value = '';
    incidentPreviewPdfBase64.value = '';
    incidentPreviewSource.value = '';
    incidentPreviewDocxBase64.value = '';
    incidentPreviewDocxFileName.value = '';
    incidentPreviewLoading.value = false;
    incidentPreviewError.value = '';
    incidentPreviewVersion.value = null;
  };

  return {
    activeIncidentSession,
    activeIncidentSessionId,
    applyIncidentDetail,
    clearActiveIncidentSession,
    generationState,
    generationTask,
    incidentErrorMessage,
    incidentGenerationProgress,
    incidentGenerationTraceId,
    incidentPreviewError,
    incidentPreviewSource,
    incidentPreviewDocxBase64,
    incidentPreviewDocxFileName,
    incidentPreviewHtml,
    incidentPreviewPdfBase64,
    incidentPreviewLoading,
    incidentPreviewVersion,
    incidentSchema,
    incidentSessionSummaries,
    incidentSidebarSessions,
    isIncidentGenerating,
    mergeSummary,
    resetGenerationState,
    resetPreviewState,
  };
});
