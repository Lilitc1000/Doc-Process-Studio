import { describe, expect, it, vi, beforeEach } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { useAuthStore } from '@modules/auth';
import * as authApi from '@modules/auth';

vi.mock('@modules/auth', async (importOriginal) => {
  const original = await importOriginal<typeof import('@modules/auth')>();
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
      tokenType: 'bearer',
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
      tokenType: 'bearer',
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

  it('refreshAccessToken 失败时清除认证状态', async () => {
    const store = useAuthStore();
    store.refreshToken = 'expired_refresh';
    localStorage.setItem('refresh_token', 'expired_refresh');

    const mockRefresh = authApi.refreshToken as ReturnType<typeof vi.fn>;
    mockRefresh.mockRejectedValue(new Error('Token expired'));

    const result = await store.refreshAccessToken();
    expect(result).toBeNull();
    expect(store.isAuthenticated).toBe(false);
    expect(localStorage.getItem('refresh_token')).toBeNull();
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
});
