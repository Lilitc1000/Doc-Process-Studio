<template>
  <span :class="['status-badge', `status-${status.replace(/_/g, '-')}`]">
    {{ label }}
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { IncidentReportStatus } from '../../../types/incident-report/incident-report';
import { INCIDENT_STATUS_LABELS } from '../../../types/incident-report/incident-report';

const props = defineProps<{
  status: IncidentReportStatus;
}>();

const label = computed(() => INCIDENT_STATUS_LABELS[props.status] ?? props.status);
</script>

<style scoped>
.status-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  line-height: 1.5;
  white-space: nowrap;
}

.status-draft {
  color: var(--color-text-secondary);
  background: var(--color-bg-secondary);
}

.status-pending {
  color: var(--color-primary);
  background: var(--color-primary-bg, #eff6ff);
}

.status-approved {
  color: var(--color-success);
  background: var(--color-success-bg, #f0fdf4);
}

.status-rejected {
  color: var(--color-danger);
  background: var(--color-danger-bg, #fef2f2);
}

.status-in-progress {
  color: var(--color-warning);
  background: var(--color-warning-bg, #fffbeb);
}

.status-closed {
  color: var(--color-text-tertiary);
  background: var(--color-bg-tertiary, #f5f5f5);
}
</style>
