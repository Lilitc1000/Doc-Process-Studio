import { describe, expect, it, vi, beforeEach } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { useReportWizard } from '../../../src/views/incident-report/create/composables/useReportWizard';
import * as incidentApi from '../../../src/api/incident-report';

vi.mock('../../../src/api/incident-report', () => ({
  createIncidentReport: vi.fn(),
  submitIncidentReport: vi.fn(),
  updateIncidentReport: vi.fn(),
}));

describe('useReportWizard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setActivePinia(createPinia());
  });

  it('初始状态：步骤为 0，不在保存/提交', () => {
    const { currentStep, saving, submitting } = useReportWizard();
    expect(currentStep.value).toBe(0);
    expect(saving.value).toBe(false);
    expect(submitting.value).toBe(false);
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
});
