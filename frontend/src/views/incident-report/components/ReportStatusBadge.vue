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

const label = computed(
  () => INCIDENT_STATUS_LABELS[props.status] ?? props.status,
);
</script>

<style scoped>
.status-badge {
  display: inline-flex;
  align-items: center;
  padding: var(--space-2xs) var(--space-sm);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  line-height: 1.5;
  white-space: nowrap;
}

.status-draft {
  color: var(--color-text-secondary);
  background: var(--color-bg-secondary);
}

.status-pending {
  color: var(--color-primary);
  background: var(--color-primary-light);
}

.status-approved {
  color: var(--color-success);
  background: var(--color-success-light);
}

.status-rejected {
  color: var(--color-danger);
  background: var(--color-danger-light);
}

.status-in-progress {
  color: var(--color-warning);
  background: var(--color-warning-light);
}

.status-closed {
  color: var(--color-text-tertiary);
  background: var(--color-bg-tertiary);
}
</style>
