import { ref } from 'vue';
import humps from 'humps';
import {
  quickGenerateIncidentReportBody,
  generateIncidentReportBodySection,
  previewIncidentReport,
} from '../../../api/incident-report';
import type {
  IncidentBodyGenerateResponse,
  IncidentReportPreviewResponse,
} from '../../../types/incident-report/incident-report';

export interface ReportPayload {
  title: string;
  severity?: string;
  system?: string;
  siteId?: string;
  faultDate?: string;
  formData?: Record<string, unknown>;
}

export function useReportGeneration() {
  const generating = ref(false);
  const previewing = ref(false);
  const previewData = ref<IncidentReportPreviewResponse | null>(null);
  const generationError = ref<string | null>(null);

  const quickGenerate = async (
    getReportId: () => string,
    payload: ReportPayload,
    saveFn: (p: ReportPayload) => Promise<unknown>,
    options?: { model?: string; rerankerModel?: string; signal?: AbortSignal },
  ): Promise<IncidentBodyGenerateResponse> => {
    generating.value = true;
    generationError.value = null;
    try {
      await saveFn(payload);
      const result = await quickGenerateIncidentReportBody(
        getReportId(),
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
    reportId: string,
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

  const generatePreview = async (
    reportId: string,
    options?: {
      version?: number;
      model?: string;
      rerankerModel?: string;
      signal?: AbortSignal;
    },
  ): Promise<IncidentReportPreviewResponse> => {
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
    generating,
    previewing,
    previewData,
    generationError,
    quickGenerate,
    generateSection,
    generatePreview,
    applyGenerationResult,
  };
}
