import { describe, expect, it, vi, beforeEach } from 'vitest';
import { useIncidentReportStore } from '../../../src/stores/incident-report';
import { setActivePinia, createPinia } from 'pinia';
import * as api from '../../../src/api/incident-report';

vi.mock('../../../src/api/incident-report', () => ({
  fetchUserIncidentRoles: vi.fn().mockResolvedValue(['reporter']),
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
      ref_no: 'DAS-001',
      title: '测试报告',
      status: 'draft',
      severity: 'P1',
      reporter_id: 'usr-test',
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

    const mockSubmitted = { ...mockCreated, status: 'pending', submitted_at: '2026-04-20' };

    (api.createIncidentReport as ReturnType<typeof vi.fn>).mockResolvedValue(mockCreated);
    (api.submitIncidentReport as ReturnType<typeof vi.fn>).mockResolvedValue(mockSubmitted);

    const created = await api.createIncidentReport({ title: '测试报告' });
    expect(created.status).toBe('draft');

    const submitted = await api.submitIncidentReport(created.id);
    expect(submitted.status).toBe('pending');
  });

  it('verifier 可以审核通过报告', async () => {
    const mockApproved = {
      id: 'rep-1',
      ref_no: 'DAS-001',
      title: '测试报告',
      status: 'approved',
      severity: 'P1',
      reporter_id: 'usr-test',
      reporter_name: null,
      assignee_id: null,
      assignee_name: null,
      verifier_id: 'usr-verifier',
      verifier_name: null,
      fault_date: null,
      created_at: '2026-04-20',
      updated_at: '2026-04-21',
      system: null,
      site_id: null,
      form_data: {},
      report_data: null,
      submitted_at: '2026-04-20',
      approved_at: '2026-04-21',
      closed_at: null,
      resolution_date: null,
    };

    (api.approveIncidentReport as ReturnType<typeof vi.fn>).mockResolvedValue(mockApproved);

    const result = await api.approveIncidentReport('rep-1', '通过审核');
    expect(result.status).toBe('approved');
    expect(result.verifier_id).toBe('usr-verifier');
  });

  it('verifier 可以驳回报告', async () => {
    const mockRejected = {
      id: 'rep-1',
      ref_no: 'DAS-001',
      title: '测试报告',
      status: 'rejected',
      severity: 'P1',
      reporter_id: 'usr-test',
      reporter_name: null,
      assignee_id: null,
      assignee_name: null,
      verifier_id: 'usr-verifier',
      verifier_name: null,
      fault_date: null,
      created_at: '2026-04-20',
      updated_at: '2026-04-21',
      system: null,
      site_id: null,
      form_data: {},
      report_data: null,
      submitted_at: '2026-04-20',
      approved_at: null,
      closed_at: null,
      resolution_date: null,
    };

    (api.rejectIncidentReport as ReturnType<typeof vi.fn>).mockResolvedValue(mockRejected);

    const result = await api.rejectIncidentReport('rep-1', '信息不完整');
    expect(result.status).toBe('rejected');
  });

  it('handler 可以关闭报告', async () => {
    const mockClosed = {
      id: 'rep-1',
      ref_no: 'DAS-001',
      title: '测试报告',
      status: 'closed',
      severity: 'P1',
      reporter_id: 'usr-test',
      reporter_name: null,
      assignee_id: 'usr-handler',
      assignee_name: null,
      verifier_id: 'usr-verifier',
      verifier_name: null,
      fault_date: null,
      created_at: '2026-04-20',
      updated_at: '2026-04-22',
      system: null,
      site_id: null,
      form_data: {},
      report_data: null,
      submitted_at: '2026-04-20',
      approved_at: '2026-04-21',
      closed_at: '2026-04-22',
      resolution_date: '2026-04-22',
    };

    (api.closeIncidentReport as ReturnType<typeof vi.fn>).mockResolvedValue(mockClosed);

    const result = await api.closeIncidentReport('rep-1', '问题已解决');
    expect(result.status).toBe('closed');
    expect(result.closed_at).toBeTruthy();
  });
});
