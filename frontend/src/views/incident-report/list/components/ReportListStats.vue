<template>
  <div class="report-list-stats">
    <div class="stat-card">
      <div class="stat-value">{{ overview?.total_this_month ?? 0 }}</div>
      <div class="stat-label">本月报告</div>
    </div>
    <div class="stat-card">
      <div class="stat-value stat-pending">{{ overview?.pending_count ?? 0 }}</div>
      <div class="stat-label">待处理</div>
    </div>
    <div class="stat-card">
      <div class="stat-value stat-progress">{{ overview?.in_progress_count ?? 0 }}</div>
      <div class="stat-label">处理中</div>
    </div>
    <div class="stat-card">
      <div class="stat-value stat-closed">{{ overview?.closed_this_month ?? 0 }}</div>
      <div class="stat-label">已关闭</div>
    </div>
    <div v-if="overview?.avg_resolution_hours != null" class="stat-card">
      <div class="stat-value">{{ overview.avg_resolution_hours }}h</div>
      <div class="stat-label">平均处理时长</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { IncidentAnalyticsOverview } from '../../../../types/incident-report/incident-report';

defineProps<{
  overview: IncidentAnalyticsOverview | null;
}>();
</script>

<style scoped>
.report-list-stats {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.stat-card {
  padding: 12px 16px;
  border-radius: 8px;
  background: var(--color-bg-secondary);
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.stat-pending {
  color: var(--color-primary);
}

.stat-progress {
  color: var(--color-warning);
}

.stat-closed {
  color: var(--color-text-tertiary);
}

.stat-label {
  font-size: 12px;
  color: var(--color-text-secondary);
  margin-top: 4px;
}
</style>
