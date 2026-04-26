import { describe, expect, it, vi, beforeEach } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { useIncidentReportRoles } from '../../../src/views/incident-report/composables/useIncidentReportRoles';
import * as incidentApi from '../../../src/api/incident-report';

vi.mock('../../../src/api/incident-report', () => ({
  fetchUserIncidentRoles: vi.fn(),
}));

describe('useIncidentReportRoles', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setActivePinia(createPinia());
  });

  it('初始状态：角色为空，未加载', () => {
    const { roles, loading } = useIncidentReportRoles();
    expect(roles.value).toEqual([]);
    expect(loading.value).toBe(false);
  });

  it('loadRoles 成功加载角色', async () => {
    const mockFetch = incidentApi.fetchUserIncidentRoles as ReturnType<
      typeof vi.fn
    >;
    mockFetch.mockResolvedValue(['admin', 'verifier']);

    const { loadRoles, roles, loading } = useIncidentReportRoles();
    await loadRoles();

    expect(roles.value).toEqual(['admin', 'verifier']);
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
    const mockFetch = incidentApi.fetchUserIncidentRoles as ReturnType<
      typeof vi.fn
    >;
    mockFetch.mockResolvedValue(['reporter', 'handler']);

    const { loadRoles, hasRole } = useIncidentReportRoles();
    await loadRoles();

    expect(hasRole('reporter')).toBe(true);
    expect(hasRole('admin')).toBe(false);
  });

  it('hasAnyRole 正确判断任一角色', async () => {
    const mockFetch = incidentApi.fetchUserIncidentRoles as ReturnType<
      typeof vi.fn
    >;
    mockFetch.mockResolvedValue(['verifier']);

    const { loadRoles, hasAnyRole } = useIncidentReportRoles();
    await loadRoles();

    expect(hasAnyRole('admin', 'verifier')).toBe(true);
    expect(hasAnyRole('admin', 'handler')).toBe(false);
  });

  it('空角色列表时 hasRole 返回 false', () => {
    const { hasRole, hasAnyRole } = useIncidentReportRoles();
    expect(hasRole('admin')).toBe(false);
    expect(hasAnyRole('admin', 'verifier')).toBe(false);
  });
});
