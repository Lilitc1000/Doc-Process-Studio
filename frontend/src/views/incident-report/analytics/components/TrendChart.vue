<template>
  <div class="trend-chart">
    <h3>趋势图（近 7 天）</h3>
    <div v-if="loading" class="trend-loading">加载中...</div>
    <div v-else-if="filledData.length === 0" class="trend-empty">暂无数据</div>
    <div v-else class="trend-container">
      <div class="trend-y-axis">
        <span class="y-label">{{ maxCount }}</span>
        <span class="y-label">{{ Math.round(maxCount / 2) }}</span>
        <span class="y-label">0</span>
      </div>
      <div class="trend-bars">
        <div v-for="item in filledData" :key="item.date" class="trend-bar-item">
          <div class="trend-bar-track">
            <div
              class="trend-bar-fill"
              :style="{ height: barHeight(item.count) }"
            />
          </div>
          <span v-if="item.count > 0" class="trend-bar-count">{{
            item.count
          }}</span>
          <span class="trend-bar-label">{{ formatLabel(item.date) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { IncidentAnalyticsTrend } from '../../../../types/incident-report/incident-report';

const props = defineProps<{
  trendData: IncidentAnalyticsTrend[];
  loading: boolean;
}>();

const maxCount = computed(() => {
  const m = Math.max(...props.trendData.map((d) => d.count), 0);
  return m || 1;
});

const filledData = computed(() => {
  const result: { date: string; count: number }[] = [];
  const dataMap = new Map(props.trendData.map((d) => [d.date, d.count]));
  const today = new Date();
  for (let i = 6; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(d.getDate() - i);
    const dateStr = d.toISOString().slice(0, 10);
    result.push({ date: dateStr, count: dataMap.get(dateStr) ?? 0 });
  }
  return result;
});

const barHeight = (count: number) => {
  return `${Math.round((count / maxCount.value) * 100)}%`;
};

const formatLabel = (date: string) => {
  try {
    const d = new Date(date + 'T00:00:00');
    return `${d.getMonth() + 1}/${d.getDate()}`;
  } catch {
    return date;
  }
};
</script>

<style scoped>
.trend-chart {
  padding: 20px;
  background: var(--color-bg-secondary, #f8fafc);
  border-radius: 8px;
}

.trend-chart h3 {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 16px;
}

.trend-loading,
.trend-empty {
  text-align: center;
  padding: 24px;
  color: var(--color-text-tertiary, #94a3b8);
}

.trend-container {
  display: flex;
  gap: 8px;
}

.trend-y-axis {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 0 0 24px;
  height: 180px;
  flex-shrink: 0;
}

.y-label {
  font-size: 11px;
  color: var(--color-text-tertiary, #94a3b8);
  text-align: right;
  width: 24px;
}

.trend-bars {
  flex: 1;
  display: flex;
  align-items: flex-end;
  gap: 6px;
  height: 180px;
  padding-top: 8px;
}

.trend-bar-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  height: 100%;
  position: relative;
}

.trend-bar-track {
  flex: 1;
  width: 100%;
  display: flex;
  align-items: flex-end;
  justify-content: center;
}

.trend-bar-fill {
  width: 100%;
  max-width: 28px;
  background: #3b82f6;
  border-radius: 3px 3px 0 0;
  min-height: 0;
  transition: height 0.3s ease;
}

.trend-bar-count {
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-primary, #0f172a);
  margin-bottom: 2px;
  position: absolute;
  top: 0;
}

.trend-bar-label {
  font-size: 11px;
  color: var(--color-text-tertiary, #94a3b8);
  margin-top: 4px;
  flex-shrink: 0;
  white-space: nowrap;
}
</style>
