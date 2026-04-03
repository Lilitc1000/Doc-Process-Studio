import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import ChatSidebar from '../src/components/ChatSidebar.vue';

describe('ChatSidebar', () => {
  it('渲染会话分组并在点击时抛出加载事件', async () => {
    const wrapper = mount(ChatSidebar, {
      props: {
        processingModes: [
          { id: 'document-assistant', displayName: '文档助手' },
          { id: 'resume-review', displayName: '简历筛选' },
        ],
        selectedProcessingMode: 'document-assistant',
        models: ['qwen3:8b'],
        selectedModel: 'qwen3:8b',
        messagesCount: 2,
        sessions: [
          {
            id: 'session-recent',
            title: '最近会话',
            created_at: '2026-04-02T09:00:00Z',
            updated_at: '2026-04-02T09:00:00Z',
            selected_processing_mode: 'document-assistant',
            selected_model: 'qwen3:8b',
          },
          {
            id: 'session-older',
            title: '旧会话',
            created_at: '2026-01-02T09:00:00Z',
            updated_at: '2026-01-02T09:00:00Z',
            selected_processing_mode: 'document-assistant',
            selected_model: 'qwen3:8b',
          },
        ],
        activeSessionId: 'session-recent',
        isLocked: false,
      },
    });

    expect(wrapper.text()).toContain('最近');
    expect(wrapper.text()).toContain('2026年1月');
    expect(wrapper.find('.history-session.active').text()).toContain(
      '最近会话',
    );

    await wrapper.find('.history-session-main').trigger('click');

    expect(wrapper.emitted('load-session')).toEqual([['session-recent']]);
  });
});
