<template>
  <div class="stats-cards">
    <div class="stat-card">
      <div class="stat-value">{{ overview?.totalThisMonth ?? 0 }}</div>
      <div class="stat-label">本月报告总数</div>
    </div>
    <div class="stat-card">
      <div class="stat-value stat-pending">
        {{ overview?.pendingCount ?? 0 }}
      </div>
      <div class="stat-label">待审核</div>
    </div>
    <div class="stat-card">
      <div class="stat-value stat-progress">
        {{ overview?.inProgressCount ?? 0 }}
      </div>
      <div class="stat-label">处理中</div>
    </div>
    <div class="stat-card">
      <div class="stat-value stat-closed">
        {{ overview?.closedThisMonth ?? 0 }}
      </div>
      <div class="stat-label">已关闭</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">
        {{ overview?.avgResolutionHours?.toFixed(1) ?? '-' }}h
      </div>
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
  gap: var(--space-lg);
  flex-wrap: wrap;
}

.stat-card {
  flex: 1;
  min-width: 140px;
  padding: var(--space-xl);
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  text-align: center;
  box-shadow: var(--shadow-xs);
  transition:
    border-color var(--transition-smooth),
    box-shadow var(--transition-smooth),
    transform var(--transition-smooth);
}

.stat-card:hover {
  border-color: var(--color-primary-lighter);
  box-shadow: var(--shadow-sm);
  transform: translateY(-1px);
}

.stat-value {
  font-size: var(--text-3xl);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
  line-height: var(--leading-tight);
  font-variant-numeric: tabular-nums;
}

.stat-pending {
  color: var(--color-primary);
}
.stat-progress {
  color: var(--color-warning);
}
.stat-closed {
  color: var(--color-success);
}

.stat-label {
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
  margin-top: var(--space-xs);
}
</style>
