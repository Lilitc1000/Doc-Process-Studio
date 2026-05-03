import { ref } from 'vue';
import {
  fetchIncidentReportDetail,
  updateIncidentReport,
} from '../../../../api/incident-report';
import type { IncidentReportDetailItem } from '../../../../types/incident-report/incident-report';
import {
  useReportGeneration,
  type ReportPayload,
} from '../../composables/useReportGeneration';

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
  const report = ref<IncidentReportDetailItem | null>(null);

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

  const load = async () => {
    loading.value = true;
    try {
      report.value = await fetchIncidentReportDetail(reportId);
    } catch {
      report.value = null;
    } finally {
      loading.value = false;
    }
  };

  const save = async (
    payload: ReportPayload,
  ): Promise<IncidentReportDetailItem> => {
    saving.value = true;
    try {
      report.value = await updateIncidentReport(reportId, payload);
      return report.value;
    } finally {
      saving.value = false;
    }
  };

  const quickGenerate = async (
    payload: ReportPayload,
    options?: { model?: string; rerankerModel?: string; signal?: AbortSignal },
  ) => {
    return baseQuickGenerate(() => reportId, payload, save, options);
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
    return baseGenerateSection(reportId, sectionId, options);
  };

  const generatePreview = async (options?: {
    version?: number;
    model?: string;
    rerankerModel?: string;
    signal?: AbortSignal;
  }) => {
    return baseGeneratePreview(reportId, options);
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
