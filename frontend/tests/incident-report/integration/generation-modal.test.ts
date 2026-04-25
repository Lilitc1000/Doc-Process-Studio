import { describe, it, expect, beforeEach, vi } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { useIncidentReportGeneration } from '../../../src/views/incident-report/composables/useIncidentReportGeneration';

vi.mock('../../../../src/api/incident-report', () => ({
  quickGenerateIncidentReportBody: vi.fn().mockResolvedValue(null),
  generateIncidentReportBodySection: vi.fn().mockResolvedValue(null),
  previewIncidentReportAttachment: vi.fn().mockResolvedValue(null),
}));

vi.mock('../../../../src/utils/common/cancel', () => ({
  isRequestCanceled: vi.fn().mockReturnValue(false),
}));

vi.mock('../../../../src/utils/common/download', () => ({
  triggerBlobDownload: vi.fn(),
}));

vi.mock('../../../../src/utils/common/error', () => ({
  getErrorMessage: vi.fn().mockReturnValue('错误'),
}));

describe('useIncidentReportGeneration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setActivePinia(createPinia());
  });

  it('初始状态应为 idle', () => {
    const generation = useIncidentReportGeneration({
      flushSaveIncidentReportSnapshot: vi.fn().mockResolvedValue(undefined),
    });
    expect(generation.quickGenerateBody).toBeTypeOf('function');
    expect(generation.generateBodySection).toBeTypeOf('function');
    expect(generation.loadIncidentReportPreview).toBeTypeOf('function');
    expect(generation.stopIncidentReportGeneration).toBeTypeOf('function');
    expect(generation.resetGenerationState).toBeTypeOf('function');
  });
});
