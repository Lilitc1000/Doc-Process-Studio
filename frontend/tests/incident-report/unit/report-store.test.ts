import { describe, expect, it, vi, beforeEach } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { useIncidentReportStore } from '../../../src/stores/incident-report';
import * as incidentReportApi from '../../../src/api/incident-report';

vi.mock('../../../src/api/incident-report', () => ({
  fetchUserIncidentRolesAndPermissions: vi.fn().mockResolvedValue({
    roles: ['reporter'],
    permissions: ['report:create', 'report:edit_own', 'report:submit'],
  }),
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

  it('加载用户角色和权限后正确计算', async () => {
    const store = useIncidentReportStore();
    await store.loadUserIncidentRoles();

    expect(store.userIncidentRoles).toEqual(['reporter']);
    expect(store.userIncidentPermissions).toEqual([
      'report:create',
      'report:edit_own',
      'report:submit',
    ]);
    expect(store.isReporter).toBe(true);
    expect(store.canAudit).toBe(false);
    expect(store.canCreateReport).toBe(true);
  });

  it('admin 角色拥有所有权限', async () => {
    const mockFetch =
      incidentReportApi.fetchUserIncidentRolesAndPermissions as ReturnType<
        typeof vi.fn
      >;
    mockFetch.mockResolvedValue({
      roles: ['viewer', 'admin'],
      permissions: [
        'report:create',
        'report:edit_own',
        'report:submit',
        'report:view',
        'report:view_all',
        'report:edit_assigned',
        'report:close_assigned',
        'report:audit',
        'report:assign',
        'report:delete',
        'report:reopen',
        'role:manage',
        'system:config',
        'data:export',
        'analytics:view',
      ],
    });

    const store = useIncidentReportStore();
    await store.loadUserIncidentRoles();

    expect(store.isAdmin).toBe(true);
    expect(store.canManageSettings).toBe(true);
    expect(store.canAudit).toBe(true);
  });

  it('verifier 角色可以审核', async () => {
    const mockFetch =
      incidentReportApi.fetchUserIncidentRolesAndPermissions as ReturnType<
        typeof vi.fn
      >;
    mockFetch.mockResolvedValue({
      roles: ['verifier'],
      permissions: [
        'report:view',
        'report:view_all',
        'report:audit',
        'report:assign',
        'analytics:view',
      ],
    });

    const store = useIncidentReportStore();
    await store.loadUserIncidentRoles();

    expect(store.isVerifier).toBe(true);
    expect(store.canAudit).toBe(true);
    expect(store.isAdmin).toBe(false);
  });

  it('无角色用户无权限', async () => {
    const mockFetch =
      incidentReportApi.fetchUserIncidentRolesAndPermissions as ReturnType<
        typeof vi.fn
      >;
    mockFetch.mockResolvedValue({
      roles: [],
      permissions: [],
    });

    const store = useIncidentReportStore();
    await store.loadUserIncidentRoles();

    expect(store.userIncidentRoles).toEqual([]);
    expect(store.canCreateReport).toBe(false);
    expect(store.canAudit).toBe(false);
  });
});
