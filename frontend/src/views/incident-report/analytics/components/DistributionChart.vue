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
  padding: 20px;
  background: var(--color-bg-secondary, #f8fafc);
  border-radius: 8px;
}

.distribution-chart h3 {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 16px;
}

.distribution-bars {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.bar-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.bar-label {
  width: 60px;
  font-size: 13px;
  color: var(--color-text-secondary, #64748b);
  flex-shrink: 0;
}

.bar-track {
  flex: 1;
  height: 24px;
  background: var(--color-bg-tertiary, #e2e8f0);
  border-radius: 4px;
  overflow: hidden;
  min-width: 0;
}

.bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s ease;
  min-width: 0;
}

.bar-pending {
  background: #3b82f6;
}

.bar-progress {
  background: #f59e0b;
}

.bar-closed {
  background: #22c55e;
}

.bar-value {
  width: 36px;
  text-align: right;
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary, #0f172a);
  flex-shrink: 0;
}
</style>
