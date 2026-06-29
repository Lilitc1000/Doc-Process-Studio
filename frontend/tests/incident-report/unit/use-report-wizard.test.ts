import { describe, expect, it, vi, beforeEach } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { useReportWizard } from '@modules/incident-report/views/create/composables/useReportWizard';
import * as incidentApi from '@modules/incident-report';

vi.mock('@modules/incident-report', async (importOriginal) => {
  const original =
    await importOriginal<typeof import('@modules/incident-report')>();
  return {
    ...original,
    createIncidentReport: vi.fn(),
    submitIncidentReport: vi.fn(),
    updateIncidentReport: vi.fn(),
    quickGenerateIncidentReportBody: vi.fn(),
    generateIncidentReportBodySection: vi.fn(),
    previewIncidentReport: vi.fn(),
  };
});

describe('useReportWizard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setActivePinia(createPinia());
  });

  it('初始状态：步骤为 0，不在保存/提交/生成/预览', () => {
    const { currentStep, saving, submitting, generating, previewing } =
      useReportWizard();
    expect(currentStep.value).toBe(0);
    expect(saving.value).toBe(false);
    expect(submitting.value).toBe(false);
    expect(generating.value).toBe(false);
    expect(previewing.value).toBe(false);
  });

  it('createAndSubmit 创建并提交报告', async () => {
    const mockCreate = incidentApi.createIncidentReport as ReturnType<
      typeof vi.fn
    >;
    const mockSubmit = incidentApi.submitIncidentReport as ReturnType<
      typeof vi.fn
    >;
    mockCreate.mockResolvedValue({
      id: 'report-1',
      title: '测试报告',
      status: 'draft',
    });
    mockSubmit.mockResolvedValue({});

    const { createAndSubmit, submitting } = useReportWizard();
    const result = await createAndSubmit({ title: '测试报告' });

    expect(mockCreate).toHaveBeenCalledWith({ title: '测试报告' });
    expect(mockSubmit).toHaveBeenCalledWith('report-1');
    expect(result.id).toBe('report-1');
    expect(submitting.value).toBe(false);
  });

  it('createAndSubmit 失败时 submitting 恢复为 false', async () => {
    const mockCreate = incidentApi.createIncidentReport as ReturnType<
      typeof vi.fn
    >;
    mockCreate.mockRejectedValue(new Error('创建失败'));

    const { createAndSubmit, submitting } = useReportWizard();
    await expect(createAndSubmit({ title: '测试' })).rejects.toThrow();
    expect(submitting.value).toBe(false);
  });

  it('saveAsDraft 保存草稿', async () => {
    const mockCreate = incidentApi.createIncidentReport as ReturnType<
      typeof vi.fn
    >;
    mockCreate.mockResolvedValue({
      id: 'report-2',
      title: '草稿',
      status: 'draft',
    });

    const { saveAsDraft, saving } = useReportWizard();
    const result = await saveAsDraft({ title: '草稿' });

    expect(mockCreate).toHaveBeenCalledWith({ title: '草稿' });
    expect(result.id).toBe('report-2');
    expect(saving.value).toBe(false);
  });

  it('saveAsDraft 失败时 saving 恢复为 false', async () => {
    const mockCreate = incidentApi.createIncidentReport as ReturnType<
      typeof vi.fn
    >;
    mockCreate.mockRejectedValue(new Error('保存失败'));

    const { saveAsDraft, saving } = useReportWizard();
    await expect(saveAsDraft({ title: '测试' })).rejects.toThrow();
    expect(saving.value).toBe(false);
  });

  it('可以修改 currentStep', () => {
    const { currentStep } = useReportWizard();
    currentStep.value = 2;
    expect(currentStep.value).toBe(2);
  });

  it('ensureReport 复用已有 reportId 时调用 update', async () => {
    const mockCreate = incidentApi.createIncidentReport as ReturnType<
      typeof vi.fn
    >;
    const mockUpdate = incidentApi.updateIncidentReport as ReturnType<
      typeof vi.fn
    >;
    mockCreate.mockResolvedValue({
      id: 'report-3',
      title: '首次',
      status: 'draft',
    });
    mockUpdate.mockResolvedValue({
      id: 'report-3',
      title: '更新',
      status: 'draft',
    });

    const { saveAsDraft, reportId } = useReportWizard();
    await saveAsDraft({ title: '首次' });
    expect(mockCreate).toHaveBeenCalledTimes(1);
    expect(reportId.value).toBe('report-3');

    await saveAsDraft({ title: '更新' });
    expect(mockUpdate).toHaveBeenCalledWith('report-3', { title: '更新' });
    expect(mockCreate).toHaveBeenCalledTimes(1);
  });

  it('quickGenerate 调用快填生成 API', async () => {
    const mockCreate = incidentApi.createIncidentReport as ReturnType<
      typeof vi.fn
    >;
    const mockQuickGen =
      incidentApi.quickGenerateIncidentReportBody as ReturnType<typeof vi.fn>;
    mockCreate.mockResolvedValue({
      id: 'report-4',
      title: '快填测试',
      status: 'draft',
    });
    mockQuickGen.mockResolvedValue({
      reportId: 'report-4',
      formAnswers: {
        body_description: { value: 'AI 生成的描述', customValue: '' },
      },
      traceId: 'trace-001',
      sectionId: 'quick',
      timelineIndex: null,
    });

    const { quickGenerate, generating, reportId } = useReportWizard();
    const result = await quickGenerate({ title: '快填测试' });

    expect(reportId.value).toBe('report-4');
    expect(mockQuickGen).toHaveBeenCalledWith(
      'report-4',
      {},
      { signal: undefined },
    );
    expect(result.sectionId).toBe('quick');
    expect(generating.value).toBe(false);
  });

  it('quickGenerate 失败时设置 generationError', async () => {
    const mockCreate = incidentApi.createIncidentReport as ReturnType<
      typeof vi.fn
    >;
    const mockQuickGen =
      incidentApi.quickGenerateIncidentReportBody as ReturnType<typeof vi.fn>;
    mockCreate.mockResolvedValue({
      id: 'report-5',
      title: '失败测试',
      status: 'draft',
    });
    mockQuickGen.mockRejectedValue(new Error('AI 服务不可用'));

    const { quickGenerate, generationError, generating } = useReportWizard();
    await expect(quickGenerate({ title: '失败测试' })).rejects.toThrow();
    expect(generationError.value).toBe('AI 服务不可用');
    expect(generating.value).toBe(false);
  });

  it('generateSection 调用分段生成 API', async () => {
    const mockSectionGen =
      incidentApi.generateIncidentReportBodySection as ReturnType<typeof vi.fn>;
    mockSectionGen.mockResolvedValue({
      reportId: 'report-6',
      formAnswers: {
        body_description: { value: '分段生成描述', customValue: '' },
      },
      traceId: 'trace-002',
      sectionId: 'description',
      timelineIndex: null,
    });

    const wizard = useReportWizard();
    wizard.reportId.value = 'report-6';
    const result = await wizard.generateSection('description');

    expect(mockSectionGen).toHaveBeenCalledWith(
      'report-6',
      {
        sectionId: 'description',
        timelineIndex: undefined,
        model: undefined,
        rerankerModel: undefined,
      },
      { signal: undefined },
    );
    expect(result.sectionId).toBe('description');
  });

  it('generatePreview 调用预览 API 并存储结果', async () => {
    const mockPreview = incidentApi.previewIncidentReport as ReturnType<
      typeof vi.fn
    >;
    mockPreview.mockResolvedValue({
      source: 'draft',
      version: null,
      label: 'test-preview',
      html: '<p>预览内容</p>',
      docxBase64: 'base64docx',
      docxFileName: 'test.docx',
      pdfBase64: 'base64pdf',
      warnings: [],
    });

    const wizard = useReportWizard();
    wizard.reportId.value = 'report-7';
    const result = await wizard.generatePreview();

    expect(mockPreview).toHaveBeenCalledWith(
      'report-7',
      { version: undefined, model: undefined, rerankerModel: undefined },
      { signal: undefined },
    );
    expect(result.html).toBe('<p>预览内容</p>');
    expect(wizard.previewData.value?.pdfBase64).toBe('base64pdf');
  });

  it('quickGenerate abort 时不设置 generationError', async () => {
    const mockCreate = incidentApi.createIncidentReport as ReturnType<
      typeof vi.fn
    >;
    const mockQuickGen =
      incidentApi.quickGenerateIncidentReportBody as ReturnType<typeof vi.fn>;
    mockCreate.mockResolvedValue({
      id: 'report-abort-1',
      title: '中止测试',
      status: 'draft',
    });
    const abortError = new DOMException(
      'The operation was aborted.',
      'AbortError',
    );
    mockQuickGen.mockRejectedValue(abortError);

    const { quickGenerate, generationError, generating } = useReportWizard();
    await expect(
      quickGenerate({ title: '中止测试' }, { signal: AbortSignal.abort() }),
    ).rejects.toThrow();
    expect(generationError.value).toBeNull();
    expect(generating.value).toBe(false);
  });

  it('generateSection abort 时不设置 generationError', async () => {
    const mockSectionGen =
      incidentApi.generateIncidentReportBodySection as ReturnType<typeof vi.fn>;
    const abortError = new DOMException(
      'The operation was aborted.',
      'AbortError',
    );
    mockSectionGen.mockRejectedValue(abortError);

    const wizard = useReportWizard();
    wizard.reportId.value = 'report-abort-2';
    await expect(
      wizard.generateSection('description', { signal: AbortSignal.abort() }),
    ).rejects.toThrow();
    expect(wizard.generationError.value).toBeNull();
    expect(wizard.generating.value).toBe(false);
  });

  it('applyGenerationResult 将生成结果应用到 formAnswers', () => {
    const wizard = useReportWizard();
    const formAnswers: Record<string, unknown> = {
      body_description: '',
      body_root_cause: '',
    };
    wizard.applyGenerationResult(
      {
        reportId: 'report-8',
        formAnswers: {
          body_description: { value: 'AI 描述', customValue: '' },
          body_root_cause: { value: 'AI 根因', customValue: '' },
        },
        traceId: 'trace-003',
        sectionId: 'quick',
        timelineIndex: null,
      },
      formAnswers,
    );
    expect(formAnswers.body_description).toBe('AI 描述');
    expect(formAnswers.body_root_cause).toBe('AI 根因');
  });
});
