<template>
  <div class="report-detail-content">
    <div class="content-card">
      <h3>报告正文</h3>
      <div
        v-if="report.formData && Object.keys(report.formData).length > 0"
        class="form-data-section"
      >
        <div
          v-for="(value, key) in report.formData"
          :key="key"
          class="form-data-row"
        >
          <span class="form-data-key">{{ key }}</span>
          <span class="form-data-value">{{ formatValue(value) }}</span>
        </div>
      </div>
      <div v-else class="content-empty">暂无报告内容</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { IncidentReportDetailItem } from '../../../../types/incident-report/incident-report';

defineProps<{
  report: IncidentReportDetailItem;
}>();

const formatValue = (value: unknown): string => {
  if (value === null || value === undefined) return '-';
  if (typeof value === 'object') return JSON.stringify(value, null, 2);
  return String(value);
};
</script>

<style scoped>
.report-detail-content {
  flex: 1;
  min-width: 0;
}

.content-card {
  padding: 20px;
  background: var(--color-bg-secondary);
  border-radius: 8px;
}

.content-card h3 {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 16px;
  color: var(--color-text-primary);
}

.form-data-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-data-row {
  display: flex;
  gap: 12px;
  padding: 6px 0;
  border-bottom: 1px solid var(--color-border);
}

.form-data-key {
  width: 160px;
  flex-shrink: 0;
  font-size: 13px;
  color: var(--color-text-secondary);
  font-weight: 500;
}

.form-data-value {
  flex: 1;
  font-size: 13px;
  color: var(--color-text-primary);
  white-space: pre-wrap;
  word-break: break-word;
}

.content-empty {
  text-align: center;
  padding: 24px;
  color: var(--color-text-tertiary);
}
</style>
