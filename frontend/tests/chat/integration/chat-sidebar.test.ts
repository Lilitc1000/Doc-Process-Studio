import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import SessionSidebar from '@shared/components/SessionSidebar.vue';

describe('SessionSidebar', () => {
  it('渲染会话分组并在点击时抛出加载事件', async () => {
    const wrapper = mount(SessionSidebar, {
      props: {
        sessions: [
          {
            id: 'session-recent',
            title: '最近会话',
            createdAt: '2026-04-02T09:00:00Z',
            updatedAt: '2026-04-02T09:00:00Z',
            selectedModel: 'qwen3:8b',
          },
          {
            id: 'session-older',
            title: '旧会话',
            createdAt: '2026-01-02T09:00:00Z',
            updatedAt: '2026-01-02T09:00:00Z',
            selectedModel: 'qwen3:8b',
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
