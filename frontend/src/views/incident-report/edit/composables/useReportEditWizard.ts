import { ref } from 'vue';
import humps from 'humps';
import {
  fetchIncidentReportDetail,
  updateIncidentReport,
  quickGenerateIncidentReportBody,
  generateIncidentReportBodySection,
  previewIncidentReport,
} from '../../../../api/incident-report';
import type {
  IncidentReportDetailItem,
  IncidentBodyGenerateResponse,
  IncidentReportPreviewResponse,
} from '../../../../types/incident-report/incident-report';

export type EditWizardStep = 0 | 1 | 2 | 3 | 4;

export const EDIT_WIZARD_STEPS = [
  { key: 'cover', label: '首页 / Cover' },
  { key: 'quick_fill', label: '快填 / Quick Fill' },
  { key: 'body', label: 'AI 正文 / Body' },
  { key: 'appendix', label: '附录 / Appendix' },
  { key: 'preview', label: '预览 / Preview' },
] as const;

export function useReportEditWizard(reportId: string) {
  const currentStep = ref<EditWizardStep>(0);
  const loading = ref(true);
  const saving = ref(false);
  const generating = ref(false);
  const previewing = ref(false);
  const report = ref<IncidentReportDetailItem | null>(null);
  const previewData = ref<IncidentReportPreviewResponse | null>(null);
  const generationError = ref<string | null>(null);

  const load = async () => {
    loading.value = true;
    try {
      report.value = await fetchIncidentReportDetail(reportId);
    } finally {
      loading.value = false;
    }
  };

  const save = async (payload: {
    title: string;
    severity?: string;
    system?: string;
    siteId?: string;
    faultDate?: string;
    formData?: Record<string, unknown>;
  }): Promise<IncidentReportDetailItem> => {
    saving.value = true;
    try {
      report.value = await updateIncidentReport(reportId, payload);
      return report.value;
    } finally {
      saving.value = false;
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
      await save(payload);
      const result = await quickGenerateIncidentReportBody(
        reportId,
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
        reportId,
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
        reportId,
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
    loading,
    saving,
    generating,
    previewing,
    report,
    previewData,
    generationError,
    load,
    save,
    quickGenerate,
    generateSection,
    generatePreview,
    applyGenerationResult,
  };
}
