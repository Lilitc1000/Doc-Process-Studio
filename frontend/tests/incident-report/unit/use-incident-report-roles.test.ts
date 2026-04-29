import { describe, expect, it, vi, beforeEach } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { useIncidentReportRoles } from '../../../src/views/incident-report/composables/useIncidentReportRoles';
import * as incidentApi from '../../../src/api/incident-report';

vi.mock('../../../src/api/incident-report', () => ({
  fetchUserIncidentRoles: vi.fn(),
  fetchUserIncidentPermissions: vi.fn(),
}));

describe('useIncidentReportRoles', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setActivePinia(createPinia());
  });

  it('初始状态：角色和权限为空，未加载', () => {
    const { roles, permissions, loading } = useIncidentReportRoles();
    expect(roles.value).toEqual([]);
    expect(permissions.value).toEqual([]);
    expect(loading.value).toBe(false);
  });

  it('loadRoles 成功加载角色和权限', async () => {
    const mockFetchRoles = incidentApi.fetchUserIncidentRoles as ReturnType<
      typeof vi.fn
    >;
    const mockFetchPerms =
      incidentApi.fetchUserIncidentPermissions as ReturnType<typeof vi.fn>;
    mockFetchRoles.mockResolvedValue(['admin', 'verifier']);
    mockFetchPerms.mockResolvedValue([
      'report:create',
      'report:audit',
      'role:manage',
    ]);

    const { loadRoles, roles, permissions, loading } = useIncidentReportRoles();
    await loadRoles();

    expect(roles.value).toEqual(['admin', 'verifier']);
    expect(permissions.value).toEqual([
      'report:create',
      'report:audit',
      'role:manage',
    ]);
    expect(loading.value).toBe(false);
  });

  it('loadRoles 失败时 loading 恢复为 false', async () => {
    const mockFetch = incidentApi.fetchUserIncidentRoles as ReturnType<
      typeof vi.fn
    >;
    mockFetch.mockRejectedValue(new Error('Network error'));

    const { loadRoles, loading } = useIncidentReportRoles();
    await expect(loadRoles()).rejects.toThrow();
    expect(loading.value).toBe(false);
  });

  it('hasRole 正确判断角色', async () => {
    const mockFetchRoles = incidentApi.fetchUserIncidentRoles as ReturnType<
      typeof vi.fn
    >;
    const mockFetchPerms =
      incidentApi.fetchUserIncidentPermissions as ReturnType<typeof vi.fn>;
    mockFetchRoles.mockResolvedValue(['reporter', 'handler']);
    mockFetchPerms.mockResolvedValue([]);

    const { loadRoles, hasRole } = useIncidentReportRoles();
    await loadRoles();

    expect(hasRole('reporter')).toBe(true);
    expect(hasRole('admin')).toBe(false);
  });

  it('hasAnyRole 正确判断任一角色', async () => {
    const mockFetchRoles = incidentApi.fetchUserIncidentRoles as ReturnType<
      typeof vi.fn
    >;
    const mockFetchPerms =
      incidentApi.fetchUserIncidentPermissions as ReturnType<typeof vi.fn>;
    mockFetchRoles.mockResolvedValue(['verifier']);
    mockFetchPerms.mockResolvedValue([]);

    const { loadRoles, hasAnyRole } = useIncidentReportRoles();
    await loadRoles();

    expect(hasAnyRole('admin', 'verifier')).toBe(true);
    expect(hasAnyRole('admin', 'handler')).toBe(false);
  });

  it('hasPermission 正确判断权限', async () => {
    const mockFetchRoles = incidentApi.fetchUserIncidentRoles as ReturnType<
      typeof vi.fn
    >;
    const mockFetchPerms =
      incidentApi.fetchUserIncidentPermissions as ReturnType<typeof vi.fn>;
    mockFetchRoles.mockResolvedValue(['admin']);
    mockFetchPerms.mockResolvedValue(['report:create', 'role:manage']);

    const { loadRoles, hasPermission } = useIncidentReportRoles();
    await loadRoles();

    expect(hasPermission('role:manage')).toBe(true);
    expect(hasPermission('report:delete')).toBe(false);
  });

  it('hasAnyPermission 正确判断任一权限', async () => {
    const mockFetchRoles = incidentApi.fetchUserIncidentRoles as ReturnType<
      typeof vi.fn
    >;
    const mockFetchPerms =
      incidentApi.fetchUserIncidentPermissions as ReturnType<typeof vi.fn>;
    mockFetchRoles.mockResolvedValue(['verifier']);
    mockFetchPerms.mockResolvedValue(['report:audit', 'report:assign']);

    const { loadRoles, hasAnyPermission } = useIncidentReportRoles();
    await loadRoles();

    expect(hasAnyPermission('role:manage', 'report:audit')).toBe(true);
    expect(hasAnyPermission('role:manage', 'report:delete')).toBe(false);
  });

  it('空角色和权限列表时判断方法返回 false', () => {
    const { hasRole, hasAnyRole, hasPermission, hasAnyPermission } =
      useIncidentReportRoles();
    expect(hasRole('admin')).toBe(false);
    expect(hasAnyRole('admin', 'verifier')).toBe(false);
    expect(hasPermission('report:create')).toBe(false);
    expect(hasAnyPermission('report:create', 'role:manage')).toBe(false);
  });
});
