import { flushPromises, mount } from '@vue/test-utils';
import { afterEach, describe, expect, it, vi } from 'vitest';
import ChatLayout from '../src/components/ChatLayout.vue';

const streamChatReplyMock = vi.hoisted(() => vi.fn());
const fetchAgentTraceReplayMock = vi.hoisted(() => vi.fn());
const downloadAttachmentMock = vi.hoisted(() => vi.fn());
const fetchAvailableModelsMock = vi.hoisted(() => vi.fn());
const fetchAvailableSkillsMock = vi.hoisted(() => vi.fn());
const fetchSessionSummariesMock = vi.hoisted(() => vi.fn());
const saveSessionMock = vi.hoisted(() => vi.fn());

vi.mock('../src/api/chat', () => ({
  streamChatReply: streamChatReplyMock,
}));

vi.mock('../src/api/trace', () => ({
  fetchAgentTraceReplay: fetchAgentTraceReplayMock,
}));

vi.mock('../src/api/attachments', () => ({
  downloadAttachment: downloadAttachmentMock,
}));

vi.mock('../src/api/catalog', () => ({
  fallbackModels: ['qwen3-coder-next:latest'],
  fetchAvailableModels: fetchAvailableModelsMock,
  fetchAvailableSkills: fetchAvailableSkillsMock,
}));

vi.mock('../src/api/sessions', () => ({
  fetchSessionSummaries: fetchSessionSummariesMock,
  fetchSessionDetail: vi.fn(),
  renameSession: vi.fn(),
  removeSession: vi.fn(),
  saveSession: saveSessionMock,
}));

afterEach(() => {
  document.body.innerHTML = '';
});

describe('chat trace flow', () => {
  it('收到 trace 事件后可打开链路回放详情', async () => {
    fetchAvailableModelsMock.mockResolvedValue(['qwen3-coder-next:latest']);
    fetchAvailableSkillsMock.mockResolvedValue({ skills: [] });
    fetchSessionSummariesMock.mockResolvedValue([]);
    saveSessionMock.mockResolvedValue({
      id: 'conversation-1',
      title: '测试会话',
      created_at: '2026-04-07T00:00:00Z',
      updated_at: '2026-04-07T00:00:00Z',
      selected_model: 'qwen3-coder-next:latest',
      selected_reranker_model: 'qwen3-coder-next:latest',
    });

    fetchAgentTraceReplayMock.mockResolvedValue({
      trace_id: 'trace-abc-123',
      payload: {
        trace_id: 'trace-abc-123',
        conversation_id: 'conversation-1',
        model: 'qwen3-coder-next:latest',
        reranker_model: 'qwen3-coder-next:latest',
        rounds: [{ round: 1, tool_calls_consumed: 1 }],
        final: { done_reason: 'stop' },
      },
    });

    streamChatReplyMock.mockImplementation(
      async (_requestSnapshot, _signal, onEvent) => {
        onEvent({
          type: 'trace',
          phase: 'start',
          trace_id: 'trace-abc-123',
        });
        onEvent({
          model: 'qwen3-coder-next:latest',
          message: {
            role: 'assistant',
            content: '这是一次可追踪的回复。',
          },
          done: false,
        });
        return { finishReason: 'stop' };
      },
    );

    const wrapper = mount(ChatLayout, {
      attachTo: document.body,
    });
    await flushPromises();

    const textarea = wrapper.find('.chat-input textarea');
    await textarea.setValue('请给我一个可追踪回复');
    await textarea.trigger('input');
    await textarea.trigger('keydown', { key: 'Enter', shiftKey: false });
    await flushPromises();

    const traceButton = wrapper.find(
      '.chat-message.role-assistant button[title="查看链路"]',
    );
    expect(traceButton.exists()).toBe(true);

    await traceButton.trigger('click');
    await flushPromises();

    expect(fetchAgentTraceReplayMock).toHaveBeenCalledWith('trace-abc-123');
    expect(document.body.textContent).toContain('链路回放详情');
    expect(document.body.textContent).toContain('trace-abc-123');
  });
});
