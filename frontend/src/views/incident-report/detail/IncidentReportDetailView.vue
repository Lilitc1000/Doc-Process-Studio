<template>
  <div class="incident-report-detail-view">
    <div v-if="loading" class="detail-loading">加载中...</div>
    <div v-else-if="!report" class="detail-empty">报告不存在</div>
    <template v-else>
      <div class="detail-header">
        <div class="detail-header-left">
          <base-button
            variant="ghost"
            size="sm"
            @click="router.push('/incident-report')"
          >
            <svg
              viewBox="0 0 20 20"
              width="16"
              height="16"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M12.5 15L7.5 10L12.5 5" />
            </svg>
            返回列表
          </base-button>
          <span class="detail-ref">{{ report.refNo }}</span>
          <span class="detail-title">{{ report.title }}</span>
        </div>
        <div class="detail-header-right">
          <base-button
            variant="ghost"
            size="sm"
            :disabled="downloadingDocx"
            @click="handleDownloadDocx"
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
              <path d="M10 3V13M10 13L6.5 9.5M10 13L13.5 9.5M3 16H17" />
            </svg>
            {{ downloadingDocx ? '生成中...' : '下载 Word' }}
          </base-button>
          <base-button
            v-if="canEdit"
            variant="secondary"
            size="sm"
            @click="router.push(`/incident-report/${report.id}/edit`)"
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
              <path d="M13.5 3.5L16.5 6.5L7 16H4V13L13.5 3.5z" />
            </svg>
            编辑
          </base-button>
          <base-button
            v-if="canAudit"
            variant="primary"
            size="sm"
            @click="router.push(`/incident-report/${report.id}/audit`)"
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
              <path d="M10 4C5 4 2 10 2 10s3 6 8 6 8-6 8-6-3-6-8-6z" />
              <circle cx="10" cy="10" r="2.5" />
            </svg>
            审核
          </base-button>
          <base-button
            v-if="canClose"
            variant="danger"
            size="sm"
            @click="handleClose"
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
              <rect x="3" y="3" width="14" height="14" rx="2" />
              <path d="M3 7H17M7 3V7" />
            </svg>
            关闭
          </base-button>
          <base-button
            v-if="canReopen"
            variant="secondary"
            size="sm"
            @click="handleReopen"
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
                d="M2.5 10A7.5 7.5 0 0 1 15 5.5M17.5 10A7.5 7.5 0 0 1 5 14.5"
              />
              <path d="M15 2V5.5H11.5M5 18V14.5H8.5" />
            </svg>
            重新打开
          </base-button>
        </div>
      </div>

      <div class="detail-body">
        <div class="detail-sidebar">
          <div class="detail-info-card">
            <h3>基本信息</h3>
            <div class="info-row">
              <span class="info-label">状态</span>
              <report-status-badge :status="report.status" />
            </div>
            <div class="info-row">
              <span class="info-label">级别</span>
              <span class="info-value">{{ report.severity ?? '-' }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">报告人</span>
              <span class="info-value">{{
                report.reporterName ?? report.reporterId
              }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">处理人</span>
              <span class="info-value">{{
                report.assigneeName ?? report.assigneeId ?? '-'
              }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">审核人</span>
              <span class="info-value">{{
                report.verifierName ?? report.verifierId ?? '-'
              }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">系统</span>
              <span class="info-value">{{ report.system ?? '-' }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">站点</span>
              <span class="info-value">{{ report.siteId ?? '-' }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">故障日期</span>
              <span class="info-value">{{
                formatDateTime(report.faultDate)
              }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">创建时间</span>
              <span class="info-value">{{
                formatDateTime(report.createdAt)
              }}</span>
            </div>
          </div>

          <report-audit-timeline :audit-logs="auditLogs" />
        </div>

        <div class="detail-content">
          <report-detail-content :report="report" />
          <report-comments
            :report-id="report.id"
            :comments="comments"
            @add-comment="handleAddComment"
          />
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useIncidentReportStore } from '../../../stores/incident-report';
import { useAuthStore } from '../../../stores/auth';
import { useReportDetail } from './composables/useReportDetail';
import {
  fetchIncidentReportComments,
  createIncidentReportComment,
  closeIncidentReport,
  reopenIncidentReport,
  previewIncidentReport,
} from '../../../api/incident-report';
import type { IncidentCommentEntry } from '../../../types/incident-report/incident-report';
import BaseButton from '../../../components/base/BaseButton.vue';
import ReportStatusBadge from '../components/ReportStatusBadge.vue';
import ReportAuditTimeline from './components/ReportAuditTimeline.vue';
import ReportDetailContent from './components/ReportDetailContent.vue';
import ReportComments from './components/ReportComments.vue';
import { formatDateTime } from '../../../utils/common/date';

const route = useRoute();
const router = useRouter();
const store = useIncidentReportStore();
const authStore = useAuthStore();

const { report, auditLogs, loading, load: loadDetail } = useReportDetail();
const comments = ref<IncidentCommentEntry[]>([]);
const downloadingDocx = ref(false);

const canEdit = computed(() => {
  if (!report.value) return false;
  const s = report.value.status;
  if (s !== 'draft' && s !== 'rejected') return false;
  if (
    report.value.reporterId === authStore.userId &&
    store.hasPermission('report:edit_own')
  )
    return true;
  return (
    store.hasPermission('report:edit_assigned') ||
    store.hasPermission('report:edit_all')
  );
});

const canAudit = computed(() => {
  if (!report.value) return false;
  return report.value.status === 'pending' && store.canAudit;
});

const canClose = computed(() => {
  if (!report.value) return false;
  return (
    report.value.status === 'in_progress' &&
    store.hasPermission('report:close_assigned')
  );
});

const canReopen = computed(() => {
  if (!report.value) return false;
  return report.value.status === 'closed' && store.canReopenReport;
});

const handleClose = async () => {
  if (!report.value || !confirm('确定要关闭此报告吗？')) return;
  report.value = await closeIncidentReport(report.value.id);
};

const handleReopen = async () => {
  if (!report.value || !confirm('确定要重新打开此报告吗？')) return;
  report.value = await reopenIncidentReport(report.value.id);
};

const handleAddComment = async (content: string) => {
  if (!report.value) return;
  const comment = await createIncidentReportComment(report.value.id, {
    content,
  });
  comments.value.push(comment);
};

const handleDownloadDocx = async () => {
  if (!report.value || downloadingDocx.value) return;
  downloadingDocx.value = true;
  try {
    const preview = await previewIncidentReport(report.value.id, {});
    if (!preview.docxBase64 || !preview.docxFileName) return;
    const binaryString = atob(preview.docxBase64);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    const blob = new Blob([bytes], {
      type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = preview.docxFileName;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  } finally {
    downloadingDocx.value = false;
  }
};

onMounted(async () => {
  const reportId = route.params.id as string;
  await store.loadUserIncidentRoles();
  try {
    const [commentData] = await Promise.all([
      fetchIncidentReportComments(reportId),
      loadDetail(reportId),
    ]);
    comments.value = commentData;
  } catch {
    // loadDetail sets report to null on failure, UI shows "报告不存在"
  }
});
</script>

<style scoped src="./styles/incident-report-detail.css"></style>
