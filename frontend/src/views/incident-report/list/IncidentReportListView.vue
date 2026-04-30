<template>
  <div class="incident-report-list-view">
    <div class="incident-report-list-header">
      <h1 class="incident-report-list-title">事故报告管理</h1>
      <div class="incident-report-list-header-actions">
        <base-button
          variant="secondary"
          @click="router.push('/incident-report/analytics')"
        >
          <svg
            viewBox="0 0 20 20"
            width="14"
            height="14"
            fill="none"
            stroke="currentColor"
            stroke-width="1.5"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <rect x="2.5" y="10.5" width="4" height="7" rx="1" />
            <rect x="8" y="5.5" width="4" height="12" rx="1" />
            <rect x="13.5" y="2.5" width="4" height="15" rx="1" />
          </svg>
          统计分析
        </base-button>
        <base-button
          v-if="store.canManageSettings"
          variant="secondary"
          @click="router.push('/incident-report/roles')"
        >
          <svg
            viewBox="0 0 20 20"
            width="14"
            height="14"
            fill="none"
            stroke="currentColor"
            stroke-width="1.5"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path
              d="M10 2a4 4 0 0 0-4 4v2H5a1 1 0 0 0-1 1v8a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1V9a1 1 0 0 0-1-1h-1V6a4 4 0 0 0-4-4zm-2 4a2 2 0 1 1 4 0v2H8V6z"
            />
          </svg>
          角色管理
        </base-button>
        <base-button
          v-if="store.canCreateReport"
          variant="primary"
          class="btn-create-report"
          @click="router.push('/incident-report/create')"
        >
          <svg
            viewBox="0 0 20 20"
            width="14"
            height="14"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
          >
            <path d="M10 4V16M4 10H16" />
          </svg>
          新建报告
        </base-button>
      </div>
    </div>

    <div class="incident-report-list-body">
      <div class="incident-report-list-main">
        <report-list-filters
          v-model:status="filterStatus"
          v-model:severity="filterSeverity"
          v-model:search="filterSearch"
          @filter-change="handleFilterChange"
        />

        <report-list-table
          :items="store.reportList"
          :loading="store.reportListLoading"
          :can-edit="store.isAdmin || store.canDeleteReport"
          :can-delete="store.isAdmin"
          @view="router.push(`/incident-report/${$event}`)"
          @edit="router.push(`/incident-report/${$event}/edit`)"
          @delete="handleDelete"
        />

        <div v-if="totalPages > 1" class="incident-report-list-pagination">
          <base-button
            variant="ghost"
            size="sm"
            :disabled="store.reportListPage <= 1"
            @click="changePage(store.reportListPage - 1)"
          >
            上一页
          </base-button>
          <span class="pagination-info">
            {{ store.reportListPage }} / {{ totalPages }}
          </span>
          <base-button
            variant="ghost"
            size="sm"
            :disabled="store.reportListPage >= totalPages"
            @click="changePage(store.reportListPage + 1)"
          >
            下一页
          </base-button>
        </div>
      </div>
    </div>

    <base-confirm-dialog
      v-model="showDeleteConfirm"
      title="删除报告"
      message="确定要删除此报告吗？此操作不可撤销。"
      confirm-text="删除"
      cancel-text="取消"
      confirm-variant="danger"
      @confirm="confirmDelete"
    />

    <floating-toast
      :visible="showSubmitToast"
      title="提交成功"
      message="事故报告已成功提交"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useIncidentReportStore } from '../../../stores/incident-report';
import { deleteIncidentReport } from '../../../api/incident-report';
import BaseButton from '../../../components/base/BaseButton.vue';
import BaseConfirmDialog from '../../../components/base/BaseConfirmDialog.vue';
import FloatingToast from '../../../components/business/FloatingToast.vue';
import ReportListFilters from './components/ReportListFilters.vue';
import ReportListTable from './components/ReportListTable.vue';

const route = useRoute();
const router = useRouter();
const store = useIncidentReportStore();

const filterStatus = ref('');
const filterSeverity = ref('');
const filterSearch = ref('');
const showDeleteConfirm = ref(false);
const pendingDeleteId = ref<string | null>(null);
const showSubmitToast = ref(false);
let refreshTimer: number | null = null;

const totalPages = computed(() =>
  Math.ceil(store.reportListTotal / store.reportListPageSize),
);

const handleFilterChange = () => {
  store.loadReportList({
    page: 1,
    status: filterStatus.value || undefined,
    severity: filterSeverity.value || undefined,
    search: filterSearch.value || undefined,
  });
};

const changePage = (page: number) => {
  store.loadReportList({
    page,
    status: filterStatus.value || undefined,
    severity: filterSeverity.value || undefined,
    search: filterSearch.value || undefined,
  });
};

const handleDelete = (reportId: string) => {
  pendingDeleteId.value = reportId;
  showDeleteConfirm.value = true;
};

const confirmDelete = async () => {
  if (!pendingDeleteId.value) return;
  await deleteIncidentReport(pendingDeleteId.value);
  pendingDeleteId.value = null;
  store.loadReportList({ page: store.reportListPage });
};

onMounted(async () => {
  await Promise.all([
    store.loadUserIncidentRoles(),
    store.loadReportList({ page: 1 }),
  ]);
  refreshTimer = window.setInterval(() => {
    store.loadReportList({ page: store.reportListPage });
  }, 30000);

  if (sessionStorage.getItem('incident_report_submitted') === '1') {
    sessionStorage.removeItem('incident_report_submitted');
    showSubmitToast.value = true;
    setTimeout(() => {
      showSubmitToast.value = false;
    }, 3000);
  }
});

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer);
    refreshTimer = null;
  }
});
</script>

<style scoped src="./styles/incident-report-list.css"></style>
<style src="../styles/incident-report-mobile.css"></style>
