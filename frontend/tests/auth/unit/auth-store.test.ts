import { describe, expect, it, vi, beforeEach } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { useAuthStore } from '@modules/auth';
import * as authApi from '@modules/auth';

vi.mock('@modules/auth/api/auth', async (importOriginal) => {
  const original =
    await importOriginal<typeof import('@modules/auth/api/auth')>();
  return {
    ...original,
    loginUser: vi.fn(),
    registerUser: vi.fn(),
    refreshToken: vi.fn(),
    logoutUser: vi.fn(),
    getCurrentUser: vi.fn(),
    updateProfile: vi.fn(),
    changePassword: vi.fn(),
  };
});

/**
 * 构造一个带 exp 声明的 JWT。
 * 只用于测试续期排期，不参与任何签名校验。
 */
function makeJwt(expiresInSeconds: number): string {
  const payload = btoa(
    JSON.stringify({ exp: Math.floor(Date.now() / 1000) + expiresInSeconds }),
  )
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');
  return `header.${payload}.signature`;
}

describe('useAuthStore', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    setActivePinia(createPinia());
  });

  it('初始状态：未认证，无 token', () => {
    const store = useAuthStore();
    expect(store.isAuthenticated).toBe(false);
    expect(store.accessToken).toBeNull();
    expect(store.userInfo).toBeNull();
  });

  it('login 成功后设置 token 和用户信息', async () => {
    const store = useAuthStore();
    const mockLogin = authApi.loginUser as ReturnType<typeof vi.fn>;
    const mockGetUser = authApi.getCurrentUser as ReturnType<typeof vi.fn>;

    mockLogin.mockResolvedValue({
      accessToken: 'test_access_token',
      refreshToken: 'test_refresh_token',
    });
    mockGetUser.mockResolvedValue({
      userId: 'usr_test123',
      username: 'testuser',
      avatarColor: '#4f46e5',
      createdAt: '2026-01-01T00:00:00Z',
    });

    await store.login('testuser', 'password123');

    expect(store.isAuthenticated).toBe(true);
    expect(store.accessToken).toBe('test_access_token');
    expect(store.refreshToken).toBe('test_refresh_token');
    expect(localStorage.getItem('refresh_token')).toBe('test_refresh_token');
    expect(store.username).toBe('testuser');
    expect(store.avatarColor).toBe('#4f46e5');
  });

  it('login 失败后保持未认证状态', async () => {
    const store = useAuthStore();
    const mockLogin = authApi.loginUser as ReturnType<typeof vi.fn>;
    mockLogin.mockRejectedValue(new Error('Invalid credentials'));

    await expect(store.login('testuser', 'wrong')).rejects.toThrow();
    expect(store.isAuthenticated).toBe(false);
    expect(store.accessToken).toBeNull();
  });

  it('register 调用 API', async () => {
    const store = useAuthStore();
    const mockRegister = authApi.registerUser as ReturnType<typeof vi.fn>;
    mockRegister.mockResolvedValue({});

    await store.register('newuser', 'password123');
    expect(mockRegister).toHaveBeenCalledWith({
      username: 'newuser',
      password: 'password123',
    });
  });

  it('refreshAccessToken 成功后更新 token', async () => {
    const store = useAuthStore();
    store.refreshToken = 'old_refresh';
    localStorage.setItem('refresh_token', 'old_refresh');

    const mockRefresh = authApi.refreshToken as ReturnType<typeof vi.fn>;
    mockRefresh.mockResolvedValue({
      accessToken: 'new_access',
      refreshToken: 'new_refresh',
    });

    const result = await store.refreshAccessToken();
    expect(result).toBe('new_access');
    expect(store.accessToken).toBe('new_access');
    expect(localStorage.getItem('refresh_token')).toBe('new_refresh');
  });

  it('refreshAccessToken 无 refresh_token 时清除认证状态', async () => {
    const store = useAuthStore();
    localStorage.removeItem('refresh_token');
    store.refreshToken = null;

    const result = await store.refreshAccessToken();
    expect(result).toBeNull();
    expect(store.isAuthenticated).toBe(false);
  });

  it('refreshAccessToken 令牌被拒绝（401）时清除认证状态', async () => {
    const store = useAuthStore();
    store.refreshToken = 'expired_refresh';
    localStorage.setItem('refresh_token', 'expired_refresh');

    const mockRefresh = authApi.refreshToken as ReturnType<typeof vi.fn>;
    mockRefresh.mockRejectedValue(
      Object.assign(new Error('Unauthorized'), {
        response: { status: 401 },
      }),
    );

    const result = await store.refreshAccessToken();
    expect(result).toBeNull();
    expect(store.isAuthenticated).toBe(false);
    expect(localStorage.getItem('refresh_token')).toBeNull();
  });

  it('refreshAccessToken 网络错误时保留登录态', async () => {
    const store = useAuthStore();
    store.accessToken = 'existing_access';
    store.refreshToken = 'valid_refresh';
    localStorage.setItem('refresh_token', 'valid_refresh');

    const mockRefresh = authApi.refreshToken as ReturnType<typeof vi.fn>;
    // 没有 response，属于网络层失败，不该把用户踢下线
    mockRefresh.mockRejectedValue(new Error('Network Error'));

    const result = await store.refreshAccessToken();
    expect(result).toBeNull();
    expect(store.isAuthenticated).toBe(true);
    expect(localStorage.getItem('refresh_token')).toBe('valid_refresh');
  });

  it('并发刷新只发一次请求，且共享结果', async () => {
    const store = useAuthStore();
    store.refreshToken = 'shared_refresh';
    localStorage.setItem('refresh_token', 'shared_refresh');

    const mockRefresh = authApi.refreshToken as ReturnType<typeof vi.fn>;
    mockRefresh.mockResolvedValue({
      accessToken: 'concurrent_access',
      refreshToken: 'concurrent_refresh',
    });

    // 同时发起三次刷新（模拟三个请求同时撞上 401）
    const results = await Promise.all([
      store.refreshAccessToken(),
      store.refreshAccessToken(),
      store.refreshAccessToken(),
    ]);

    expect(mockRefresh).toHaveBeenCalledTimes(1);
    expect(results).toEqual([
      'concurrent_access',
      'concurrent_access',
      'concurrent_access',
    ]);
    expect(store.accessToken).toBe('concurrent_access');
  });

  it('令牌已进入过期窗口时立即主动续期', async () => {
    const store = useAuthStore();
    const mockLogin = authApi.loginUser as ReturnType<typeof vi.fn>;
    const mockRefresh = authApi.refreshToken as ReturnType<typeof vi.fn>;
    const mockGetUser = authApi.getCurrentUser as ReturnType<typeof vi.fn>;

    mockGetUser.mockResolvedValue({ userId: 'usr_1', username: 'tester' });
    // 30 秒后过期，已经落在"提前 60 秒续期"的窗口内
    mockLogin.mockResolvedValue({
      accessToken: makeJwt(30),
      refreshToken: 'r1',
    });
    mockRefresh.mockResolvedValue({
      accessToken: makeJwt(900),
      refreshToken: 'r2',
    });

    await store.login('tester', 'password123');
    expect(mockRefresh).toHaveBeenCalledTimes(1);
  });

  it('令牌离过期还早时不立即刷新，到期前才续', async () => {
    vi.useFakeTimers();
    try {
      const store = useAuthStore();
      const mockLogin = authApi.loginUser as ReturnType<typeof vi.fn>;
      const mockRefresh = authApi.refreshToken as ReturnType<typeof vi.fn>;
      const mockGetUser = authApi.getCurrentUser as ReturnType<typeof vi.fn>;

      mockGetUser.mockResolvedValue({ userId: 'usr_1', username: 'tester' });
      // 15 分钟后过期
      mockLogin.mockResolvedValue({
        accessToken: makeJwt(900),
        refreshToken: 'r1',
      });
      mockRefresh.mockResolvedValue({
        accessToken: makeJwt(900),
        refreshToken: 'r2',
      });

      await store.login('tester', 'password123');
      expect(mockRefresh).not.toHaveBeenCalled();

      // 快进到"过期前 60 秒"的续期点之后
      await vi.advanceTimersByTimeAsync((900 - 60) * 1000 + 1000);
      expect(mockRefresh).toHaveBeenCalledTimes(1);
    } finally {
      vi.useRealTimers();
    }
  });

  it('logout 清除所有认证状态', async () => {
    const store = useAuthStore();
    store.accessToken = 'test_access';
    store.refreshToken = 'test_refresh';
    localStorage.setItem('refresh_token', 'test_refresh');
    store.userInfo = {
      userId: 'usr_test',
      username: 'testuser',
      avatarColor: '#4f46e5',
      role: 'member',
      createdAt: '2026-01-01T00:00:00Z',
    };

    const mockLogout = authApi.logoutUser as ReturnType<typeof vi.fn>;
    mockLogout.mockResolvedValue({});

    await store.logout();

    expect(store.accessToken).toBeNull();
    expect(store.refreshToken).toBeNull();
    expect(store.userInfo).toBeNull();
    expect(localStorage.getItem('refresh_token')).toBeNull();
  });

  it('clearAuth 重置所有状态', () => {
    const store = useAuthStore();
    store.accessToken = 'test_access';
    store.refreshToken = 'test_refresh';
    localStorage.setItem('refresh_token', 'test_refresh');
    store.userInfo = {
      userId: 'usr_test',
      username: 'testuser',
      avatarColor: '#4f46e5',
      role: 'member',
      createdAt: '2026-01-01T00:00:00Z',
    };

    store.clearAuth();

    expect(store.accessToken).toBeNull();
    expect(store.refreshToken).toBeNull();
    expect(store.userInfo).toBeNull();
    expect(localStorage.getItem('refresh_token')).toBeNull();
  });

  it('computed 属性正确反映用户信息', () => {
    const store = useAuthStore();
    store.userInfo = {
      userId: 'usr_abc',
      username: 'admin',
      avatarColor: '#ef4444',
      role: 'admin',
      createdAt: '2026-01-01T00:00:00Z',
    };

    expect(store.userId).toBe('usr_abc');
    expect(store.username).toBe('admin');
    expect(store.avatarColor).toBe('#ef4444');
  });

  it('computed 属性在无用户信息时返回默认值', () => {
    const store = useAuthStore();
    store.userInfo = null;

    expect(store.userId).toBe('');
    expect(store.username).toBe('');
    expect(store.avatarColor).toBe('#4f46e5');
  });

  // isGlobalAdmin 决定能否修改全系统共享设置（如 RAGFlow 凭据），
  // 所以这里必须覆盖"未知角色一律 false"这条 fail-closed 规则。
  describe('isGlobalAdmin', () => {
    const withRole = (role: string) => {
      const store = useAuthStore();
      store.userInfo = {
        userId: 'usr_role_test',
        username: 'role-tester',
        avatarColor: '#4f46e5',
        role,
        createdAt: '2026-01-01T00:00:00Z',
      };
      return store;
    };

    it("role 为 'admin' 时为 true", () => {
      expect(withRole('admin').isGlobalAdmin).toBe(true);
    });

    it.each(['member', '', 'Admin', 'administrator', 'root'])(
      'role 为 %p 时为 false（fail closed）',
      (role) => {
        expect(withRole(role).isGlobalAdmin).toBe(false);
      },
    );

    it('无用户信息时为 false', () => {
      const store = useAuthStore();
      store.userInfo = null;
      expect(store.isGlobalAdmin).toBe(false);
    });
  });
});
