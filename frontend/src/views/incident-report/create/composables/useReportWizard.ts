import { ref } from 'vue';
import {
  createIncidentReport,
  updateIncidentReport,
  submitIncidentReport,
} from '../../../../api/incident-report';
import type { IncidentReportDetailItem } from '../../../../types/incident-report/incident-report';
import {
  useReportGeneration,
  type ReportPayload,
} from '../../composables/useReportGeneration';

export type WizardStep = 0 | 1 | 2 | 3 | 4;

export const WIZARD_STEPS = [
  { key: 'cover', label: '首页 / Cover' },
  { key: 'quick_fill', label: '快填 / Quick Fill' },
  { key: 'body', label: 'AI 正文 / Body' },
  { key: 'appendix', label: '附录 / Appendix' },
  { key: 'preview', label: '预览 / Preview' },
] as const;

export function useReportWizard() {
  const currentStep = ref<WizardStep>(0);
  const saving = ref(false);
  const submitting = ref(false);
  const reportId = ref<string | null>(null);

  const {
    generating,
    previewing,
    previewData,
    generationError,
    quickGenerate: baseQuickGenerate,
    generateSection: baseGenerateSection,
    generatePreview: baseGeneratePreview,
    applyGenerationResult,
  } = useReportGeneration();

  const ensureReport = async (
    payload: ReportPayload,
  ): Promise<IncidentReportDetailItem> => {
    if (reportId.value) {
      return await updateIncidentReport(reportId.value, payload);
    }
    const report = await createIncidentReport(payload);
    reportId.value = report.id;
    return report;
  };

  const saveAsDraft = async (
    payload: ReportPayload,
  ): Promise<IncidentReportDetailItem> => {
    saving.value = true;
    try {
      return await ensureReport(payload);
    } finally {
      saving.value = false;
    }
  };

  const createAndSubmit = async (
    payload: ReportPayload,
  ): Promise<IncidentReportDetailItem> => {
    submitting.value = true;
    try {
      const report = await ensureReport(payload);
      await submitIncidentReport(report.id);
      return report;
    } finally {
      submitting.value = false;
    }
  };

  const quickGenerate = async (
    payload: ReportPayload,
    options?: { model?: string; rerankerModel?: string; signal?: AbortSignal },
  ) => {
    return baseQuickGenerate(
      () => reportId.value!,
      payload,
      ensureReport,
      options,
    );
  };

  const generateSection = async (
    sectionId: string,
    options?: {
      timelineIndex?: number;
      model?: string;
      rerankerModel?: string;
      signal?: AbortSignal;
    },
  ) => {
    return baseGenerateSection(reportId.value!, sectionId, options);
  };

  const generatePreview = async (options?: {
    version?: number;
    model?: string;
    rerankerModel?: string;
    signal?: AbortSignal;
  }) => {
    return baseGeneratePreview(reportId.value!, options);
  };

  return {
    currentStep,
    saving,
    submitting,
    generating,
    previewing,
    reportId,
    previewData,
    generationError,
    saveAsDraft,
    createAndSubmit,
    quickGenerate,
    generateSection,
    generatePreview,
    applyGenerationResult,
  };
}
