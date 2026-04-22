import { flushPromises, mount } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import IncidentReportPage from '../src/pages/IncidentReportPage.vue';

const fetchAvailableModelsMock = vi.hoisted(() => vi.fn());
const fetchIncidentFormSchemaMock = vi.hoisted(() => vi.fn());
const fetchIncidentSessionSummariesMock = vi.hoisted(() => vi.fn());
const createIncidentSessionMock = vi.hoisted(() => vi.fn());
const fetchIncidentSessionDetailMock = vi.hoisted(() => vi.fn());
const quickGenerateIncidentBodyMock = vi.hoisted(() => vi.fn());
const generateIncidentBodySectionMock = vi.hoisted(() => vi.fn());
const previewIncidentAttachmentMock = vi.hoisted(() => vi.fn());

vi.mock('../src/api/chat', () => ({
  streamChatReply: vi.fn(),
}));

vi.mock('../src/api/attachments', () => ({
  downloadAttachment: vi.fn(),
}));

vi.mock('../src/api/catalog', () => ({
  fetchAvailableModels: fetchAvailableModelsMock,
  fetchAvailableSkills: vi.fn(),
}));

vi.mock('../src/api/sessions', () => ({
  fetchSessionSummaries: vi.fn(),
  fetchSessionDetail: vi.fn(),
  renameSession: vi.fn(),
  removeSession: vi.fn(),
  saveSession: vi.fn(),
}));

vi.mock('../src/api/incident-report', () => ({
  fetchIncidentFormSchema: fetchIncidentFormSchemaMock,
  fetchIncidentSessionSummaries: fetchIncidentSessionSummariesMock,
  createIncidentSession: createIncidentSessionMock,
  fetchIncidentSessionDetail: fetchIncidentSessionDetailMock,
  saveIncidentSessionSnapshot: vi.fn(),
  quickGenerateIncidentBody: quickGenerateIncidentBodyMock,
  generateIncidentBodySection: generateIncidentBodySectionMock,
  previewIncidentAttachment: previewIncidentAttachmentMock,
  renameIncidentSession: vi.fn(),
  removeIncidentSession: vi.fn(),
}));

vi.mock('../src/api/trace', () => ({
  fetchAgentTraceReplay: vi.fn(),
}));

const buildBaseSnapshot = () => ({
  form_answers: {
    manual_fault_date: { value: '12/03/2026', custom_value: '' },
    manual_fault_time: { value: '15:00', custom_value: '' },
    manual_reporting_person: { value: 'SOC', custom_value: '' },
    manual_site_id: { value: 'CHT', custom_value: '' },
    manual_system: { value: 'Payment Service', custom_value: '' },
    manual_location: { value: 'CHT', custom_value: '' },
    manual_fault_symptom: { value: '下单报错', custom_value: '' },
    body_description: {
      value: '客户反馈下单报错，定位数据库 CPU 打满。',
      custom_value: '',
    },
    body_impact_scope: { value: '下单链路', custom_value: '' },
    body_impact_severity: { value: 'High', custom_value: '' },
    body_root_cause: { value: '慢查询缺失索引', custom_value: '' },
    body_follow_up_actions: { value: '加强 code review', custom_value: '' },
    body_timeline: {
      value: [
        {
          time: '12/03/2026 15:00',
          event: '客户报错',
          resolution: '',
          evidence: '',
        },
      ],
      custom_value: '',
    },
    quick_narrative: {
      value: '3月12日下午3点客户下单报错。',
      custom_value: '',
    },
  },
  report_data: null,
  generated_attachment: null,
  generated_versions: [],
  generated_trace_id: null,
  section_trace_ids: {},
  generated_at: null,
  is_locked: false,
  fallback_used: false,
  polish_error: null,
});

describe('incident workspace flow', () => {
  it('支持快填生成正文并触发实时预览', async () => {
    fetchAvailableModelsMock.mockResolvedValue(['qwen3-coder-next:latest']);
    fetchIncidentSessionSummariesMock.mockResolvedValue([]);
    fetchIncidentFormSchemaMock.mockResolvedValue({
      intro_message: '欢迎来到事故报告向导',
      steps: [],
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
      snapshot: buildBaseSnapshot(),
    });

    quickGenerateIncidentBodyMock.mockResolvedValue({
      session: {
        id: 'incident-session-1',
        title: '事故报告-2026/04/14 12:30',
        status: 'draft',
        created_at: '2026-04-14T12:30:00Z',
        updated_at: '2026-04-14T12:35:00Z',
      },
      snapshot: {
        ...buildBaseSnapshot(),
        generated_trace_id: 'trace-quick-1',
        section_trace_ids: {
          quick: 'trace-quick-1',
        },
      },
      trace_id: 'trace-quick-1',
      section_id: 'quick',
      timeline_index: null,
    });

    previewIncidentAttachmentMock.mockResolvedValue({
      source: 'draft',
      version: null,
      label: 'Realtime Draft Preview',
      html: '<p>preview</p>',
      docx_base64: 'ZHVtbXk=',
      docx_file_name: 'incident-report.docx',
      pdf_base64: null,
      warnings: [],
    });

    const wrapper = mount(IncidentReportPage);
    await flushPromises();

    const startButton = wrapper.find('.incident-primary-btn');
    await startButton.trigger('click');
    await flushPromises();

    expect(createIncidentSessionMock).toHaveBeenCalledTimes(1);
    expect(fetchIncidentSessionDetailMock).toHaveBeenCalledWith(
      'incident-session-1',
    );

    const quickGenerateButton = wrapper
      .findAll('button')
      .find((node) => node.text().includes('一键生成正文'));
    expect(quickGenerateButton).toBeTruthy();
    await quickGenerateButton!.trigger('click');
    await flushPromises();

    expect(quickGenerateIncidentBodyMock).toHaveBeenCalledWith(
      'incident-session-1',
      {
        model: 'qwen3-coder-next:latest',
        reranker_model: 'qwen3-coder-next:latest',
      },
      expect.objectContaining({
        signal: expect.any(Object),
      }),
    );

    const previewButton = wrapper
      .findAll('button')
      .find((node) => node.text().includes('预览附件'));
    expect(previewButton).toBeTruthy();
    await previewButton!.trigger('click');
    await flushPromises();

    expect(previewIncidentAttachmentMock).toHaveBeenCalledWith(
      'incident-session-1',
      {
        version: undefined,
        model: 'qwen3-coder-next:latest',
        reranker_model: 'qwen3-coder-next:latest',
      },
      expect.objectContaining({
        signal: expect.any(Object),
      }),
    );
    const generateAttachmentButton = wrapper
      .findAll('button')
      .find((node) => node.text().includes('生成附件（新增版本）'));
    expect(generateAttachmentButton).toBeUndefined();
  });
});
