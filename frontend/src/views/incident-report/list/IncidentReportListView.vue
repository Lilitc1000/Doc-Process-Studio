<template>
  <div class="incident-report-list-view">
    <div class="incident-report-list-header">
      <h1 class="incident-report-list-title">事故报告管理</h1>
      <base-button
        v-if="store.canCreateReport"
        variant="primary"
        class="btn-create-report"
        @click="router.push('/incident-report/create')"
      >
        + 新建报告
      </base-button>
    </div>

    <div class="incident-report-list-body">
      <div class="incident-report-list-sidebar">
        <report-list-stats :overview="store.analyticsOverview" />
      </div>

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
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { useIncidentReportStore } from '../../../stores/incident-report';
import { deleteIncidentReport } from '../../../api/incident-report';
import BaseButton from '../../../components/base/BaseButton.vue';
import ReportListStats from './components/ReportListStats.vue';
import ReportListFilters from './components/ReportListFilters.vue';
import ReportListTable from './components/ReportListTable.vue';

const router = useRouter();
const store = useIncidentReportStore();

const filterStatus = ref('');
const filterSeverity = ref('');
const filterSearch = ref('');

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

const handleDelete = async (reportId: string) => {
  if (!confirm('确定要删除此报告吗？')) return;
  await deleteIncidentReport(reportId);
  store.loadReportList({ page: store.reportListPage });
};

onMounted(async () => {
  await Promise.all([
    store.loadUserIncidentRoles(),
    store.loadReportList({ page: 1 }),
    store.loadAnalyticsOverview(),
  ]);
});
</script>

<style scoped src="./styles/incident-report-list.css"></style>
<style src="../styles/incident-report-mobile.css"></style>
