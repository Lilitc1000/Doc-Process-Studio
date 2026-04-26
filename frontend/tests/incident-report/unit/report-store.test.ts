import { describe, expect, it, vi, beforeEach } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { useIncidentReportStore } from '../../../src/stores/incident-report';
import * as incidentReportApi from '../../../src/api/incident-report';

vi.mock('../../../src/api/incident-report', () => ({
  fetchUserIncidentRoles: vi.fn().mockResolvedValue(['reporter']),
  fetchIncidentReportList: vi.fn().mockResolvedValue({ total: 0, items: [] }),
  fetchIncidentReportDetail: vi.fn().mockResolvedValue({}),
  fetchIncidentAnalyticsOverview: vi.fn().mockResolvedValue({
    total_this_month: 0,
    pending_count: 0,
    in_progress_count: 0,
    closed_this_month: 0,
    avg_resolution_hours: null,
  }),
}));

describe('useIncidentReportStore', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setActivePinia(createPinia());
  });

  it('加载用户角色后正确计算权限', async () => {
    const store = useIncidentReportStore();
    await store.loadUserIncidentRoles();

    expect(store.userIncidentRoles).toEqual(['reporter']);
    expect(store.isReporter).toBe(true);
    expect(store.canAudit).toBe(false);
    expect(store.canCreateReport).toBe(true);
  });

  it('admin 角色拥有所有权限', async () => {
    const mockFetchRoles = incidentReportApi.fetchUserIncidentRoles as ReturnType<typeof vi.fn>;
    mockFetchRoles.mockResolvedValue(['viewer', 'admin']);

    const store = useIncidentReportStore();
    await store.loadUserIncidentRoles();

    expect(store.isAdmin).toBe(true);
    expect(store.canManageSettings).toBe(true);
    expect(store.canAudit).toBe(true);
  });

  it('verifier 角色可以审核', async () => {
    const mockFetchRoles = incidentReportApi.fetchUserIncidentRoles as ReturnType<typeof vi.fn>;
    mockFetchRoles.mockResolvedValue(['verifier']);

    const store = useIncidentReportStore();
    await store.loadUserIncidentRoles();

    expect(store.isVerifier).toBe(true);
    expect(store.canAudit).toBe(true);
    expect(store.isAdmin).toBe(false);
  });

  it('无角色用户为 viewer', async () => {
    const mockFetchRoles = incidentReportApi.fetchUserIncidentRoles as ReturnType<typeof vi.fn>;
    mockFetchRoles.mockResolvedValue([]);

    const store = useIncidentReportStore();
    await store.loadUserIncidentRoles();

    expect(store.isViewer).toBe(true);
    expect(store.canCreateReport).toBe(false);
    expect(store.canAudit).toBe(false);
  });
});
