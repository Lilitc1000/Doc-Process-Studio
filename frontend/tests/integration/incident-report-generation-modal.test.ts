import { describe, it, vi } from 'vitest';
import { ref } from 'vue';
import { useIncidentReportGeneration } from '../../src/views/incident-report/composables/useIncidentReportGeneration';

const createMockStore = () => ({
  activeIncidentReportSessionId: ref(''),
  activeIncidentReportSession: ref(null),
  isIncidentReportGenerating: ref(false),
  generationState: ref('idle'),
  generationTask: ref('none'),
  incidentReportErrorMessage: ref(''),
  incidentReportPreviewHtml: ref(''),
  incidentReportPreviewPdfBase64: ref(''),
  incidentReportPreviewDocxBase64: ref(''),
  incidentReportPreviewDocxFileName: ref(''),
  incidentReportPreviewLoading: ref(false),
  incidentReportPreviewError: ref(''),
  incidentReportPreviewVersion: ref(null),
  incidentReportPreviewSource: ref('draft'),
  applyIncidentReportDetail: vi.fn(),
  resetGenerationState: vi.fn(),
  resetPreviewState: vi.fn(),
});

describe('useIncidentReportGeneration', () => {
  it('初始状态应为 idle', () => {
    createMockStore();
    useIncidentReportGeneration({
      flushSaveIncidentReportSnapshot: vi.fn().mockResolvedValue(undefined),
    });
  });
});
