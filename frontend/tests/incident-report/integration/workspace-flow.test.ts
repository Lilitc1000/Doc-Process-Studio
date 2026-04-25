import { describe, it, expect, beforeEach, vi } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { useIncidentReportForm } from '../../../src/views/incident-report/composables/useIncidentReportForm';

vi.mock('../../../../src/api/incident-report', () => ({
  fetchIncidentReportFormSchema: vi.fn().mockResolvedValue(null),
  saveIncidentReportSessionSnapshot: vi.fn().mockResolvedValue(null),
}));

describe('useIncidentReportForm', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setActivePinia(createPinia());
  });

  it('应正确初始化并返回方法', () => {
    const form = useIncidentReportForm();
    expect(form.loadIncidentReportSchema).toBeTypeOf('function');
    expect(form.updateIncidentReportAnswers).toBeTypeOf('function');
    expect(form.flushSaveIncidentReportSnapshot).toBeTypeOf('function');
    expect(form.clearFormTimers).toBeTypeOf('function');
  });
});
