import { describe, expect, it, vi, beforeEach } from 'vitest';
import { useReportList } from '@modules/incident-report/views/list/composables/useReportList';
import * as api from '@modules/incident-report';

vi.mock('@modules/incident-report', async (importOriginal) => {
  const original =
    await importOriginal<typeof import('@modules/incident-report')>();
  return {
    ...original,
    fetchIncidentReportList: vi.fn(),
  };
});

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
        {
          id: 'rep-1',
          refNo: 'DAS-001',
          title: '测试1',
          status: 'draft',
          severity: 'P1',
          reporterId: 'usr-1',
          reporterName: null,
          assigneeId: null,
          assigneeName: null,
          verifierId: null,
          verifierName: null,
          faultDate: null,
          createdAt: '2026-04-20',
          updatedAt: '2026-04-20',
        },
        {
          id: 'rep-2',
          refNo: 'DAS-002',
          title: '测试2',
          status: 'pending',
          severity: 'P2',
          reporterId: 'usr-2',
          reporterName: null,
          assigneeId: null,
          assigneeName: null,
          verifierId: null,
          verifierName: null,
          faultDate: null,
          createdAt: '2026-04-19',
          updatedAt: '2026-04-19',
        },
      ],
    };
    (api.fetchIncidentReportList as ReturnType<typeof vi.fn>).mockResolvedValue(
      mockData,
    );

    const { items, total, load } = useReportList();
    await load({ page: 1 });

    expect(items.value).toHaveLength(2);
    expect(total.value).toBe(2);
    expect(items.value[0].refNo).toBe('DAS-001');
  });
});
