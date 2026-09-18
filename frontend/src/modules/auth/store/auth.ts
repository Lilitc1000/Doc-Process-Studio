import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type { UserInfoResponse } from '../types/auth';
import {
  loginUser,
  registerUser,
  refreshToken as refreshTokenApi,
  logoutUser,
  getCurrentUser,
} from '../api/auth';

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref<string | null>(null);
  const refreshToken = ref<string | null>(
    localStorage.getItem('refresh_token'),
  );
  const userInfo = ref<UserInfoResponse | null>(null);
  const isRefreshing = ref(false);

  const isAuthenticated = computed(() => !!accessToken.value);
  const userId = computed(() => userInfo.value?.userId ?? '');
  const username = computed(() => userInfo.value?.username ?? '');
  const avatarColor = computed(() => userInfo.value?.avatarColor ?? '#4f46e5');

  /**
   * 全局管理员。用于判定能否查看/修改全系统共享设置（如 RAGFlow 连接信息与密钥）。
   *
   * 命名刻意与事故报告模块的 `isAdmin` 区分开：那个是**模块级**角色
   * （`incident_report_user_roles` 里的 `admin`），只在该模块内生效，
   * 拿来守全局设置会把"给某人分配报告审核人"变成"能改全局密钥"。
   */
  const isGlobalAdmin = computed(() => userInfo.value?.role === 'admin');

  async function login(usernameVal: string, password: string) {
    const response = await loginUser({ username: usernameVal, password });
    accessToken.value = response.accessToken;
    refreshToken.value = response.refreshToken;
    localStorage.setItem('refresh_token', response.refreshToken);
    await fetchUserInfo();
  }

  async function register(usernameVal: string, password: string) {
    await registerUser({ username: usernameVal, password });
  }

  async function refreshAccessToken(): Promise<string | null> {
    if (isRefreshing.value) return null;
    if (!refreshToken.value) {
      clearAuth();
      return null;
    }

    isRefreshing.value = true;
    try {
      const response = await refreshTokenApi({
        refreshToken: refreshToken.value,
      });
      accessToken.value = response.accessToken;
      refreshToken.value = response.refreshToken;
      localStorage.setItem('refresh_token', response.refreshToken);
      return response.accessToken;
    } catch {
      clearAuth();
      return null;
    } finally {
      isRefreshing.value = false;
    }
  }

  async function logout() {
    if (refreshToken.value) {
      try {
        await logoutUser({ refreshToken: refreshToken.value });
      } catch {
        // ignore
      }
    }
    clearAuth();
  }

  async function fetchUserInfo() {
    try {
      userInfo.value = await getCurrentUser();
    } catch {
      userInfo.value = null;
    }
  }

  function clearAuth() {
    accessToken.value = null;
    refreshToken.value = null;
    userInfo.value = null;
    localStorage.removeItem('refresh_token');
  }

  return {
    accessToken,
    refreshToken,
    userInfo,
    isRefreshing,
    isAuthenticated,
    userId,
    username,
    avatarColor,
    isGlobalAdmin,
    login,
    register,
    refreshAccessToken,
    logout,
    fetchUserInfo,
    clearAuth,
  };
});
