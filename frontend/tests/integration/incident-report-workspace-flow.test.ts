import { describe, it, expect, vi } from 'vitest';
import { ref } from 'vue';
import { useIncidentReportForm } from '../../src/views/incident-report/composables/useIncidentReportForm';

const createMockStore = () => ({
  activeIncidentReportSessionId: ref(''),
  activeIncidentReportSession: ref(null),
  incidentReportSchema: ref(null),
  isIncidentReportGenerating: ref(false),
  generationState: ref('idle'),
  generationTask: ref('none'),
  incidentReportErrorMessage: ref(''),
  incidentReportSessionSummaries: ref([]),
  incidentReportSidebarSessions: ref([]),
  incidentReportPreviewHtml: ref(''),
  incidentReportPreviewPdfBase64: ref(''),
  incidentReportPreviewDocxBase64: ref(''),
  incidentReportPreviewDocxFileName: ref(''),
  incidentReportPreviewLoading: ref(false),
  incidentReportPreviewError: ref(''),
  incidentReportPreviewVersion: ref(null),
  incidentReportPreviewSource: ref('draft'),
  applyIncidentReportDetail: vi.fn(),
  mergeSummary: vi.fn(),
  clearActiveIncidentReportSession: vi.fn(),
  resetGenerationState: vi.fn(),
  resetPreviewState: vi.fn(),
});

describe('useIncidentReportForm', () => {
  it('应正确初始化', () => {
    createMockStore();
    const form = useIncidentReportForm();
    expect(form).toBeDefined();
  });
});
