import { fetchAvailableModels, fetchAvailableSkills } from '../../api/catalog';
import { useAppStore } from '../../stores/app';

export const useCatalogLoader = () => {
  const appStore = useAppStore();

  const loadAvailableModels = async () => {
    try {
      const modelNames = await fetchAvailableModels();
      if (modelNames.length === 0) {
        return;
      }

      appStore.availableModels = modelNames;
      if (!modelNames.includes(appStore.selectedModel)) {
        appStore.selectedModel = modelNames[0];
      }
      if (!modelNames.includes(appStore.selectedRerankerModel)) {
        appStore.selectedRerankerModel = appStore.selectedModel;
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
      appStore.processingModes = filteredSkills;
    } catch (error) {
      console.error('加载 skill 列表失败，继续使用前端兜底选项。', error);
    }
  };

  return {
    loadAvailableModels,
    loadAvailableSkills,
  };
};
