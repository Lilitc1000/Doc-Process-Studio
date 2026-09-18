import { fetchAvailableModels, fetchAvailableSkills } from '../api/catalog';
import { listKBProjectsSimple } from '@modules/knowledge-base';
import { useUserSettingsStore } from '@modules/settings';
import { useAppStore } from '../stores/app';
import { logger } from '../utils/logger';

/** 只在候选列表里采用保存值，避免把一个已下线的模型名塞回去。 */
const pickAvailable = (
  candidate: string | null,
  available: string[],
): string | null =>
  candidate && available.includes(candidate) ? candidate : null;

export const useCatalogLoader = () => {
  const appStore = useAppStore();
  const userSettingsStore = useUserSettingsStore();

  const loadAvailableModels = async () => {
    try {
      const modelNames = await fetchAvailableModels();
      if (modelNames.length === 0) {
        return;
      }

      appStore.availableModels = modelNames;

      // 模型选择是"跟用户走"的偏好，真相源在后端 `user_settings`。
      // 这里先确保偏好已加载，再优先采用它；只有在偏好缺失或已不在可用列表中时，
      // 才回落到第一个可用模型。
      if (!userSettingsStore.loaded) {
        await userSettingsStore.loadSettings();
      }
      const saved = userSettingsStore.preferences.models;
      const preferred =
        pickAvailable(saved.selected, modelNames) ?? modelNames[0];
      const preferredReranker =
        pickAvailable(saved.reranker, modelNames) ?? preferred;

      appStore.selectedModel = preferred;
      appStore.selectedRerankerModel = preferredReranker;
    } catch (error) {
      logger.error('加载远程模型列表失败，继续使用前端兜底模型列表。', {
        context: 'useCatalogLoader',
        error,
      });
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
      logger.error('加载 skill 列表失败，继续使用前端兜底选项。', {
        context: 'useCatalogLoader',
        error,
      });
    }
  };

  const loadKBProjects = async () => {
    try {
      const projects = await listKBProjectsSimple();
      appStore.kbProjects = projects.map((p) => ({ id: p.id, name: p.name }));
    } catch (error) {
      logger.error('加载知识库项目列表失败。', {
        context: 'useCatalogLoader',
        error,
      });
    }
  };

  return {
    loadAvailableModels,
    loadAvailableSkills,
    loadKBProjects,
  };
};
