import { describe, expect, it, vi, beforeEach } from 'vitest';
import { useReportDetail } from '../../../src/views/incident-report/detail/composables/useReportDetail';
import * as api from '../../../src/api/incident-report';

vi.mock('../../../src/api/incident-report', () => ({
  fetchIncidentReportDetail: vi.fn(),
  fetchIncidentReportAuditLogs: vi.fn(),
}));

describe('useReportDetail', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('初始状态正确', () => {
    const { report, auditLogs, loading } = useReportDetail();
    expect(report.value).toBeNull();
    expect(auditLogs.value).toEqual([]);
    expect(loading.value).toBe(false);
  });

  it('加载报告详情', async () => {
    const mockReport = {
      id: 'rep-1',
      refNo: 'DAS-001',
      title: '测试报告',
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
      system: null,
      siteId: null,
      formData: {},
      reportData: null,
      submittedAt: null,
      approvedAt: null,
      closedAt: null,
      resolutionDate: null,
    };
    const mockLogs = [
      {
        id: 'log-1',
        action: 'create',
        actorId: 'usr-1',
        actorName: null,
        fromStatus: null,
        toStatus: 'draft',
        comment: null,
        createdAt: '2026-04-20',
      },
    ];

    (
      api.fetchIncidentReportDetail as ReturnType<typeof vi.fn>
    ).mockResolvedValue(mockReport);
    (
      api.fetchIncidentReportAuditLogs as ReturnType<typeof vi.fn>
    ).mockResolvedValue(mockLogs);

    const { report, auditLogs, load } = useReportDetail();
    await load('rep-1');

    expect(report.value).not.toBeNull();
    expect(report.value?.title).toBe('测试报告');
    expect(auditLogs.value).toHaveLength(1);
  });

  it('refreshLogs 刷新审核记录', async () => {
    const mockLogs = [
      {
        id: 'log-1',
        action: 'create',
        actorId: 'usr-1',
        actorName: null,
        fromStatus: null,
        toStatus: 'draft',
        comment: null,
        createdAt: '2026-04-20',
      },
      {
        id: 'log-2',
        action: 'submit',
        actorId: 'usr-1',
        actorName: null,
        fromStatus: 'draft',
        toStatus: 'pending',
        comment: null,
        createdAt: '2026-04-21',
      },
    ];

    (
      api.fetchIncidentReportAuditLogs as ReturnType<typeof vi.fn>
    ).mockResolvedValue(mockLogs);

    const { auditLogs, refreshLogs } = useReportDetail();
    await refreshLogs('rep-1');

    expect(auditLogs.value).toHaveLength(2);
    expect(api.fetchIncidentReportAuditLogs).toHaveBeenCalledWith('rep-1');
  });
});
