import axios from 'axios';
import humps from 'humps';
import { useAuthStore } from '../stores/auth';
import router from '../router';
import { logger } from '../utils/common/logger';

export const apiClient = axios.create({
  baseURL: '/api',
});

apiClient.interceptors.request.use((config) => {
  const authStore = useAuthStore();
  if (authStore.accessToken) {
    config.headers.Authorization = `Bearer ${authStore.accessToken}`;
  }
  if (
    config.data &&
    typeof config.data === 'object' &&
    Object.prototype.toString.call(config.data) === '[object Object]'
  ) {
    config.data = humps.decamelizeKeys(config.data);
  }
  if (config.params && typeof config.params === 'object') {
    config.params = humps.decamelizeKeys(config.params);
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => {
    if (response.data && typeof response.data === 'object') {
      response.data = humps.camelizeKeys(response.data);
    }
    return response;
  },
  async (error) => {
    const status = error.response?.status;
    const requestId = error.response?.headers?.['x-request-id'];
    const method = error.config?.method?.toUpperCase();
    const url = error.config?.url;

    if (status >= 500) {
      logger.error('服务端错误', {
        context: 'api',
        status,
        method,
        url,
        requestId,
        detail: error.response?.data?.detail,
      });
    } else if (status >= 400 && status !== 401) {
      logger.warn('请求失败', {
        context: 'api',
        status,
        method,
        url,
        requestId,
        detail: error.response?.data?.detail,
      });
    }

    const originalRequest = error.config;

    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !originalRequest.url?.includes('/auth/login') &&
      !originalRequest.url?.includes('/auth/refresh') &&
      !originalRequest.url?.includes('/auth/register')
    ) {
      originalRequest._retry = true;

      const authStore = useAuthStore();
      const newToken = await authStore.refreshAccessToken();

      if (newToken) {
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        return apiClient(originalRequest);
      }

      authStore.clearAuth();
      router.push('/login');
    }

    return Promise.reject(error);
  },
);
