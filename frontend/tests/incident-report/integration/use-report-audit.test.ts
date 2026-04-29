import { describe, expect, it, vi, beforeEach } from 'vitest';
import { useReportAudit } from '../../../src/views/incident-report/audit/composables/useReportAudit';
import * as api from '../../../src/api/incident-report';

vi.mock('../../../src/api/incident-report', () => ({
  fetchIncidentReportDetail: vi.fn(),
  approveIncidentReport: vi.fn(),
  rejectIncidentReport: vi.fn(),
}));

describe('useReportAudit', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('初始状态正确', () => {
    const { report, loading, processing } = useReportAudit();
    expect(report.value).toBeNull();
    expect(loading.value).toBe(false);
    expect(processing.value).toBe(false);
  });

  it('审核通过后更新报告状态', async () => {
    const mockReport = {
      id: 'rep-1',
      refNo: 'DAS-001',
      title: '测试报告',
      status: 'approved',
      severity: 'P1',
      reporterId: 'usr-1',
      reporterName: null,
      assigneeId: null,
      assigneeName: null,
      verifierId: 'usr-verifier',
      verifierName: null,
      faultDate: null,
      createdAt: '2026-04-20',
      updatedAt: '2026-04-20',
      system: null,
      siteId: null,
      formData: {},
      reportData: null,
      submittedAt: null,
      approvedAt: '2026-04-21',
      closedAt: null,
      resolutionDate: null,
    };

    (api.approveIncidentReport as ReturnType<typeof vi.fn>).mockResolvedValue(
      mockReport,
    );

    const { report, approve } = useReportAudit();
    await approve('rep-1', '通过审核');

    expect(report.value).not.toBeNull();
    expect(report.value?.status).toBe('approved');
  });

  it('驳回后更新报告状态', async () => {
    const mockReport = {
      id: 'rep-1',
      refNo: 'DAS-001',
      title: '测试报告',
      status: 'rejected',
      severity: 'P1',
      reporterId: 'usr-1',
      reporterName: null,
      assigneeId: null,
      assigneeName: null,
      verifierId: 'usr-verifier',
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

    (api.rejectIncidentReport as ReturnType<typeof vi.fn>).mockResolvedValue(
      mockReport,
    );

    const { report, reject } = useReportAudit();
    await reject('rep-1', '信息不完整');

    expect(report.value).not.toBeNull();
    expect(report.value?.status).toBe('rejected');
  });
});
