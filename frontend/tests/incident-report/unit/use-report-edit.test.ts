import { describe, expect, it, vi, beforeEach } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { useReportEditWizard } from '../../../src/views/incident-report/edit/composables/useReportEditWizard';
import * as incidentApi from '../../../src/api/incident-report';

vi.mock('../../../src/api/incident-report', () => ({
  fetchIncidentReportDetail: vi.fn(),
  updateIncidentReport: vi.fn(),
  generateIncidentReportBodySection: vi.fn(),
  previewIncidentReport: vi.fn(),
}));

describe('useReportEditWizard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setActivePinia(createPinia());
  });

  it('初始状态：报告为 null，正在加载', () => {
    const { report, loading, saving, generating, previewing, currentStep } =
      useReportEditWizard('report-1');
    expect(report.value).toBeNull();
    expect(loading.value).toBe(true);
    expect(saving.value).toBe(false);
    expect(generating.value).toBe(false);
    expect(previewing.value).toBe(false);
    expect(currentStep.value).toBe(0);
  });

  it('load 成功加载报告', async () => {
    const mockFetch = incidentApi.fetchIncidentReportDetail as ReturnType<
      typeof vi.fn
    >;
    mockFetch.mockResolvedValue({
      id: 'report-1',
      title: '测试报告',
      status: 'draft',
    });

    const { load, report, loading } = useReportEditWizard('report-1');
    await load();

    expect(report.value).toEqual({
      id: 'report-1',
      title: '测试报告',
      status: 'draft',
    });
    expect(loading.value).toBe(false);
  });

  it('load 失败时 loading 恢复为 false', async () => {
    const mockFetch = incidentApi.fetchIncidentReportDetail as ReturnType<
      typeof vi.fn
    >;
    mockFetch.mockRejectedValue(new Error('加载失败'));

    const { load, loading } = useReportEditWizard('report-1');
    await expect(load()).rejects.toThrow();
    expect(loading.value).toBe(false);
  });

  it('save 成功保存并更新报告', async () => {
    const mockUpdate = incidentApi.updateIncidentReport as ReturnType<
      typeof vi.fn
    >;
    mockUpdate.mockResolvedValue({
      id: 'report-1',
      title: '更新标题',
      status: 'draft',
    });

    const { save, report, saving } = useReportEditWizard('report-1');
    await save({ title: '更新标题' });

    expect(mockUpdate).toHaveBeenCalledWith('report-1', { title: '更新标题' });
    expect(report.value?.title).toBe('更新标题');
    expect(saving.value).toBe(false);
  });

  it('save 失败时 saving 恢复为 false', async () => {
    const mockUpdate = incidentApi.updateIncidentReport as ReturnType<
      typeof vi.fn
    >;
    mockUpdate.mockRejectedValue(new Error('保存失败'));

    const { save, saving } = useReportEditWizard('report-1');
    await expect(save({ title: '测试' })).rejects.toThrow();
    expect(saving.value).toBe(false);
  });

  it('generateSection 成功生成正文段落', async () => {
    const mockGenerate =
      incidentApi.generateIncidentReportBodySection as ReturnType<typeof vi.fn>;
    mockGenerate.mockResolvedValue({
      reportId: 'report-1',
      formAnswers: {
        body_description: { value: 'AI生成的描述' },
      },
      traceId: 'trace-1',
      sectionId: 'description',
      timelineIndex: null,
    });

    const { generateSection, generating } = useReportEditWizard('report-1');
    const result = await generateSection('description');

    expect(mockGenerate).toHaveBeenCalledWith(
      'report-1',
      {
        sectionId: 'description',
        timelineIndex: undefined,
        model: undefined,
        rerankerModel: undefined,
      },
      { signal: undefined },
    );
    expect(result.formAnswers.body_description.value).toBe('AI生成的描述');
    expect(generating.value).toBe(false);
  });

  it('generatePreview 成功生成预览', async () => {
    const mockPreview = incidentApi.previewIncidentReport as ReturnType<
      typeof vi.fn
    >;
    mockPreview.mockResolvedValue({
      source: 'draft',
      label: 'Preview',
      html: '<h1>预览</h1>',
      docx_base64: null,
      docx_file_name: null,
      pdf_base64: null,
      warnings: [],
    });

    const { generatePreview, previewData, previewing } =
      useReportEditWizard('report-1');
    await generatePreview();

    expect(mockPreview).toHaveBeenCalled();
    expect(previewData.value).not.toBeNull();
    expect(previewData.value?.html).toBe('<h1>预览</h1>');
    expect(previewing.value).toBe(false);
  });

  it('applyGenerationResult 将生成结果合并到 formAnswers', async () => {
    const { applyGenerationResult } = useReportEditWizard('report-1');
    const formAnswers: Record<string, unknown> = {
      body_description: '',
      body_root_cause: '',
    };
    const result = {
      reportId: 'report-1',
      formAnswers: {
        bodyDescription: { value: 'AI生成的描述' },
        bodyRootCause: { value: 'AI生成的根因' },
      },
      traceId: 'trace-1',
      sectionId: 'description',
      timelineIndex: null,
    };
    applyGenerationResult(result as any, formAnswers);

    expect(formAnswers.body_description).toBe('AI生成的描述');
    expect(formAnswers.body_root_cause).toBe('AI生成的根因');
  });
});
