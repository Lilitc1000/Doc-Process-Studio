import { flushPromises, mount } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import ChatLayout from '../src/components/ChatLayout.vue';

const streamChatReplyMock = vi.hoisted(() => vi.fn());
const downloadAttachmentMock = vi.hoisted(() => vi.fn());
const fetchAvailableModelsMock = vi.hoisted(() => vi.fn());
const fetchAvailableSkillsMock = vi.hoisted(() => vi.fn());
const fetchSessionSummariesMock = vi.hoisted(() => vi.fn());
const saveSessionMock = vi.hoisted(() => vi.fn());

vi.mock('../src/api/chat', () => ({
  streamChatReply: streamChatReplyMock,
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

describe('chat attachment flow', () => {
  it('渲染附件文件框并触发下载', async () => {
    fetchAvailableModelsMock.mockResolvedValue(['qwen3-coder-next:latest']);
    fetchAvailableSkillsMock.mockResolvedValue({
      skills: [
        {
          id: 'project-architecture-docx',
          displayName: '项目架构文档',
        },
      ],
    });
    fetchSessionSummariesMock.mockResolvedValue([]);
    saveSessionMock.mockResolvedValue({
      id: 'conversation-1',
      title: '测试会话',
      created_at: '2026-04-07T00:00:00Z',
      updated_at: '2026-04-07T00:00:00Z',
      selected_model: 'qwen3-coder-next:latest',
    });

    streamChatReplyMock.mockImplementation(
      async (requestSnapshot, _signal, onEvent) => {
        expect(requestSnapshot.attachmentIds).toEqual([]);
        onEvent({
          type: 'attachment',
          attachment: {
            attachmentId: 'attachment-1',
            name: '系统架构与设计文档.docx',
            source: 'generated',
            sizeLabel: '24 KB',
            downloadUrl: '/api/attachments/attachment-1/download',
            mimeType:
              'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            expiresAt: '2026-04-14T00:00:00Z',
          },
        });
        onEvent({
          type: 'delta',
          content: '文件已生成，可直接下载。',
        });
      },
    );

    const wrapper = mount(ChatLayout);
    await flushPromises();

    const textarea = wrapper.find('.chat-input textarea');
    await textarea.setValue('请生成系统架构文档');
    await textarea.trigger('input');
    await textarea.trigger('keydown', { key: 'Enter', shiftKey: false });
    await flushPromises();

    expect(wrapper.text()).toContain('文件已生成，可直接下载。');

    const attachmentButton = wrapper.find(
      '.chat-message.role-assistant .message-file-item.is-downloadable',
    );
    expect(attachmentButton.exists()).toBe(true);
    expect(attachmentButton.text()).toContain('系统架构与设计文档.docx');

    await attachmentButton.trigger('click');
    expect(downloadAttachmentMock).toHaveBeenCalledWith('attachment-1');
  });
});
