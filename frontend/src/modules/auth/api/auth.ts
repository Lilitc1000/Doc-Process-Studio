import { apiClient } from '@shared/api/request';
import type {
  ChangePasswordRequest,
  LoginRequest,
  LogoutRequest,
  RefreshTokenRequest,
  RegisterRequest,
  TokenResponse,
  UpdateProfileRequest,
  UserInfoResponse,
} from '../types/auth';

export async function registerUser(data: RegisterRequest) {
  const response = await apiClient.post('/auth/register', data);
  return response.data;
}

export async function loginUser(data: LoginRequest): Promise<TokenResponse> {
  const params = new URLSearchParams();
  params.append('username', data.username);
  params.append('password', data.password);
  const response = await apiClient.post('/auth/login', params, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    transformRequest: [(d) => d],
  });
  return response.data;
}

export async function refreshToken(
  data: RefreshTokenRequest,
): Promise<TokenResponse> {
  const response = await apiClient.post('/auth/refresh', data);
  return response.data;
}

export async function getCurrentUser(): Promise<UserInfoResponse> {
  const response = await apiClient.get('/auth/me');
  return response.data;
}

export async function updateProfile(
  data: UpdateProfileRequest,
): Promise<UserInfoResponse> {
  const response = await apiClient.put('/auth/me', data);
  return response.data;
}

export async function changePassword(data: ChangePasswordRequest) {
  const response = await apiClient.put('/auth/password', data);
  return response.data;
}

export async function logoutUser(data: LogoutRequest) {
  const response = await apiClient.post('/auth/logout', data);
  return response.data;
}
