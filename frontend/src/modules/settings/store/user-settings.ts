import { defineStore } from 'pinia';
import { ref } from 'vue';
import { logger } from '@shared/utils/logger';
import {
  clearRagflowApiKey,
  fetchSettings,
  testRagflowConnection,
  updateRagflowSettings,
  updateUserPreferences,
} from '../api/settings';
import type {
  ModelPreferences,
  RagflowConnectionTestResponse,
  RagflowSettings,
  UpdateRagflowRequest,
  UserPreferences,
} from '../types/settings';

const EMPTY_MODELS: ModelPreferences = { selected: null, reranker: null };

/**
 * 用户设置 store。
 *
 * **刻意不做 persist**：
 *
 * - 真相源在后端（`user_settings` / `system_*` 表），本地缓存只会制造"改了没生效"的困惑；
 * - 即便接口永不返回明文，把凭据相关信息写进 localStorage 也是没必要的暴露面。
 *
 * 模型选择仍写回 `useAppStore.selectedModel` —— 那是运行期状态（聊天、报告生成都要读），
 * 本 store 只负责"从服务端取/存"。
 */
export const useUserSettingsStore = defineStore('user-settings', () => {
  const preferences = ref<UserPreferences>({ models: { ...EMPTY_MODELS } });
  const ragflow = ref<RagflowSettings | null>(null);

  const loading = ref(false);
  const saving = ref(false);
  const testing = ref(false);
  const loaded = ref(false);
  const loadError = ref<string | null>(null);
  const lastTestResult = ref<RagflowConnectionTestResponse | null>(null);

  /**
   * 同一时刻只允许一个 `fetchSettings` 在飞，且加载成功后不再重复拉取。
   *
   * 为什么必须去重：设置页上有多个调用方会触发加载 —— `DefaultLayout.onMounted`、
   * `SettingsView.onMounted`、以及 `useCatalogLoader.loadAvailableModels`（它要拿模型偏好），
   * 三者会在页面挂载的瞬间几乎同时发起请求。若不去重，**后返回的那个响应会把
   * `ragflow` 整个替换掉**，进而触发页面把用户正在编辑的草稿重置回服务端值 ——
   * 表现就是"我刚点了开关 / 刚输入了密钥，它自己变回去了"。
   */
  let inflight: Promise<void> | null = null;

  const loadSettings = async (force = false): Promise<void> => {
    if (!force && loaded.value) return;
    if (inflight) return inflight;

    inflight = (async () => {
      loading.value = true;
      loadError.value = null;
      try {
        const overview = await fetchSettings();
        preferences.value = overview.preferences;
        ragflow.value = overview.ragflow;
        loaded.value = true;
      } catch (error) {
        loadError.value = '加载设置失败，请稍后重试。';
        logger.error('加载用户设置失败', { context: 'user-settings', error });
      } finally {
        loading.value = false;
        inflight = null;
      }
    })();

    return inflight;
  };

  /** 保存模型偏好；只提交本次真正变化的字段。 */
  const saveModelPreferences = async (
    patch: Partial<ModelPreferences>,
  ): Promise<void> => {
    saving.value = true;
    try {
      const next = await updateUserPreferences({ models: patch });
      preferences.value = next;
    } catch (error) {
      logger.error('保存模型偏好失败', { context: 'user-settings', error });
      throw error;
    } finally {
      saving.value = false;
    }
  };

  /**
   * 保存系统级 RAGFlow 设置（仅管理员）。
   *
   * 调用方必须遵守 `apiKey` 的四态语义：**空串等于"不变"**，
   * 只有用户真的输入了新密钥才把明文放进来。
   */
  const saveRagflow = async (payload: UpdateRagflowRequest): Promise<void> => {
    saving.value = true;
    try {
      ragflow.value = await updateRagflowSettings(payload);
    } catch (error) {
      logger.error('保存 RAGFlow 设置失败', {
        context: 'user-settings',
        error,
      });
      throw error;
    } finally {
      saving.value = false;
    }
  };

  /** 用已保存的配置做连通性自检；结果留在 store 里供页面展示。 */
  const runConnectionTest =
    async (): Promise<RagflowConnectionTestResponse> => {
      testing.value = true;
      try {
        const result = await testRagflowConnection();
        lastTestResult.value = result;
        return result;
      } catch (error) {
        logger.error('RAGFlow 连通性自检失败', {
          context: 'user-settings',
          error,
        });
        throw error;
      } finally {
        testing.value = false;
      }
    };

  const removeApiKey = async (): Promise<void> => {
    saving.value = true;
    try {
      ragflow.value = await clearRagflowApiKey();
      lastTestResult.value = null;
    } catch (error) {
      logger.error('清除 RAGFlow 密钥失败', {
        context: 'user-settings',
        error,
      });
      throw error;
    } finally {
      saving.value = false;
    }
  };

  return {
    preferences,
    ragflow,
    loading,
    saving,
    testing,
    loaded,
    loadError,
    lastTestResult,
    loadSettings,
    saveModelPreferences,
    saveRagflow,
    runConnectionTest,
    removeApiKey,
  };
});
