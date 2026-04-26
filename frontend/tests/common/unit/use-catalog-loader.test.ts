import { describe, expect, it, vi, beforeEach } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { useCatalogLoader } from '../../../src/composables/business/useCatalogLoader';
import * as catalogApi from '../../../src/api/catalog';

vi.mock('../../../src/api/catalog', () => ({
  fetchAvailableModels: vi.fn(),
  fetchAvailableSkills: vi.fn(),
  fallbackModels: ['gpt-4o-mini'],
}));

describe('useCatalogLoader', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setActivePinia(createPinia());
  });

  describe('loadAvailableModels', () => {
    it('成功加载模型列表', async () => {
      const mockFetch = catalogApi.fetchAvailableModels as ReturnType<
        typeof vi.fn
      >;
      mockFetch.mockResolvedValue(['model-a', 'model-b', 'model-c']);

      const { loadAvailableModels } = useCatalogLoader();
      await loadAvailableModels();

      const { useAppStore } = await import('../../../src/stores/app');
      const appStore = useAppStore();
      expect(appStore.availableModels).toEqual([
        'model-a',
        'model-b',
        'model-c',
      ]);
    });

    it('空模型列表不更新 store', async () => {
      const mockFetch = catalogApi.fetchAvailableModels as ReturnType<
        typeof vi.fn
      >;
      mockFetch.mockResolvedValue([]);

      const { loadAvailableModels } = useCatalogLoader();
      await loadAvailableModels();

      const { useAppStore } = await import('../../../src/stores/app');
      const appStore = useAppStore();
      expect(appStore.availableModels).not.toEqual([]);
    });

    it('当前选中模型不在列表中时切换到第一个', async () => {
      const mockFetch = catalogApi.fetchAvailableModels as ReturnType<
        typeof vi.fn
      >;
      mockFetch.mockResolvedValue(['model-x', 'model-y']);

      const { loadAvailableModels } = useCatalogLoader();
      await loadAvailableModels();

      const { useAppStore } = await import('../../../src/stores/app');
      const appStore = useAppStore();
      expect(appStore.selectedModel).toBe('model-x');
    });

    it('请求失败不抛出异常', async () => {
      const mockFetch = catalogApi.fetchAvailableModels as ReturnType<
        typeof vi.fn
      >;
      mockFetch.mockRejectedValue(new Error('Network error'));

      const { loadAvailableModels } = useCatalogLoader();
      await expect(loadAvailableModels()).resolves.toBeUndefined();
    });
  });

  describe('loadAvailableSkills', () => {
    it('成功加载技能列表', async () => {
      const mockFetch = catalogApi.fetchAvailableSkills as ReturnType<
        typeof vi.fn
      >;
      mockFetch.mockResolvedValue({
        skills: [
          { id: 'skill-1', displayName: '技能1', skillType: 'chat' },
          { id: 'skill-2', displayName: '技能2', skillType: 'chat' },
        ],
      });

      const { loadAvailableSkills } = useCatalogLoader();
      await loadAvailableSkills();

      const { useAppStore } = await import('../../../src/stores/app');
      const appStore = useAppStore();
      expect(appStore.processingModes).toHaveLength(2);
    });

    it('过滤掉 document-assistant 和非 chat 类型', async () => {
      const mockFetch = catalogApi.fetchAvailableSkills as ReturnType<
        typeof vi.fn
      >;
      mockFetch.mockResolvedValue({
        skills: [
          {
            id: 'document-assistant',
            displayName: '文档助手',
            skillType: 'chat',
          },
          { id: 'skill-1', displayName: '技能1', skillType: 'chat' },
          { id: 'skill-2', displayName: '技能2', skillType: 'incident_report' },
        ],
      });

      const { loadAvailableSkills } = useCatalogLoader();
      await loadAvailableSkills();

      const { useAppStore } = await import('../../../src/stores/app');
      const appStore = useAppStore();
      expect(appStore.processingModes).toHaveLength(1);
      expect(appStore.processingModes[0].id).toBe('skill-1');
    });

    it('空技能列表不更新 store', async () => {
      const mockFetch = catalogApi.fetchAvailableSkills as ReturnType<
        typeof vi.fn
      >;
      mockFetch.mockResolvedValue({ skills: [] });

      const { loadAvailableSkills } = useCatalogLoader();
      await loadAvailableSkills();

      const { useAppStore } = await import('../../../src/stores/app');
      const appStore = useAppStore();
      expect(appStore.processingModes).toEqual([]);
    });

    it('请求失败不抛出异常', async () => {
      const mockFetch = catalogApi.fetchAvailableSkills as ReturnType<
        typeof vi.fn
      >;
      mockFetch.mockRejectedValue(new Error('Network error'));

      const { loadAvailableSkills } = useCatalogLoader();
      await expect(loadAvailableSkills()).resolves.toBeUndefined();
    });
  });
});
