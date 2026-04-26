import { describe, expect, it, beforeEach } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { useAppStore } from '../../../src/stores/app';

describe('useAppStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('初始状态有默认模型', () => {
    const store = useAppStore();
    expect(store.selectedModel).toBe('gpt-4o-mini');
    expect(store.selectedRerankerModel).toBe('gpt-4o-mini');
  });

  it('初始 activePageId 为 home', () => {
    const store = useAppStore();
    expect(store.activePageId).toBe('home');
  });

  it('初始 availableModels 包含默认模型', () => {
    const store = useAppStore();
    expect(store.availableModels).toContain('gpt-4o-mini');
    expect(store.availableModels).toContain('gpt-4o');
    expect(store.availableModels.length).toBeGreaterThanOrEqual(4);
  });

  it('初始 processingModes 为空', () => {
    const store = useAppStore();
    expect(store.processingModes).toEqual([]);
  });

  it('可以修改 selectedModel', () => {
    const store = useAppStore();
    store.selectedModel = 'deepseek-v3';
    expect(store.selectedModel).toBe('deepseek-v3');
  });

  it('可以修改 selectedRerankerModel', () => {
    const store = useAppStore();
    store.selectedRerankerModel = 'claude-3.5-sonnet';
    expect(store.selectedRerankerModel).toBe('claude-3.5-sonnet');
  });

  it('可以修改 activePageId', () => {
    const store = useAppStore();
    store.activePageId = 'chat';
    expect(store.activePageId).toBe('chat');
  });

  it('可以修改 availableModels', () => {
    const store = useAppStore();
    store.availableModels = ['model-a', 'model-b'];
    expect(store.availableModels).toEqual(['model-a', 'model-b']);
  });

  it('可以修改 processingModes', () => {
    const store = useAppStore();
    store.processingModes = [{ id: 'skill-1', displayName: '技能1' }];
    expect(store.processingModes).toHaveLength(1);
    expect(store.processingModes[0].id).toBe('skill-1');
  });
});
