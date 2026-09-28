import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type { UserInfoResponse } from '../types/auth';
import {
  fetchSetupStatus,
  loginUser,
  registerUser,
  refreshToken as refreshTokenApi,
  logoutUser,
  getCurrentUser,
  setupAdmin as setupAdminApi,
} from '../api/auth';

/** 在令牌过期前多久主动续期 */
const REFRESH_LEAD_SECONDS = 60;
/** setTimeout 的毫秒上限，超过会被当成 0 立即触发 */
const MAX_TIMEOUT_MS = 2_147_483_647;

/** 从 JWT 解析过期时间（Unix 秒）。解析失败返回 null，退回"401 之后被动刷新"。 */
function parseTokenExpiration(token: string | null): number | null {
  if (!token) return null;
  try {
    const payload = token.split('.')[1];
    if (!payload) return null;
    // JWT 用的是 base64url，需要先转成标准 base64
    const normalized = payload.replace(/-/g, '+').replace(/_/g, '/');
    const decoded = JSON.parse(atob(normalized)) as { exp?: unknown };
    return typeof decoded.exp === 'number' ? decoded.exp : null;
  } catch {
    return null;
  }
}

/**
 * 是否属于"令牌确实被拒绝"。
 *
 * 网络抖动、后端临时不可用不该让用户掉线 —— 那种情况下保留登录态，
 * 让当前请求失败即可，下一次操作还有机会自动恢复。
 */
function isTokenRejected(error: unknown): boolean {
  const status = (error as { response?: { status?: number } } | null)?.response
    ?.status;
  return status === 401 || status === 400;
}

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref<string | null>(null);
  const refreshToken = ref<string | null>(
    localStorage.getItem('refresh_token'),
  );
  const userInfo = ref<UserInfoResponse | null>(null);

  /**
   * 正在进行的刷新请求。
   *
   * 后端刷新会轮换令牌（签发新 refresh token 后把旧的加入黑名单），
   * 因此并发发起多个刷新必然只有一个成功、其余拿到已失效的令牌。
   * 并发的 401 必须共用同一个 Promise，而不是各自发起一次刷新。
   */
  let refreshPromise: Promise<string | null> | null = null;
  /** 主动续期的定时器 */
  let refreshTimer: ReturnType<typeof setTimeout> | null = null;

  const isAuthenticated = computed(() => !!accessToken.value);
  const userId = computed(() => userInfo.value?.userId ?? '');
  const username = computed(() => userInfo.value?.username ?? '');
  const avatarColor = computed(() => userInfo.value?.avatarColor ?? '#4f46e5');

  /**
   * 系统是否还缺少首个管理员。
   *
   * 未认证时由路由守卫惰性拉取一次（见 `setupStatusLoaded`），为 true 时
   * 所有路由都会被引导到 `/setup`；创建成功后立即翻回 false。
   */
  const needsSetup = ref(false);
  /** setup 状态是否已拉取过（只拉一次，避免每次导航都打接口） */
  const setupStatusLoaded = ref(false);

  /**
   * 全局管理员。用于判定能否查看/修改全系统共享设置（如 RAGFlow 连接信息与密钥）。
   *
   * 命名刻意与事故报告模块的 `isAdmin` 区分开：那个是**模块级**角色
   * （`incident_report_user_roles` 里的 `admin`），只在该模块内生效，
   * 拿来守全局设置会把"给某人分配报告审核人"变成"能改全局密钥"。
   */
  const isGlobalAdmin = computed(() => userInfo.value?.role === 'admin');

  /**
   * 在令牌过期前主动续期。
   *
   * 不做这一步的话，过期那一刻所有并发请求会同时撞上 401，
   * 即便有并发保护，用户也会感知到一次明显的卡顿。
   */
  function scheduleProactiveRefresh() {
    if (refreshTimer) {
      clearTimeout(refreshTimer);
      refreshTimer = null;
    }

    // 后台标签不排期：浏览器会节流定时器，回到前台时会重新检查
    if (document.visibilityState === 'hidden') return;

    const expiresAt = parseTokenExpiration(accessToken.value);
    if (!expiresAt) return;

    const delay = (expiresAt - REFRESH_LEAD_SECONDS) * 1000 - Date.now();
    if (delay <= 0) {
      // 已进入过期窗口，立即续
      void refreshAccessToken();
      return;
    }
    refreshTimer = setTimeout(
      () => void refreshAccessToken(),
      Math.min(delay, MAX_TIMEOUT_MS),
    );
  }

  async function login(usernameVal: string, password: string) {
    const response = await loginUser({ username: usernameVal, password });
    accessToken.value = response.accessToken;
    refreshToken.value = response.refreshToken;
    localStorage.setItem('refresh_token', response.refreshToken);
    await fetchUserInfo();
    scheduleProactiveRefresh();
  }

  async function register(usernameVal: string, password: string) {
    await registerUser({ username: usernameVal, password });
  }

  /** 拉取一次 setup 状态（失败按"无需 setup"处理，回退到登录页） */
  async function loadSetupStatus() {
    try {
      needsSetup.value = await fetchSetupStatus();
    } catch {
      needsSetup.value = false;
    } finally {
      setupStatusLoaded.value = true;
    }
  }

  async function setupAdmin(usernameVal: string, password: string) {
    await setupAdminApi({ username: usernameVal, password });
    needsSetup.value = false;
  }

  async function refreshAccessToken(): Promise<string | null> {
    if (!refreshToken.value) {
      clearAuth();
      return null;
    }

    // 已有刷新在进行：共用同一个 Promise，让并发请求一起等结果
    if (refreshPromise) return refreshPromise;

    refreshPromise = (async () => {
      try {
        const response = await refreshTokenApi({
          refreshToken: refreshToken.value as string,
        });
        accessToken.value = response.accessToken;
        refreshToken.value = response.refreshToken;
        localStorage.setItem('refresh_token', response.refreshToken);
        scheduleProactiveRefresh();
        return response.accessToken;
      } catch (error) {
        // 只有令牌确实被拒绝才清理登录态；网络问题保留登录态
        if (isTokenRejected(error)) {
          clearAuth();
        }
        return null;
      } finally {
        refreshPromise = null;
      }
    })();

    return refreshPromise;
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
    if (refreshTimer) {
      clearTimeout(refreshTimer);
      refreshTimer = null;
    }
    accessToken.value = null;
    refreshToken.value = null;
    userInfo.value = null;
    localStorage.removeItem('refresh_token');
  }

  // 标签页切回前台：令牌可能已在后台期间过期，这里补一次检查
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState !== 'visible') {
      if (refreshTimer) {
        clearTimeout(refreshTimer);
        refreshTimer = null;
      }
      return;
    }
    const expiresAt = parseTokenExpiration(accessToken.value);
    if (!expiresAt) return;
    const remaining = expiresAt * 1000 - Date.now();
    if (remaining <= REFRESH_LEAD_SECONDS * 1000) {
      void refreshAccessToken();
    } else {
      scheduleProactiveRefresh();
    }
  });

  return {
    accessToken,
    refreshToken,
    userInfo,
    isAuthenticated,
    userId,
    username,
    avatarColor,
    isGlobalAdmin,
    needsSetup,
    setupStatusLoaded,
    login,
    register,
    loadSetupStatus,
    setupAdmin,
    refreshAccessToken,
    logout,
    fetchUserInfo,
    clearAuth,
  };
});
