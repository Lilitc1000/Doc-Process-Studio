<template>
  <div class="trend-chart">
    <h3>趋势图</h3>
    <div v-if="loading" class="trend-loading">加载中...</div>
    <div v-else-if="trendData.length === 0" class="trend-empty">暂无数据</div>
    <div v-else class="trend-bars">
      <div v-for="item in trendData" :key="item.date" class="trend-bar-item">
        <div
          class="trend-bar-fill"
          :style="{ height: barHeight(item.count) }"
          :title="`${item.date}: ${item.count}`"
        />
        <span class="trend-bar-label">{{ formatLabel(item.date) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { IncidentAnalyticsTrend } from '../../../../types/incident-report/incident-report';

const props = defineProps<{
  trendData: IncidentAnalyticsTrend[];
  loading: boolean;
}>();

const barHeight = (count: number) => {
  const maxCount = Math.max(...props.trendData.map((d) => d.count), 1);
  return `${Math.round((count / maxCount) * 100)}%`;
};

const formatLabel = (date: string) => {
  try {
    return new Date(date).toLocaleDateString('zh-CN', {
      month: 'numeric',
      day: 'numeric',
    });
  } catch {
    return date;
  }
};
</script>

<style scoped>
.trend-chart {
  padding: 20px;
  background: var(--color-bg-secondary);
  border-radius: 8px;
}

.trend-chart h3 {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 16px;
}

.trend-loading,
.trend-empty {
  text-align: center;
  padding: 24px;
  color: var(--color-text-tertiary);
}

.trend-bars {
  display: flex;
  align-items: flex-end;
  gap: 4px;
  height: 200px;
  padding-top: 8px;
}

.trend-bar-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  height: 100%;
  justify-content: flex-end;
}

.trend-bar-fill {
  width: 100%;
  max-width: 24px;
  background: var(--color-primary);
  border-radius: 2px 2px 0 0;
  min-height: 2px;
  transition: height 0.3s ease;
}

.trend-bar-label {
  font-size: 10px;
  color: var(--color-text-tertiary);
  margin-top: 4px;
  writing-mode: vertical-rl;
  text-orientation: mixed;
}
</style>
