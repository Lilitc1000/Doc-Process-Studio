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
    login,
    register,
    refreshAccessToken,
    logout,
    fetchUserInfo,
    clearAuth,
  };
});
