import axios from 'axios';
import humps from 'humps';
import { useAuthStore } from '../stores/auth';
import router from '../router';

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
