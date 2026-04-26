<template>
  <div class="stats-cards">
    <div class="stat-card">
      <div class="stat-value">{{ overview?.total_this_month ?? 0 }}</div>
      <div class="stat-label">本月报告总数</div>
    </div>
    <div class="stat-card">
      <div class="stat-value stat-pending">{{ overview?.pending_count ?? 0 }}</div>
      <div class="stat-label">待审核</div>
    </div>
    <div class="stat-card">
      <div class="stat-value stat-progress">{{ overview?.in_progress_count ?? 0 }}</div>
      <div class="stat-label">处理中</div>
    </div>
    <div class="stat-card">
      <div class="stat-value stat-closed">{{ overview?.closed_this_month ?? 0 }}</div>
      <div class="stat-label">已关闭</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">{{ overview?.avg_resolution_hours?.toFixed(1) ?? '-' }}h</div>
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
.stats-cards {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.stat-card {
  flex: 1;
  min-width: 140px;
  padding: 20px;
  background: var(--color-bg-secondary);
  border-radius: 8px;
  text-align: center;
}

.stat-value {
  font-size: 32px;
  font-weight: 700;
  color: var(--color-text-primary);
}

.stat-pending { color: var(--color-primary); }
.stat-progress { color: var(--color-warning); }
.stat-closed { color: var(--color-success); }

.stat-label {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin-top: 4px;
}
</style>
