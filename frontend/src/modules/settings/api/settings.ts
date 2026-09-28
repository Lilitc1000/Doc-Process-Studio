import { apiClient } from '@shared/api/request';
import type {
  RagflowConnectionTestResponse,
  RagflowDatasetListResponse,
  RagflowSettings,
  SettingsOverviewResponse,
  UpdatePreferencesRequest,
  UpdateRagflowRequest,
  UserPreferences,
  SystemSecret,
  SystemSecretList,
} from '../types/settings';

/** 拉取设置页所需的全部内容（个人偏好 + 系统 RAGFlow 设置视图）。 */
export const fetchSettings = async (): Promise<SettingsOverviewResponse> => {
  const response = await apiClient.get<SettingsOverviewResponse>('/settings');
  return response.data;
};

/** 部分更新当前用户的偏好（只改请求里出现的段落）。 */
export const updateUserPreferences = async (
  payload: UpdatePreferencesRequest,
): Promise<UserPreferences> => {
  const response = await apiClient.put<UserPreferences>(
    '/settings/preferences',
    payload,
  );
  return response.data;
};

/**
 * 更新系统级 RAGFlow 非密钥设置（**仅管理员**，非管理员会拿到 403）。
 *
 * 密钥（API Key）统一走通用系统密钥端点 `setSystemSecret` / `clearSystemSecret`，
 * 不在本请求里出现，避免两套密钥写入路径并存。
 */
export const updateRagflowSettings = async (
  payload: UpdateRagflowRequest,
): Promise<RagflowSettings> => {
  const response = await apiClient.put<RagflowSettings>(
    '/settings/ragflow',
    payload,
  );
  return response.data;
};

/**
 * 用**已保存的**服务器侧配置做一次连通性自检（**仅管理员**）。
 *
 * 刻意不接收草稿值：自检的应该是"实际生效的配置"，否则会出现
 * "测试通过但保存的是别的东西"这种误导。想验证新密钥请先保存再测试。
 */
/**
 * 拉取当前连接下可访问的知识库列表（**仅管理员**）。
 *
 * 刻意不走缓存：换了 Base URL 或密钥之后可访问的集合会完全不同 ——
 * 所以保存连接配置后要重新调用，让选择项跟着变。
 */
export const fetchRagflowDatasets =
  async (): Promise<RagflowDatasetListResponse> => {
    const response = await apiClient.get<RagflowDatasetListResponse>(
      '/settings/ragflow/datasets',
    );
    return response.data;
  };

export const testRagflowConnection =
  async (): Promise<RagflowConnectionTestResponse> => {
    const response = await apiClient.post<RagflowConnectionTestResponse>(
      '/settings/ragflow/test',
    );
    return response.data;
  };

/** 拉取所有已注册的系统级密钥槽位及其配置状态（**仅管理员**）。 */
export const listSystemSecrets = async (): Promise<SystemSecretList> => {
  const response = await apiClient.get<SystemSecretList>('/settings/secrets');
  return response.data;
};

/** 写入/覆盖一个系统级密钥（**仅管理员**）。明文只用于本次请求，服务端加密入库。 */
export const setSystemSecret = async (
  key: string,
  value: string,
): Promise<SystemSecret> => {
  const response = await apiClient.put<SystemSecret>(
    `/settings/secrets/${key}`,
    { value },
  );
  return response.data;
};

/** 清除一个系统级密钥（**仅管理员**）。 */
export const clearSystemSecret = async (key: string): Promise<SystemSecret> => {
  const response = await apiClient.delete<SystemSecret>(
    `/settings/secrets/${key}`,
  );
  return response.data;
};
