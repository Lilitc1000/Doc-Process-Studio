import { ref } from 'vue';
import humps from 'humps';
import {
  createIncidentReport,
  updateIncidentReport,
  submitIncidentReport,
  quickGenerateIncidentReportBody,
  generateIncidentReportBodySection,
  previewIncidentReport,
} from '../../../../api/incident-report';
import type {
  IncidentReportDetailItem,
  IncidentBodyGenerateResponse,
  IncidentReportPreviewResponse,
} from '../../../../types/incident-report/incident-report';

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
  const generating = ref(false);
  const previewing = ref(false);
  const reportId = ref<string | null>(null);
  const previewData = ref<IncidentReportPreviewResponse | null>(null);
  const generationError = ref<string | null>(null);

  const ensureReport = async (payload: {
    title: string;
    severity?: string;
    system?: string;
    siteId?: string;
    faultDate?: string;
    formData?: Record<string, unknown>;
  }): Promise<IncidentReportDetailItem> => {
    if (reportId.value) {
      return await updateIncidentReport(reportId.value, payload);
    }
    const report = await createIncidentReport(payload);
    reportId.value = report.id;
    return report;
  };

  const saveAsDraft = async (payload: {
    title: string;
    severity?: string;
    system?: string;
    siteId?: string;
    faultDate?: string;
    formData?: Record<string, unknown>;
  }): Promise<IncidentReportDetailItem> => {
    saving.value = true;
    try {
      return await ensureReport(payload);
    } finally {
      saving.value = false;
    }
  };

  const createAndSubmit = async (payload: {
    title: string;
    severity?: string;
    system?: string;
    siteId?: string;
    faultDate?: string;
    formData?: Record<string, unknown>;
  }): Promise<IncidentReportDetailItem> => {
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
    payload: {
      title: string;
      severity?: string;
      system?: string;
      siteId?: string;
      faultDate?: string;
      formData?: Record<string, unknown>;
    },
    options?: { model?: string; rerankerModel?: string; signal?: AbortSignal },
  ): Promise<IncidentBodyGenerateResponse> => {
    generating.value = true;
    generationError.value = null;
    try {
      await ensureReport(payload);
      const result = await quickGenerateIncidentReportBody(
        reportId.value!,
        {
          model: options?.model,
          rerankerModel: options?.rerankerModel,
        },
        { signal: options?.signal },
      );
      return result;
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') {
        throw err;
      }
      const message = err instanceof Error ? err.message : '快填生成失败';
      generationError.value = message;
      throw err;
    } finally {
      generating.value = false;
    }
  };

  const generateSection = async (
    sectionId: string,
    options?: {
      timelineIndex?: number;
      model?: string;
      rerankerModel?: string;
      signal?: AbortSignal;
    },
  ): Promise<IncidentBodyGenerateResponse> => {
    generating.value = true;
    generationError.value = null;
    try {
      const result = await generateIncidentReportBodySection(
        reportId.value!,
        {
          sectionId,
          timelineIndex: options?.timelineIndex,
          model: options?.model,
          rerankerModel: options?.rerankerModel,
        },
        { signal: options?.signal },
      );
      return result;
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') {
        throw err;
      }
      const message = err instanceof Error ? err.message : '分段生成失败';
      generationError.value = message;
      throw err;
    } finally {
      generating.value = false;
    }
  };

  const generatePreview = async (options?: {
    version?: number;
    model?: string;
    rerankerModel?: string;
    signal?: AbortSignal;
  }): Promise<IncidentReportPreviewResponse> => {
    previewing.value = true;
    try {
      const result = await previewIncidentReport(
        reportId.value!,
        {
          version: options?.version,
          model: options?.model,
          rerankerModel: options?.rerankerModel,
        },
        { signal: options?.signal },
      );
      previewData.value = result;
      return result;
    } finally {
      previewing.value = false;
    }
  };

  const applyGenerationResult = (
    result: IncidentBodyGenerateResponse,
    formAnswers: Record<string, unknown>,
  ) => {
    for (const [key, answer] of Object.entries(result.formAnswers)) {
      const snakeKey = humps.decamelize(key);
      formAnswers[snakeKey] = answer.value ?? '';
    }
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
