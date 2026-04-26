<template>
  <div class="distribution-chart">
    <h3>状态分布</h3>
    <div class="distribution-bars">
      <div class="bar-item">
        <span class="bar-label">待审核</span>
        <div class="bar-track">
          <div class="bar-fill bar-pending" :style="{ width: barWidth('pending') }" />
        </div>
        <span class="bar-value">{{ overview?.pending_count ?? 0 }}</span>
      </div>
      <div class="bar-item">
        <span class="bar-label">处理中</span>
        <div class="bar-track">
          <div class="bar-fill bar-progress" :style="{ width: barWidth('in_progress') }" />
        </div>
        <span class="bar-value">{{ overview?.in_progress_count ?? 0 }}</span>
      </div>
      <div class="bar-item">
        <span class="bar-label">已关闭</span>
        <div class="bar-track">
          <div class="bar-fill bar-closed" :style="{ width: barWidth('closed') }" />
        </div>
        <span class="bar-value">{{ overview?.closed_this_month ?? 0 }}</span>
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
  const total = props.overview.total_this_month || 1;
  let count = 0;
  if (type === 'pending') count = props.overview.pending_count;
  else if (type === 'in_progress') count = props.overview.in_progress_count;
  else count = props.overview.closed_this_month;
  return `${Math.round((count / total) * 100)}%`;
};
</script>

<style scoped>
.distribution-chart {
  padding: 20px;
  background: var(--color-bg-secondary);
  border-radius: 8px;
}

.distribution-chart h3 {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 16px;
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
  color: var(--color-text-secondary);
}

.bar-track {
  flex: 1;
  height: 20px;
  background: var(--color-bg-tertiary, #e5e7eb);
  border-radius: 4px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s ease;
}

.bar-pending { background: var(--color-primary); }
.bar-progress { background: var(--color-warning); }
.bar-closed { background: var(--color-success); }

.bar-value {
  width: 30px;
  text-align: right;
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
}
</style>
