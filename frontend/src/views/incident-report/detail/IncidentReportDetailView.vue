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
          <span class="detail-ref">{{ report.ref_no }}</span>
          <span class="detail-title">{{ report.title }}</span>
        </div>
        <div class="detail-header-right">
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
                report.reporter_name ?? report.reporter_id
              }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">处理人</span>
              <span class="info-value">{{
                report.assignee_name ?? report.assignee_id ?? '-'
              }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">审核人</span>
              <span class="info-value">{{
                report.verifier_name ?? report.verifier_id ?? '-'
              }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">系统</span>
              <span class="info-value">{{ report.system ?? '-' }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">站点</span>
              <span class="info-value">{{ report.site_id ?? '-' }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">故障日期</span>
              <span class="info-value">{{
                formatDate(report.fault_date)
              }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">创建时间</span>
              <span class="info-value">{{
                formatDate(report.created_at)
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
import {
  fetchIncidentReportDetail,
  fetchIncidentReportAuditLogs,
  fetchIncidentReportComments,
  createIncidentReportComment,
  closeIncidentReport,
  reopenIncidentReport,
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

const report = ref<IncidentReportDetailItem | null>(null);
const auditLogs = ref<IncidentAuditLogEntry[]>([]);
const comments = ref<IncidentCommentEntry[]>([]);
const loading = ref(true);

const canEdit = computed(() => {
  if (!report.value) return false;
  const s = report.value.status;
  if (s !== 'draft' && s !== 'rejected') return false;
  return store.isReporter || store.isAdmin;
});

const canAudit = computed(() => {
  if (!report.value) return false;
  return report.value.status === 'pending' && store.canAudit;
});

const canClose = computed(() => {
  if (!report.value) return false;
  return (
    report.value.status === 'in_progress' && (store.isHandler || store.isAdmin)
  );
});

const canReopen = computed(() => {
  if (!report.value) return false;
  return report.value.status === 'closed' && store.isAdmin;
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
