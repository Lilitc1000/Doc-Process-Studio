import { defineStore } from 'pinia';
import { computed, ref } from 'vue';
import type {
  IncidentReportFormSchemaPayload,
  IncidentReportSummaryItem,
  IncidentReportDetailItem,
  IncidentAnalyticsOverview,
} from '../types/incident-report/incident-report';
import {
  fetchUserIncidentRoles,
  fetchIncidentReportList,
  fetchIncidentReportDetail,
  fetchIncidentAnalyticsOverview,
} from '../api/incident-report';

export const useIncidentReportStore = defineStore('incident-report', () => {
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

  const userIncidentRoles = ref<string[]>([]);
  const reportList = ref<IncidentReportSummaryItem[]>([]);
  const reportListTotal = ref(0);
  const reportListPage = ref(1);
  const reportListPageSize = ref(20);
  const reportListLoading = ref(false);
  const activeReport = ref<IncidentReportDetailItem | null>(null);
  const analyticsOverview = ref<IncidentAnalyticsOverview | null>(null);

  const isAdmin = computed(() => userIncidentRoles.value.includes('admin'));
  const isVerifier = computed(() =>
    userIncidentRoles.value.includes('verifier'),
  );
  const isHandler = computed(() => userIncidentRoles.value.includes('handler'));
  const isReporter = computed(() =>
    userIncidentRoles.value.includes('reporter'),
  );
  const isViewer = computed(
    () =>
      userIncidentRoles.value.length === 0 ||
      userIncidentRoles.value.includes('viewer'),
  );

  const canCreateReport = computed(() =>
    userIncidentRoles.value.some((r) =>
      ['reporter', 'handler', 'verifier', 'admin'].includes(r),
    ),
  );

  const canAudit = computed(() => isVerifier.value || isAdmin.value);
  const canManageSettings = computed(() => isAdmin.value);

  const loadUserIncidentRoles = async () => {
    userIncidentRoles.value = await fetchUserIncidentRoles();
  };

  const loadReportList = async (params?: {
    page?: number;
    pageSize?: number;
    status?: string;
    severity?: string;
    search?: string;
    startDate?: string;
    endDate?: string;
  }) => {
    reportListLoading.value = true;
    try {
      const response = await fetchIncidentReportList({
        page: params?.page ?? reportListPage.value,
        pageSize: params?.pageSize ?? reportListPageSize.value,
        status: params?.status,
        severity: params?.severity,
        search: params?.search,
        startDate: params?.startDate,
        endDate: params?.endDate,
      });
      reportList.value = response.items;
      reportListTotal.value = response.total;
      if (params?.page) reportListPage.value = params.page;
      if (params?.pageSize) reportListPageSize.value = params.pageSize;
    } finally {
      reportListLoading.value = false;
    }
  };

  const loadActiveReport = async (reportId: string) => {
    activeReport.value = await fetchIncidentReportDetail(reportId);
  };

  const loadAnalyticsOverview = async () => {
    analyticsOverview.value = await fetchIncidentAnalyticsOverview();
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
    userIncidentRoles,
    reportList,
    reportListTotal,
    reportListPage,
    reportListPageSize,
    reportListLoading,
    activeReport,
    analyticsOverview,
    isAdmin,
    isVerifier,
    isHandler,
    isReporter,
    isViewer,
    canCreateReport,
    canAudit,
    canManageSettings,
    loadUserIncidentRoles,
    loadReportList,
    loadActiveReport,
    loadAnalyticsOverview,
    resetGenerationState,
    resetPreviewState,
  };
});
