<template>
  <div class="report-detail-header">
    <div class="detail-header-left">
      <base-button variant="ghost" size="sm" @click="$emit('go-back')">
        ← 返回列表
      </base-button>
      <span class="detail-ref">{{ report.ref_no }}</span>
      <span class="detail-title">{{ report.title }}</span>
    </div>
    <div class="detail-header-right">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup lang="ts">
import type { IncidentReportDetailItem } from '../../../../types/incident-report/incident-report';
import BaseButton from '../../../../components/base/BaseButton.vue';

defineProps<{
  report: IncidentReportDetailItem;
}>();

defineEmits<{
  (e: 'go-back'): void;
}>();
</script>

<style scoped>
.report-detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  gap: 12px;
  flex-wrap: wrap;
}

.detail-header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.detail-ref {
  font-family: monospace;
  font-size: 14px;
  color: var(--color-text-secondary);
}

.detail-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.detail-header-right {
  display: flex;
  gap: 8px;
}
</style>
