import { defineStore } from 'pinia';
import { ref } from 'vue';
import type { SkillOption } from '../types/skill';

const DEFAULT_MODELS = [
  'gpt-4o-mini',
  'gpt-4o',
  'claude-3.5-sonnet',
  'deepseek-v3',
];

export const useAppStore = defineStore(
  'app',
  () => {
    const selectedModel = ref(DEFAULT_MODELS[0]);
    const selectedRerankerModel = ref(DEFAULT_MODELS[0]);
    const activeWorkspaceId = ref<'chat' | 'incident-report'>('chat');
    const availableModels = ref<string[]>([...DEFAULT_MODELS]);
    const processingModes = ref<SkillOption[]>([]);

    return {
      activeWorkspaceId,
      availableModels,
      processingModes,
      selectedModel,
      selectedRerankerModel,
    };
  },
  {
    persist: {
      pick: [
        'selectedModel',
        'selectedRerankerModel',
        'activeWorkspaceId',
        'availableModels',
        'processingModes',
      ],
    },
  },
);
