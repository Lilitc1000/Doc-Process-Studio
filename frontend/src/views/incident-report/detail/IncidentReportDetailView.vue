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
            ← 返回列表
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
            {{ downloadingDocx ? '生成中...' : '下载 Word' }}
          </base-button>
          <base-button
            v-if="canEdit"
            variant="secondary"
            size="sm"
            @click="router.push(`/incident-report/${report.id}/edit`)"
          >
            编辑
          </base-button>
          <base-button
            v-if="canAudit"
            variant="primary"
            size="sm"
            @click="router.push(`/incident-report/${report.id}/audit`)"
          >
            审核
          </base-button>
          <base-button
            v-if="canClose"
            variant="danger"
            size="sm"
            @click="handleClose"
          >
            关闭
          </base-button>
          <base-button
            v-if="canReopen"
            variant="secondary"
            size="sm"
            @click="handleReopen"
          >
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
              <span class="info-value">{{ formatDate(report.faultDate) }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">创建时间</span>
              <span class="info-value">{{ formatDate(report.createdAt) }}</span>
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
import {
  fetchIncidentReportDetail,
  fetchIncidentReportAuditLogs,
  fetchIncidentReportComments,
  createIncidentReportComment,
  closeIncidentReport,
  reopenIncidentReport,
  previewIncidentReport,
} from '../../../api/incident-report';
import type {
  IncidentReportDetailItem,
  IncidentAuditLogEntry,
  IncidentCommentEntry,
} from '../../../types/incident-report/incident-report';
import BaseButton from '../../../components/base/BaseButton.vue';
import ReportStatusBadge from '../components/ReportStatusBadge.vue';
import ReportAuditTimeline from './components/ReportAuditTimeline.vue';
import ReportDetailContent from './components/ReportDetailContent.vue';
import ReportComments from './components/ReportComments.vue';

const route = useRoute();
const router = useRouter();
const store = useIncidentReportStore();
const authStore = useAuthStore();

const report = ref<IncidentReportDetailItem | null>(null);
const auditLogs = ref<IncidentAuditLogEntry[]>([]);
const comments = ref<IncidentCommentEntry[]>([]);
const loading = ref(true);
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
    store.hasPermission('report:delete')
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

const formatDate = (dateStr: string | null) => {
  if (!dateStr) return '-';
  try {
    return new Date(dateStr).toLocaleString('zh-CN');
  } catch {
    return dateStr;
  }
};

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
  try {
    await store.loadUserIncidentRoles();
    const [reportData, logs, commentData] = await Promise.all([
      fetchIncidentReportDetail(reportId),
      fetchIncidentReportAuditLogs(reportId),
      fetchIncidentReportComments(reportId),
    ]);
    report.value = reportData;
    auditLogs.value = logs;
    comments.value = commentData;
  } finally {
    loading.value = false;
  }
});
</script>

<style scoped src="./styles/incident-report-detail.css"></style>
