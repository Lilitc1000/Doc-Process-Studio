import { describe, expect, it, vi, beforeEach } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { useReportEdit } from '../../../src/views/incident-report/edit/composables/useReportEdit';
import * as incidentApi from '../../../src/api/incident-report';

vi.mock('../../../src/api/incident-report', () => ({
  fetchIncidentReportDetail: vi.fn(),
  updateIncidentReport: vi.fn(),
}));

describe('useReportEdit', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setActivePinia(createPinia());
  });

  it('初始状态：报告为 null，未加载', () => {
    const { report, loading, saving } = useReportEdit();
    expect(report.value).toBeNull();
    expect(loading.value).toBe(false);
    expect(saving.value).toBe(false);
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

    const { load, report, loading } = useReportEdit();
    await load('report-1');

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

    const { load, loading } = useReportEdit();
    await expect(load('report-1')).rejects.toThrow();
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

    const { save, report, saving } = useReportEdit();
    await save('report-1', { title: '更新标题' });

    expect(mockUpdate).toHaveBeenCalledWith('report-1', { title: '更新标题' });
    expect(report.value?.title).toBe('更新标题');
    expect(saving.value).toBe(false);
  });

  it('save 失败时 saving 恢复为 false', async () => {
    const mockUpdate = incidentApi.updateIncidentReport as ReturnType<
      typeof vi.fn
    >;
    mockUpdate.mockRejectedValue(new Error('保存失败'));

    const { save, saving } = useReportEdit();
    await expect(save('report-1', { title: '测试' })).rejects.toThrow();
    expect(saving.value).toBe(false);
  });
});
