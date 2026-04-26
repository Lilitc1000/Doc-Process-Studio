import { describe, expect, it, vi, beforeEach } from 'vitest';
import { useReportAnalytics } from '../../../src/views/incident-report/analytics/composables/useReportAnalytics';
import * as api from '../../../src/api/incident-report';

vi.mock('../../../src/api/incident-report', () => ({
  fetchIncidentAnalyticsOverview: vi.fn(),
  fetchIncidentAnalyticsTrend: vi.fn(),
}));

describe('useReportAnalytics', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('初始状态正确', () => {
    const { overview, trendData, loading } = useReportAnalytics();
    expect(overview.value).toBeNull();
    expect(trendData.value).toEqual([]);
    expect(loading.value).toBe(false);
  });

  it('加载数据后更新概览和趋势', async () => {
    const mockOverview = {
      total_this_month: 10,
      pending_count: 3,
      in_progress_count: 2,
      closed_this_month: 5,
      avg_resolution_hours: 24.5,
    };
    const mockTrend = [
      { date: '2026-04-20', count: 2 },
      { date: '2026-04-21', count: 3 },
    ];

    (api.fetchIncidentAnalyticsOverview as ReturnType<typeof vi.fn>).mockResolvedValue(mockOverview);
    (api.fetchIncidentAnalyticsTrend as ReturnType<typeof vi.fn>).mockResolvedValue(mockTrend);

    const { overview, trendData, load } = useReportAnalytics();
    await load(30);

    expect(overview.value).not.toBeNull();
    expect(overview.value?.total_this_month).toBe(10);
    expect(trendData.value).toHaveLength(2);
  });
});
