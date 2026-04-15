import type { Ref } from 'vue';
import { fetchAvailableModels, fetchAvailableSkills } from '../api/catalog';
import type { SkillOption } from '../types/skill';

interface UseCatalogLoaderOptions {
  availableModels: Ref<string[]>;
  selectedModel: Ref<string>;
  selectedRerankerModel: Ref<string>;
  processingModes: Ref<SkillOption[]>;
}

export const useCatalogLoader = (options: UseCatalogLoaderOptions) => {
  const loadAvailableModels = async () => {
    try {
      const modelNames = await fetchAvailableModels();
      if (modelNames.length === 0) {
        return;
      }

      options.availableModels.value = modelNames;
      if (!modelNames.includes(options.selectedModel.value)) {
        options.selectedModel.value = modelNames[0];
      }
      if (!modelNames.includes(options.selectedRerankerModel.value)) {
        options.selectedRerankerModel.value = options.selectedModel.value;
      }
    } catch (error) {
      console.error('加载远程模型列表失败，继续使用前端兜底模型列表。', error);
    }
  };

  const loadAvailableSkills = async () => {
    try {
      const { skills: nextSkills } = await fetchAvailableSkills();
      if (nextSkills.length === 0) {
        return;
      }
      const filteredSkills = nextSkills.filter((skill) => {
        return skill.id !== 'document-assistant' && skill.skillType === 'chat';
      });
      options.processingModes.value = filteredSkills;
    } catch (error) {
      console.error('加载 skill 列表失败，继续使用前端兜底选项。', error);
    }
  };

  return {
    loadAvailableModels,
    loadAvailableSkills,
  };
};
