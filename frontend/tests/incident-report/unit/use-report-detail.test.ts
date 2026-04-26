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
      ref_no: 'DAS-001',
      title: '测试报告',
      status: 'draft',
      severity: 'P1',
      reporter_id: 'usr-1',
      reporter_name: null,
      assignee_id: null,
      assignee_name: null,
      verifier_id: null,
      verifier_name: null,
      fault_date: null,
      created_at: '2026-04-20',
      updated_at: '2026-04-20',
      system: null,
      site_id: null,
      form_data: {},
      report_data: null,
      submitted_at: null,
      approved_at: null,
      closed_at: null,
      resolution_date: null,
    };
    const mockLogs = [
      {
        id: 'log-1',
        action: 'create',
        actor_id: 'usr-1',
        actor_name: null,
        from_status: null,
        to_status: 'draft',
        comment: null,
        created_at: '2026-04-20',
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
});
