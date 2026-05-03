import { describe, expect, it, vi, beforeEach } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import * as api from '../../../src/api/incident-report';

vi.mock('../../../src/api/incident-report', () => ({
  fetchUserIncidentRolesAndPermissions: vi.fn().mockResolvedValue({
    roles: ['reporter'],
    permissions: ['report:create', 'report:edit_own', 'report:submit'],
  }),
  fetchIncidentReportList: vi.fn().mockResolvedValue({ total: 0, items: [] }),
  fetchIncidentReportDetail: vi.fn(),
  fetchIncidentAnalyticsOverview: vi.fn().mockResolvedValue({
    total_this_month: 0,
    pending_count: 0,
    in_progress_count: 0,
    closed_this_month: 0,
    avg_resolution_hours: null,
  }),
  createIncidentReport: vi.fn(),
  submitIncidentReport: vi.fn(),
  approveIncidentReport: vi.fn(),
  rejectIncidentReport: vi.fn(),
  closeIncidentReport: vi.fn(),
  reopenIncidentReport: vi.fn(),
}));

describe('报告状态流转集成测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setActivePinia(createPinia());
  });

  it('reporter 可以创建并提交报告', async () => {
    const mockCreated = {
      id: 'rep-1',
      refNo: 'DAS-001',
      title: '测试报告',
      status: 'draft',
      severity: 'P1',
      reporterId: 'usr-test',
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

    const mockSubmitted = {
      ...mockCreated,
      status: 'pending',
      submittedAt: '2026-04-20',
    };

    (api.createIncidentReport as ReturnType<typeof vi.fn>).mockResolvedValue(
      mockCreated,
    );
    (api.submitIncidentReport as ReturnType<typeof vi.fn>).mockResolvedValue(
      mockSubmitted,
    );

    const created = await api.createIncidentReport({ title: '测试报告' });
    expect(created.status).toBe('draft');

    const submitted = await api.submitIncidentReport(created.id);
    expect(submitted.status).toBe('pending');
  });

  it('verifier 可以审核通过报告', async () => {
    const mockApproved = {
      id: 'rep-1',
      refNo: 'DAS-001',
      title: '测试报告',
      status: 'approved',
      severity: 'P1',
      reporterId: 'usr-test',
      reporterName: null,
      assigneeId: null,
      assigneeName: null,
      verifierId: 'usr-verifier',
      verifierName: null,
      faultDate: null,
      createdAt: '2026-04-20',
      updatedAt: '2026-04-21',
      system: null,
      siteId: null,
      formData: {},
      reportData: null,
      submittedAt: '2026-04-20',
      approvedAt: '2026-04-21',
      closedAt: null,
      resolutionDate: null,
    };

    (api.approveIncidentReport as ReturnType<typeof vi.fn>).mockResolvedValue(
      mockApproved,
    );

    const result = await api.approveIncidentReport('rep-1', '通过审核');
    expect(result.status).toBe('approved');
    expect(result.verifierId).toBe('usr-verifier');
  });

  it('verifier 可以驳回报告', async () => {
    const mockRejected = {
      id: 'rep-1',
      refNo: 'DAS-001',
      title: '测试报告',
      status: 'rejected',
      severity: 'P1',
      reporterId: 'usr-test',
      reporterName: null,
      assigneeId: null,
      assigneeName: null,
      verifierId: 'usr-verifier',
      verifierName: null,
      faultDate: null,
      createdAt: '2026-04-20',
      updatedAt: '2026-04-21',
      system: null,
      siteId: null,
      formData: {},
      reportData: null,
      submittedAt: '2026-04-20',
      approvedAt: null,
      closedAt: null,
      resolutionDate: null,
    };

    (api.rejectIncidentReport as ReturnType<typeof vi.fn>).mockResolvedValue(
      mockRejected,
    );

    const result = await api.rejectIncidentReport('rep-1', '信息不完整');
    expect(result.status).toBe('rejected');
  });

  it('handler 可以关闭报告', async () => {
    const mockClosed = {
      id: 'rep-1',
      refNo: 'DAS-001',
      title: '测试报告',
      status: 'closed',
      severity: 'P1',
      reporterId: 'usr-test',
      reporterName: null,
      assigneeId: 'usr-handler',
      assigneeName: null,
      verifierId: 'usr-verifier',
      verifierName: null,
      faultDate: null,
      createdAt: '2026-04-20',
      updatedAt: '2026-04-22',
      system: null,
      siteId: null,
      formData: {},
      reportData: null,
      submittedAt: '2026-04-20',
      approvedAt: '2026-04-21',
      closedAt: '2026-04-22',
      resolutionDate: '2026-04-22',
    };

    (api.closeIncidentReport as ReturnType<typeof vi.fn>).mockResolvedValue(
      mockClosed,
    );

    const result = await api.closeIncidentReport('rep-1', '问题已解决');
    expect(result.status).toBe('closed');
    expect(result.closedAt).toBeTruthy();
  });
});
