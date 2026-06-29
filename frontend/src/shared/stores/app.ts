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
      pick: [
        'selectedModel',
        'selectedRerankerModel',
        'activePageId',
        'availableModels',
        'processingModes',
      ],
    },
  },
);
