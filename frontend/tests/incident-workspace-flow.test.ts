import { flushPromises, mount } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import ChatLayout from '../src/components/ChatLayout.vue';

const streamChatReplyMock = vi.hoisted(() => vi.fn());
const downloadAttachmentMock = vi.hoisted(() => vi.fn());
const fetchAvailableModelsMock = vi.hoisted(() => vi.fn());
const fetchAvailableSkillsMock = vi.hoisted(() => vi.fn());
const fetchSessionSummariesMock = vi.hoisted(() => vi.fn());
const saveSessionMock = vi.hoisted(() => vi.fn());
const fetchIncidentFormSchemaMock = vi.hoisted(() => vi.fn());
const fetchIncidentSessionSummariesMock = vi.hoisted(() => vi.fn());
const createIncidentSessionMock = vi.hoisted(() => vi.fn());
const fetchIncidentSessionDetailMock = vi.hoisted(() => vi.fn());
const generateIncidentAttachmentMock = vi.hoisted(() => vi.fn());
const fetchAgentTraceReplayMock = vi.hoisted(() => vi.fn());

vi.mock('../src/api/chat', () => ({
  streamChatReply: streamChatReplyMock,
}));

vi.mock('../src/api/attachments', () => ({
  downloadAttachment: downloadAttachmentMock,
}));

vi.mock('../src/api/catalog', () => ({
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

vi.mock('../src/api/incident-report', () => ({
  fetchIncidentFormSchema: fetchIncidentFormSchemaMock,
  fetchIncidentSessionSummaries: fetchIncidentSessionSummariesMock,
  createIncidentSession: createIncidentSessionMock,
  fetchIncidentSessionDetail: fetchIncidentSessionDetailMock,
  saveIncidentSessionSnapshot: vi.fn(),
  generateIncidentAttachment: generateIncidentAttachmentMock,
  renameIncidentSession: vi.fn(),
  removeIncidentSession: vi.fn(),
}));

vi.mock('../src/api/trace', () => ({
  fetchAgentTraceReplay: fetchAgentTraceReplayMock,
}));

describe('incident workspace flow', () => {
  it('可在事故报告专区开始会话并生成附件', async () => {
    fetchAvailableModelsMock.mockResolvedValue(['qwen3-coder-next:latest']);
    fetchAvailableSkillsMock.mockResolvedValue({ skills: [] });
    fetchSessionSummariesMock.mockResolvedValue([]);
    fetchIncidentSessionSummariesMock.mockResolvedValue([]);
    fetchIncidentFormSchemaMock.mockResolvedValue({
      intro_message: '欢迎来到事故报告向导',
      steps: [
        {
          id: 'incident_type',
          title: 'Step 1/1 事故类型',
          prompt: '请选择事故类型',
          field_path: 'detailed_description',
          kind: 'single_select',
          options: [{ value: 'A', label: 'A' }],
          allow_custom: true,
          required: true,
          placeholder: '',
        },
      ],
    });

    createIncidentSessionMock.mockResolvedValue({
      id: 'incident-session-1',
      title: '事故报告-2026/04/14 12:30',
      status: 'draft',
      created_at: '2026-04-14T12:30:00Z',
      updated_at: '2026-04-14T12:30:00Z',
    });

    fetchIncidentSessionDetailMock.mockResolvedValue({
      id: 'incident-session-1',
      title: '事故报告-2026/04/14 12:30',
      status: 'draft',
      created_at: '2026-04-14T12:30:00Z',
      updated_at: '2026-04-14T12:30:00Z',
      snapshot: {
        form_answers: {},
        report_data: null,
        generated_attachment: null,
        generated_trace_id: '',
        generated_at: null,
        is_locked: false,
        fallback_used: false,
        polish_error: null,
      },
    });

    generateIncidentAttachmentMock.mockResolvedValue({
      session: {
        id: 'incident-session-1',
        title: '事故报告-2026/04/14 12:30',
        status: 'generated',
        created_at: '2026-04-14T12:30:00Z',
        updated_at: '2026-04-14T12:40:00Z',
      },
      snapshot: {
        form_answers: {
          incident_type: { value: 'A', custom_value: '' },
        },
        report_data: {},
        generated_attachment: {
          attachment_id: 'incident-attachment-1',
          name: 'incident-report.docx',
          source: 'generated',
          size_label: '20 KB',
          download_url: '/api/attachments/incident-attachment-1/download',
          mime_type:
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
          expires_at: '2026-04-15T00:00:00Z',
        },
        generated_trace_id: 'trace-incident-1',
        generated_at: '2026-04-14T12:40:00Z',
        is_locked: true,
        fallback_used: false,
        polish_error: null,
      },
      trace_id: 'trace-incident-1',
    });
    fetchAgentTraceReplayMock.mockResolvedValue({
      payload: {
        events: [],
      },
    });

    const wrapper = mount(ChatLayout);
    await flushPromises();

    const incidentTab = wrapper
      .findAll('.workspace-item')
      .find((node) => node.text() === '事故报告');
    expect(incidentTab).toBeTruthy();
    await incidentTab!.trigger('click');
    await flushPromises();

    expect(wrapper.text()).toContain('事故报告助手');

    const startButton = wrapper.find('.incident-primary-btn');
    await startButton.trigger('click');
    await flushPromises();

    expect(createIncidentSessionMock).toHaveBeenCalledTimes(1);
    expect(fetchIncidentSessionDetailMock).toHaveBeenCalledWith(
      'incident-session-1',
    );

    const selectTrigger = wrapper.find('.incident-select-trigger');
    await selectTrigger.trigger('click');
    await flushPromises();

    const optionA = wrapper
      .findAll('.incident-select-option')
      .find((node) => node.text().trim() === 'A');
    expect(optionA).toBeTruthy();
    await optionA!.trigger('click');
    await flushPromises();

    const generateButton = wrapper.find(
      '.incident-form-actions .incident-primary-btn',
    );
    await generateButton.trigger('click');
    await flushPromises();

    expect(generateIncidentAttachmentMock).toHaveBeenCalledWith(
      'incident-session-1',
      {
        model: 'qwen3-coder-next:latest',
        reranker_model: 'qwen3-coder-next:latest',
      },
      expect.objectContaining({
        signal: expect.any(Object),
      }),
    );
    expect(wrapper.text()).toContain('下载附件');
  });
});
