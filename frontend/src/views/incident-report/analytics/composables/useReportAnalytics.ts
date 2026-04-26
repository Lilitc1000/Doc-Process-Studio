import { ref } from 'vue';
import {
  fetchIncidentAnalyticsOverview,
  fetchIncidentAnalyticsTrend,
} from '../../../../api/incident-report';
import type {
  IncidentAnalyticsOverview,
  IncidentAnalyticsTrend,
} from '../../../../types/incident-report/incident-report';

export function useReportAnalytics() {
  const overview = ref<IncidentAnalyticsOverview | null>(null);
  const trendData = ref<IncidentAnalyticsTrend[]>([]);
  const loading = ref(false);

  const load = async (days = 30) => {
    loading.value = true;
    try {
      const [overviewData, trend] = await Promise.all([
        fetchIncidentAnalyticsOverview(),
        fetchIncidentAnalyticsTrend(days),
      ]);
      overview.value = overviewData;
      trendData.value = trend;
    } finally {
      loading.value = false;
    }
  };

  return { overview, trendData, loading, load };
}
