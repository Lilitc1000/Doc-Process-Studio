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
          返回详情
        </base-button>
        <h1>审核报告 - {{ report.refNo }}</h1>
      </div>

      <div class="audit-body">
        <div class="audit-report-preview">
          <report-status-badge :status="report.status" />
          <h2>{{ report.title }}</h2>
          <div class="audit-meta">
            <span>报告人: {{ report.reporterName ?? report.reporterId }}</span>
            <span>级别: {{ report.severity ?? '-' }}</span>
            <span>系统: {{ report.system ?? '-' }}</span>
          </div>
          <div
            v-if="report.formData && Object.keys(report.formData).length > 0"
            class="audit-form-data"
          >
            <div
              v-for="(value, key) in report.formData"
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
                <svg
                  viewBox="0 0 20 20"
                  width="14"
                  height="14"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                >
                  <path d="M5 5L15 15M15 5L5 15" />
                </svg>
                驳回
              </base-button>
              <base-button
                variant="primary"
                :disabled="!comment.trim() || processing"
                @click="handleApprove"
              >
                <svg
                  viewBox="0 0 20 20"
                  width="14"
                  height="14"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <path d="M4 10.5L8 14.5L16 5.5" />
                </svg>
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
import { useReportAudit } from './composables/useReportAudit';
import BaseButton from '../../../components/base/BaseButton.vue';
import BaseTextarea from '../../../components/base/BaseTextarea.vue';
import ReportStatusBadge from '../components/ReportStatusBadge.vue';

const route = useRoute();
const router = useRouter();

const { report, loading, processing, load, approve, reject } = useReportAudit();
const comment = ref('');

const formatValue = (value: unknown): string => {
  if (value === null || value === undefined) return '-';
  if (typeof value === 'object') return JSON.stringify(value, null, 2);
  return String(value);
};

const handleApprove = async () => {
  if (!report.value || !comment.value.trim()) return;
  if (!confirm('确定通过此报告吗？')) return;
  const reportId = route.params.id as string;
  await approve(reportId, comment.value);
  router.push(`/incident-report/${reportId}`);
};

const handleReject = async () => {
  if (!report.value || !comment.value.trim()) return;
  if (!confirm('确定驳回此报告吗？')) return;
  const reportId = route.params.id as string;
  await reject(reportId, comment.value);
  router.push(`/incident-report/${reportId}`);
};

onMounted(() => {
  load(route.params.id as string);
});
</script>

<style scoped src="./styles/incident-report-audit.css"></style>
