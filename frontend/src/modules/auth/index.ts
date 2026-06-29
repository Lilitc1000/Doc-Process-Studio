// auth 模块桶文件：统一导出认证域公共 API

// --- Store ---
export { useAuthStore } from './store/auth';

// --- API ---
export {
  registerUser,
  loginUser,
  refreshToken,
  getCurrentUser,
  updateProfile,
  changePassword,
  logoutUser,
} from './api/auth';

// --- Types ---
export type {
  RegisterRequest,
  LoginRequest,
  TokenResponse,
  UserInfoResponse,
  UpdateProfileRequest,
  ChangePasswordRequest,
  RefreshTokenRequest,
  LogoutRequest,
} from './types/auth';
