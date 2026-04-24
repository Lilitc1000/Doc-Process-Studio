import { defineStore } from 'pinia';
import { computed, ref } from 'vue';
import type {
  IncidentReportFormSchemaPayload,
  IncidentReportSessionDetail,
  IncidentReportSessionSummary,
} from '../types/incident-report/incident-report';

export const useIncidentReportStore = defineStore('incident-report', () => {
  const activeIncidentReportSessionId = ref<string>('');
  const activeIncidentReportSession = ref<IncidentReportSessionDetail | null>(
    null,
  );
  const incidentReportSessionSummaries = ref<IncidentReportSessionSummary[]>(
    [],
  );
  const incidentReportSchema = ref<IncidentReportFormSchemaPayload | null>(
    null,
  );
  const isIncidentReportGenerating = ref(false);
  const generationState = ref<'idle' | 'generating' | 'done'>('idle');
  const generationTask = ref<'none' | 'attachment' | 'quick-body' | 'section'>(
    'none',
  );
  const incidentReportErrorMessage = ref('');
  const incidentReportPreviewHtml = ref('');
  const incidentReportPreviewPdfBase64 = ref('');
  const incidentReportPreviewDocxBase64 = ref('');
  const incidentReportPreviewDocxFileName = ref('');
  const incidentReportPreviewLoading = ref(false);
  const incidentReportPreviewError = ref('');
  const incidentReportPreviewVersion = ref<number | null>(null);
  const incidentReportPreviewSource = ref<'draft' | 'version'>('draft');

  const incidentReportSidebarSessions = computed(() => {
    const summaries = incidentReportSessionSummaries.value;
    const activeId = activeIncidentReportSessionId.value;
    const activeSession = activeIncidentReportSession.value;
    if (!activeId || !activeSession) {
      return summaries;
    }
    const exists = summaries.some((item) => item.id === activeId);
    if (exists) {
      return summaries;
    }
    return [
      {
        id: activeSession.id,
        title: activeSession.title,
        status: activeSession.status,
        createdAt: activeSession.createdAt,
        updatedAt: activeSession.updatedAt,
      },
      ...summaries,
    ];
  });

  const clearActiveIncidentReportSession = () => {
    activeIncidentReportSessionId.value = '';
    activeIncidentReportSession.value = null;
    resetGenerationState();
    resetPreviewState();
  };

  const applyIncidentReportDetail = (detail: IncidentReportSessionDetail) => {
    activeIncidentReportSession.value = detail;
    const index = incidentReportSessionSummaries.value.findIndex(
      (item) => item.id === detail.id,
    );
    if (index >= 0) {
      incidentReportSessionSummaries.value[index] = {
        id: detail.id,
        title: detail.title,
        status: detail.status,
        createdAt: detail.createdAt,
        updatedAt: detail.updatedAt,
      };
    }
  };

  const mergeSummary = (summary: IncidentReportSessionSummary) => {
    const existing = incidentReportSessionSummaries.value.find(
      (item) => item.id === summary.id,
    );
    if (existing) {
      Object.assign(existing, summary);
    } else {
      incidentReportSessionSummaries.value.unshift(summary);
    }
  };

  const resetGenerationState = () => {
    isIncidentReportGenerating.value = false;
    generationState.value = 'idle';
    generationTask.value = 'none';
    incidentReportErrorMessage.value = '';
  };

  const resetPreviewState = () => {
    incidentReportPreviewHtml.value = '';
    incidentReportPreviewPdfBase64.value = '';
    incidentReportPreviewDocxBase64.value = '';
    incidentReportPreviewDocxFileName.value = '';
    incidentReportPreviewLoading.value = false;
    incidentReportPreviewError.value = '';
    incidentReportPreviewVersion.value = null;
    incidentReportPreviewSource.value = 'draft';
  };

  return {
    activeIncidentReportSessionId,
    activeIncidentReportSession,
    incidentReportSessionSummaries,
    incidentReportSchema,
    isIncidentReportGenerating,
    generationState,
    generationTask,
    incidentReportErrorMessage,
    incidentReportPreviewHtml,
    incidentReportPreviewPdfBase64,
    incidentReportPreviewDocxBase64,
    incidentReportPreviewDocxFileName,
    incidentReportPreviewLoading,
    incidentReportPreviewError,
    incidentReportPreviewVersion,
    incidentReportPreviewSource,
    incidentReportSidebarSessions,
    clearActiveIncidentReportSession,
    applyIncidentReportDetail,
    mergeSummary,
    resetGenerationState,
    resetPreviewState,
  };
});
