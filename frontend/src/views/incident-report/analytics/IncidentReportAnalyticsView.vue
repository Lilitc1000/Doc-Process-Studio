<template>
  <section class="incident-report-analytics-view">
    <div class="analytics-header">
      <base-button
        variant="ghost"
        size="sm"
        @click="router.push('/incident-report')"
      >
        <svg
          viewBox="0 0 20 20"
          width="16"
          height="16"
          fill="none"
          stroke="currentColor"
          stroke-width="1.8"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path d="M12.5 15L7.5 10L12.5 5" />
        </svg>
        返回列表
      </base-button>
      <h1>统计分析</h1>
    </div>

    <div class="analytics-body">
      <stats-cards :overview="overview" />

      <div class="analytics-charts">
        <distribution-chart :overview="overview" />
        <trend-chart :trend-data="trendData" :loading="trendLoading" />
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useReportAnalytics } from './composables/useReportAnalytics';
import BaseButton from '../../../components/base/BaseButton.vue';
import StatsCards from './components/StatsCards.vue';
import DistributionChart from './components/DistributionChart.vue';
import TrendChart from './components/TrendChart.vue';

const router = useRouter();

const {
  overview,
  trendData,
  loading: trendLoading,
  load,
} = useReportAnalytics();

onMounted(() => {
  load(7);
});
</script>

<style scoped src="./styles/incident-report-analytics.css"></style>
