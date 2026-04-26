<template>
  <div class="incident-report-analytics-view">
    <div class="analytics-header">
      <base-button variant="ghost" size="sm" @click="router.push('/incident-report')">
        ← 返回列表
      </base-button>
      <h1>统计分析</h1>
    </div>

    <div class="analytics-body">
      <stats-cards :overview="overview" />

      <div class="analytics-charts">
        <distribution-chart
          :overview="overview"
        />
        <trend-chart
          :trend-data="trendData"
          :loading="trendLoading"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { fetchIncidentAnalyticsOverview, fetchIncidentAnalyticsTrend } from '../../../api/incident-report';
import type { IncidentAnalyticsOverview, IncidentAnalyticsTrend } from '../../../types/incident-report/incident-report';
import BaseButton from '../../../components/base/BaseButton.vue';
import StatsCards from './components/StatsCards.vue';
import DistributionChart from './components/DistributionChart.vue';
import TrendChart from './components/TrendChart.vue';

const router = useRouter();

const overview = ref<IncidentAnalyticsOverview | null>(null);
const trendData = ref<IncidentAnalyticsTrend[]>([]);
const trendLoading = ref(false);

onMounted(async () => {
  const [overviewData, trend] = await Promise.all([
    fetchIncidentAnalyticsOverview(),
    fetchIncidentAnalyticsTrend(30),
  ]);
  overview.value = overviewData;
  trendData.value = trend;
});
</script>

<style scoped src="./styles/incident-report-analytics.css"></style>
