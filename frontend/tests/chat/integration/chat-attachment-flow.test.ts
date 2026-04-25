import { flushPromises, mount } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import ChatPage from '../../../src/views/chat/ChatView.vue';

const streamChatReplyMock = vi.hoisted(() => vi.fn());
const downloadAttachmentMock = vi.hoisted(() => vi.fn());
const fetchAvailableModelsMock = vi.hoisted(() => vi.fn());
const fetchAvailableSkillsMock = vi.hoisted(() => vi.fn());
const fetchSessionSummariesMock = vi.hoisted(() => vi.fn());
const saveSessionMock = vi.hoisted(() => vi.fn());

vi.mock('../../../../src/api/chat-stream', () => ({
  streamChatReply: streamChatReplyMock,
}));

vi.mock('../../../../src/api/chat-attachments', () => ({
  downloadAttachment: downloadAttachmentMock,
}));

vi.mock('../../../../src/api/catalog', () => ({
  fetchAvailableModels: fetchAvailableModelsMock,
  fetchAvailableSkills: fetchAvailableSkillsMock,
}));

vi.mock('../../../../src/api/chat-sessions', () => ({
  fetchSessionSummaries: fetchSessionSummariesMock,
  fetchSessionDetail: vi.fn(),
  renameSession: vi.fn(),
  removeSession: vi.fn(),
  saveSession: saveSessionMock,
}));

vi.mock('../../../../src/api/incident', () => ({
  fetchIncidentFormSchema: vi.fn(),
  fetchIncidentSessionSummaries: vi.fn(),
  createIncidentSession: vi.fn(),
  fetchIncidentSessionDetail: vi.fn(),
  saveIncidentSessionSnapshot: vi.fn(),
  quickGenerateIncidentBody: vi.fn(),
  generateIncidentBodySection: vi.fn(),
  previewIncidentAttachment: vi.fn(),
  renameIncidentSession: vi.fn(),
  removeIncidentSession: vi.fn(),
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
      createdAt: '2026-04-07T00:00:00Z',
      updatedAt: '2026-04-07T00:00:00Z',
      selectedModel: 'qwen3-coder-next:latest',
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
          model: 'qwen3-coder-next:latest',
          message: {
            role: 'assistant',
            content: '文件已生成，可直接下载。',
          },
          done: false,
        });
        return { finishReason: 'stop' };
      },
    );

    const wrapper = mount(ChatPage);
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
