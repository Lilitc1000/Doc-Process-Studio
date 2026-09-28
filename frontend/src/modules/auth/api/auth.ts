import { apiClient } from '@shared/api/request';
import type {
  ChangePasswordRequest,
  LoginRequest,
  LogoutRequest,
  RefreshTokenRequest,
  RegisterRequest,
  SetupStatusResponse,
  TokenResponse,
  UpdateProfileRequest,
  UserInfoResponse,
} from '../types/auth';

/**
 * 系统是否还需要创建首个管理员（公开端点）。
 *
 * 未认证时由路由守卫惰性调用一次：`needsSetup=true` 会把所有路由
 * 引导到 `/setup`，创建完管理员再回登录页。
 */
export async function fetchSetupStatus(): Promise<boolean> {
  const response =
    await apiClient.get<SetupStatusResponse>('/auth/setup-status');
  return response.data.needsSetup;
}

/** 创建首个管理员（公开端点；系统已有管理员时后端返回 409）。 */
export async function setupAdmin(data: RegisterRequest) {
  const response = await apiClient.post('/auth/setup-admin', data);
  return response.data;
}

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
