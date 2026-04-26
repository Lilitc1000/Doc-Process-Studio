import { describe, expect, it, vi, beforeEach } from 'vitest';
import { useReportList } from '../../../src/views/incident-report/list/composables/useReportList';
import * as api from '../../../src/api/incident-report';

vi.mock('../../../src/api/incident-report', () => ({
  fetchIncidentReportList: vi.fn(),
}));

describe('useReportList', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('初始状态正确', () => {
    const { items, total, loading } = useReportList();
    expect(items.value).toEqual([]);
    expect(total.value).toBe(0);
    expect(loading.value).toBe(false);
  });

  it('加载数据后更新列表', async () => {
    const mockData = {
      total: 2,
      items: [
        { id: 'rep-1', ref_no: 'DAS-001', title: '测试1', status: 'draft', severity: 'P1', reporter_id: 'usr-1', reporter_name: null, assignee_id: null, assignee_name: null, verifier_id: null, verifier_name: null, fault_date: null, created_at: '2026-04-20', updated_at: '2026-04-20' },
        { id: 'rep-2', ref_no: 'DAS-002', title: '测试2', status: 'pending', severity: 'P2', reporter_id: 'usr-2', reporter_name: null, assignee_id: null, assignee_name: null, verifier_id: null, verifier_name: null, fault_date: null, created_at: '2026-04-19', updated_at: '2026-04-19' },
      ],
    };
    (api.fetchIncidentReportList as ReturnType<typeof vi.fn>).mockResolvedValue(mockData);

    const { items, total, load } = useReportList();
    await load({ page: 1 });

    expect(items.value).toHaveLength(2);
    expect(total.value).toBe(2);
    expect(items.value[0].ref_no).toBe('DAS-001');
  });
});
