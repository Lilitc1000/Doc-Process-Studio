import { defineStore } from 'pinia';
import { ref } from 'vue';
import type { SkillOption } from '../types/skill';

const DEFAULT_MODELS = [
  'qwen3:8b',
  'qwen3:32b',
  'qwen3-coder:30b',
  'llama3.3:70b',
];

export type PageId =
  | 'home'
  | 'chat'
  | 'incident-report'
  | 'knowledge-base'
  | 'settings';

export interface KBProjectOption {
  id: string;
  name: string;
}

export const useAppStore = defineStore(
  'app',
  () => {
    const selectedModel = ref(DEFAULT_MODELS[0]);
    const selectedRerankerModel = ref(DEFAULT_MODELS[0]);
    const activePageId = ref<PageId>('home');
    const availableModels = ref<string[]>([...DEFAULT_MODELS]);
    const processingModes = ref<SkillOption[]>([]);
    const kbProjects = ref<KBProjectOption[]>([]);

    return {
      activePageId,
      availableModels,
      processingModes,
      kbProjects,
      selectedModel,
      selectedRerankerModel,
    };
  },
  {
    persist: {
      // 只持久化"与账号无关的设备级缓存"。
      //
      // `selectedModel` / `selectedRerankerModel` **刻意不在其中**：
      // 它们是"跟着用户走"的偏好，真相源在后端（`user_settings` 表），
      // 由 `useUserSettingsStore` 在应用启动时拉取并回填到本 store。
      // 继续写 localStorage 会导致同一浏览器下多个账号共用一份模型选择，
      // 而且改了服务端也不会生效 —— 典型的双真相源。
      pick: ['activePageId', 'availableModels', 'processingModes'],
    },
  },
);
