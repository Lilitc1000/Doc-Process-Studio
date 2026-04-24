import axios from 'axios';
import humps from 'humps';

export const apiClient = axios.create({
  baseURL: '/api',
});

apiClient.interceptors.request.use((config) => {
  if (config.data && typeof config.data === 'object') {
    config.data = humps.decamelizeKeys(config.data);
  }
  if (config.params && typeof config.params === 'object') {
    config.params = humps.decamelizeKeys(config.params);
  }
  return config;
});

apiClient.interceptors.response.use((response) => {
  if (response.data && typeof response.data === 'object') {
    response.data = humps.camelizeKeys(response.data);
  }
  return response;
});
