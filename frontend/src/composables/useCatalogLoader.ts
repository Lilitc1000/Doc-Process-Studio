import type { Ref } from 'vue';
import { fetchAvailableModels, fetchAvailableSkills } from '../api/catalog';
import type { SkillOption } from '../types/skill';

interface UseCatalogLoaderOptions {
  availableModels: Ref<string[]>;
  selectedModel: Ref<string>;
  processingModes: Ref<SkillOption[]>;
  selectedProcessingMode: Ref<string>;
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
    } catch (error) {
      console.error('加载远程模型列表失败，继续使用前端兜底模型列表。', error);
    }
  };

  const loadAvailableSkills = async () => {
    try {
      const { skills: nextSkills, defaultSkillId } =
        await fetchAvailableSkills();
      if (nextSkills.length === 0) {
        return;
      }

      options.processingModes.value = nextSkills;
      const resolvedSkillId = nextSkills.some((skill) => {
        return skill.id === options.selectedProcessingMode.value;
      })
        ? options.selectedProcessingMode.value
        : nextSkills.some((skill) => skill.id === defaultSkillId)
          ? defaultSkillId
          : nextSkills[0].id;

      options.selectedProcessingMode.value = resolvedSkillId;
    } catch (error) {
      console.error('加载 skill 列表失败，继续使用前端兜底选项。', error);
    }
  };

  return {
    loadAvailableModels,
    loadAvailableSkills,
  };
};
