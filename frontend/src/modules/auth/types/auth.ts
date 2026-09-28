export interface RegisterRequest {
  username: string;
  password: string;
}

/** 首次初始化状态：系统中是否存在管理员 */
export interface SetupStatusResponse {
  needsSetup: boolean;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface TokenResponse {
  accessToken: string;
  refreshToken: string;
}

export interface UserInfoResponse {
  userId: string;
  username: string;
  avatarColor: string;
  /**
   * 全局角色：`admin` / `member`。
   *
   * ⚠️ 这是**全局**角色，用于判定能否修改全系统共享设置（如 RAGFlow 凭据）。
   * 与事故报告模块的角色（`GET /api/incident-report/roles/me`）是两套东西。
   */
  role: string;
  createdAt: string;
}

export interface UpdateProfileRequest {
  username?: string;
  avatarColor?: string;
}

export interface ChangePasswordRequest {
  currentPassword: string;
  newPassword: string;
}

export interface RefreshTokenRequest {
  refreshToken: string;
}

export interface LogoutRequest {
  refreshToken: string;
}
