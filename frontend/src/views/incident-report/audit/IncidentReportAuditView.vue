<template>
  <div class="incident-report-audit-view">
    <div v-if="loading" class="audit-loading">加载中...</div>
    <div v-else-if="!report" class="audit-empty">报告不存在</div>
    <template v-else>
      <div class="audit-header">
        <base-button
          variant="ghost"
          size="sm"
          @click="router.push(`/incident-report/${report.id}`)"
        >
          ← 返回详情
        </base-button>
        <h1>审核报告 - {{ report.ref_no }}</h1>
      </div>

      <div class="audit-body">
        <div class="audit-report-preview">
          <report-status-badge :status="report.status" />
          <h2>{{ report.title }}</h2>
          <div class="audit-meta">
            <span
              >报告人: {{ report.reporter_name ?? report.reporter_id }}</span
            >
            <span>级别: {{ report.severity ?? '-' }}</span>
            <span>系统: {{ report.system ?? '-' }}</span>
          </div>
          <div
            v-if="report.form_data && Object.keys(report.form_data).length > 0"
            class="audit-form-data"
          >
            <div
              v-for="(value, key) in report.form_data"
              :key="key"
              class="audit-data-row"
            >
              <span class="audit-data-key">{{ key }}</span>
              <span class="audit-data-value">{{ formatValue(value) }}</span>
            </div>
          </div>
        </div>

        <div class="audit-action-panel">
          <h3>审核操作</h3>
          <div class="audit-form">
            <div class="form-group">
              <label class="form-label">审核意见 *</label>
              <base-textarea
                v-model="comment"
                placeholder="请输入审核意见..."
              />
            </div>
            <div class="audit-buttons">
              <base-button
                variant="danger"
                :disabled="!comment.trim() || processing"
                @click="handleReject"
              >
                驳回
              </base-button>
              <base-button
                variant="primary"
                :disabled="!comment.trim() || processing"
                @click="handleApprove"
              >
                通过
              </base-button>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import {
  fetchIncidentReportDetail,
  approveIncidentReport,
  rejectIncidentReport,
} from '../../../api/incident-report';
import type { IncidentReportDetailItem } from '../../../types/incident-report/incident-report';
import BaseButton from '../../../components/base/BaseButton.vue';
import BaseTextarea from '../../../components/base/BaseTextarea.vue';
import ReportStatusBadge from '../components/ReportStatusBadge.vue';

const route = useRoute();
const router = useRouter();

const report = ref<IncidentReportDetailItem | null>(null);
const loading = ref(true);
const processing = ref(false);
const comment = ref('');

const formatValue = (value: unknown): string => {
  if (value === null || value === undefined) return '-';
  if (typeof value === 'object') return JSON.stringify(value, null, 2);
  return String(value);
};

const handleApprove = async () => {
  if (!report.value || !comment.value.trim()) return;
  if (!confirm('确定通过此报告吗？')) return;
  processing.value = true;
  try {
    await approveIncidentReport(report.value.id, comment.value);
    router.push(`/incident-report/${report.value.id}`);
  } finally {
    processing.value = false;
  }
};

const handleReject = async () => {
  if (!report.value || !comment.value.trim()) return;
  if (!confirm('确定驳回此报告吗？')) return;
  processing.value = true;
  try {
    await rejectIncidentReport(report.value.id, comment.value);
    router.push(`/incident-report/${report.value.id}`);
  } finally {
    processing.value = false;
  }
};

onMounted(async () => {
  const reportId = route.params.id as string;
  try {
    report.value = await fetchIncidentReportDetail(reportId);
  } finally {
    loading.value = false;
  }
});
</script>

<style scoped src="./styles/incident-report-audit.css"></style>
