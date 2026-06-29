import { defineStore } from 'pinia';
import { computed, ref } from 'vue';
import type {
  IncidentReportSummaryItem,
  IncidentReportDetailItem,
  IncidentAnalyticsOverview,
} from '../types/incident-report';
import {
  fetchUserIncidentRolesAndPermissions,
  fetchIncidentReportList,
  fetchIncidentReportDetail,
  fetchIncidentAnalyticsOverview,
} from '../api/incident-report';

export const useIncidentReportStore = defineStore('incident-report', () => {
  const isIncidentReportGenerating = ref(false);
  const generationState = ref<'idle' | 'generating' | 'done'>('idle');
  const generationTask = ref<'none' | 'attachment' | 'quick-body' | 'section'>(
    'none',
  );
  const userIncidentRoles = ref<string[]>([]);
  const userIncidentPermissions = ref<string[]>([]);
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

  const canCreateReport = computed(() =>
    userIncidentPermissions.value.includes('report:create'),
  );

  const canAudit = computed(() =>
    userIncidentPermissions.value.includes('report:audit'),
  );
  const canManageSettings = computed(() =>
    userIncidentPermissions.value.includes('role:manage'),
  );
  const canDeleteReport = computed(() =>
    userIncidentPermissions.value.includes('report:delete'),
  );
  const canEditAllReport = computed(() =>
    userIncidentPermissions.value.includes('report:edit_all'),
  );
  const canReopenReport = computed(() =>
    userIncidentPermissions.value.includes('report:reopen'),
  );

  const hasPermission = (permission: string) =>
    userIncidentPermissions.value.includes(permission);

  const hasAnyPermission = (...permissions: string[]) =>
    permissions.some((p) => userIncidentPermissions.value.includes(p));

  const loadUserIncidentRoles = async () => {
    const data = await fetchUserIncidentRolesAndPermissions();
    userIncidentRoles.value = data.roles ?? [];
    userIncidentPermissions.value = data.permissions ?? [];
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
  };

  return {
    isIncidentReportGenerating,
    generationState,
    generationTask,
    userIncidentRoles,
    userIncidentPermissions,
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
    canCreateReport,
    canAudit,
    canManageSettings,
    canDeleteReport,
    canEditAllReport,
    canReopenReport,
    hasPermission,
    hasAnyPermission,
    loadUserIncidentRoles,
    loadReportList,
    loadActiveReport,
    loadAnalyticsOverview,
    resetGenerationState,
  };
});
