<template>
  <div class="distribution-chart">
    <h3>状态分布</h3>
    <div class="distribution-bars">
      <div class="bar-item">
        <span class="bar-label">待审核</span>
        <div class="bar-track">
          <div
            class="bar-fill bar-pending"
            :style="{ width: barWidth('pending') }"
          />
        </div>
        <span class="bar-value">{{ overview?.pendingCount ?? 0 }}</span>
      </div>
      <div class="bar-item">
        <span class="bar-label">处理中</span>
        <div class="bar-track">
          <div
            class="bar-fill bar-progress"
            :style="{ width: barWidth('in_progress') }"
          />
        </div>
        <span class="bar-value">{{ overview?.inProgressCount ?? 0 }}</span>
      </div>
      <div class="bar-item">
        <span class="bar-label">已关闭</span>
        <div class="bar-track">
          <div
            class="bar-fill bar-closed"
            :style="{ width: barWidth('closed') }"
          />
        </div>
        <span class="bar-value">{{ overview?.closedThisMonth ?? 0 }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { IncidentAnalyticsOverview } from '../../../../types/incident-report/incident-report';

const props = defineProps<{
  overview: IncidentAnalyticsOverview | null;
}>();

const barWidth = (type: 'pending' | 'in_progress' | 'closed') => {
  if (!props.overview) return '0%';
  const total = props.overview.totalThisMonth || 1;
  let count = 0;
  if (type === 'pending') count = props.overview.pendingCount;
  else if (type === 'in_progress') count = props.overview.inProgressCount;
  else count = props.overview.closedThisMonth;
  return `${Math.round((count / total) * 100)}%`;
};
</script>

<style scoped>
.distribution-chart {
  padding: var(--space-xl);
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-xs);
}

.distribution-chart h3 {
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  margin: 0 0 var(--space-lg);
  color: var(--color-text-primary);
}

.distribution-bars {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.bar-item {
  display: flex;
  align-items: center;
  gap: var(--space-md);
}

.bar-label {
  width: 3.75rem;
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  flex-shrink: 0;
}

.bar-track {
  flex: 1;
  height: 1.5rem;
  background: var(--color-bg-tertiary);
  border-radius: var(--radius-sm);
  overflow: hidden;
  min-width: 0;
}

.bar-fill {
  height: 100%;
  border-radius: var(--radius-sm);
  transition: width var(--transition-smooth);
  min-width: 0;
}

.bar-pending {
  background: var(--color-primary);
}

.bar-progress {
  background: var(--color-warning);
}

.bar-closed {
  background: var(--color-success);
}

.bar-value {
  width: 2.25rem;
  text-align: right;
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
  flex-shrink: 0;
}
</style>
