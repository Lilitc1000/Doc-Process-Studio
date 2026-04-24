import {
  generateIncidentReportBodySection,
  previewIncidentReportAttachment,
  quickGenerateIncidentReportBody,
} from '../../../api/incident-report';
import { useIncidentReportStore } from '../../../stores/incident-report';
import { isRequestCanceled } from '../../../utils/common/cancel';
import { triggerBlobDownload } from '../../../utils/common/download';
import { getErrorMessage } from '../../../utils/common/error';

interface UseIncidentReportGenerationOptions {
  flushSaveIncidentReportSnapshot: () => Promise<void>;
}

const decodeBase64ToBlob = (base64: string, mimeType: string) => {
  const binary = window.atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  return new Blob([bytes], { type: mimeType });
};

export const useIncidentReportGeneration = (
  options: UseIncidentReportGenerationOptions,
) => {
  const incidentReportStore = useIncidentReportStore();
  let generationAbortController: AbortController | null = null;
  let previewAbortController: AbortController | null = null;
  let previewRequestSeq = 0;

  const startGeneration = (task: 'quick-body' | 'section'): AbortController => {
    generationAbortController?.abort();
    const controller = new AbortController();
    generationAbortController = controller;
    incidentReportStore.isIncidentReportGenerating = true;
    incidentReportStore.generationState = 'generating';
    incidentReportStore.generationTask = task;
    incidentReportStore.incidentReportErrorMessage = '';
    return controller;
  };

  const finishGeneration = (
    task: 'quick-body' | 'section',
    state: 'idle' | 'done',
  ) => {
    incidentReportStore.generationState = state;
    incidentReportStore.generationTask = 'none';
    incidentReportStore.isIncidentReportGenerating = false;
  };

  const quickGenerateBody = async (model: string, rerankerModel?: string) => {
    if (
      !incidentReportStore.activeIncidentReportSessionId ||
      !incidentReportStore.activeIncidentReportSession
    ) {
      return null;
    }
    await options.flushSaveIncidentReportSnapshot();
    const controller = startGeneration('quick-body');
    try {
      const response = await quickGenerateIncidentReportBody(
        incidentReportStore.activeIncidentReportSessionId,
        {
          model,
          rerankerModel,
        },
        {
          signal: controller.signal,
        },
      );
      incidentReportStore.applyIncidentReportDetail({
        ...response.session,
        snapshot: response.snapshot,
      });
      finishGeneration('quick-body', 'idle');
      return response;
    } catch (error) {
      if (isRequestCanceled(error)) {
        finishGeneration('quick-body', 'idle');
        incidentReportStore.incidentReportErrorMessage = '';
        return null;
      }
      finishGeneration('quick-body', 'idle');
      throw error;
    } finally {
      if (generationAbortController === controller) {
        generationAbortController = null;
      }
    }
  };

  const generateBodySection = async (
    model: string,
    sectionId: string,
    payload?: {
      rerankerModel?: string;
      timelineIndex?: number;
    },
  ) => {
    if (
      !incidentReportStore.activeIncidentReportSessionId ||
      !incidentReportStore.activeIncidentReportSession
    ) {
      return null;
    }
    await options.flushSaveIncidentReportSnapshot();
    const controller = startGeneration('section');
    try {
      const response = await generateIncidentReportBodySection(
        incidentReportStore.activeIncidentReportSessionId,
        {
          model,
          rerankerModel: payload?.rerankerModel,
          sectionId,
          timelineIndex: payload?.timelineIndex,
        },
        {
          signal: controller.signal,
        },
      );
      incidentReportStore.applyIncidentReportDetail({
        ...response.session,
        snapshot: response.snapshot,
      });
      finishGeneration('section', 'idle');
      return response;
    } catch (error) {
      if (isRequestCanceled(error)) {
        finishGeneration('section', 'idle');
        incidentReportStore.incidentReportErrorMessage = '';
        return null;
      }
      finishGeneration('section', 'idle');
      throw error;
    } finally {
      if (generationAbortController === controller) {
        generationAbortController = null;
      }
    }
  };

  const loadIncidentReportPreview = async (payload?: {
    version?: number;
    model?: string;
    rerankerModel?: string;
  }) => {
    if (
      !incidentReportStore.activeIncidentReportSessionId ||
      !incidentReportStore.activeIncidentReportSession
    ) {
      return null;
    }
    previewAbortController?.abort();
    const requestSeq = previewRequestSeq + 1;
    previewRequestSeq = requestSeq;
    const controller = new AbortController();
    previewAbortController = controller;

    incidentReportStore.incidentReportPreviewLoading = true;
    incidentReportStore.incidentReportPreviewError = '';
    incidentReportStore.incidentReportPreviewVersion =
      typeof payload?.version === 'number' ? payload.version : null;
    try {
      await options.flushSaveIncidentReportSnapshot();
      if (requestSeq !== previewRequestSeq) {
        return null;
      }
      const response = await previewIncidentReportAttachment(
        incidentReportStore.activeIncidentReportSessionId,
        {
          version: payload?.version,
          model: payload?.model,
          rerankerModel: payload?.rerankerModel,
        },
        {
          signal: controller.signal,
        },
      );
      if (requestSeq !== previewRequestSeq) {
        return null;
      }
      incidentReportStore.incidentReportPreviewSource = response.source;
      incidentReportStore.incidentReportPreviewHtml = response.html;
      incidentReportStore.incidentReportPreviewPdfBase64 =
        response.pdfBase64 ?? '';
      incidentReportStore.incidentReportPreviewDocxBase64 =
        response.docxBase64 ?? '';
      incidentReportStore.incidentReportPreviewDocxFileName =
        response.docxFileName ?? '';
      incidentReportStore.incidentReportPreviewError = '';
      return response;
    } catch (error) {
      if (isRequestCanceled(error) || requestSeq !== previewRequestSeq) {
        return null;
      }
      incidentReportStore.incidentReportPreviewSource = 'draft';
      incidentReportStore.incidentReportPreviewHtml = '';
      incidentReportStore.incidentReportPreviewPdfBase64 = '';
      incidentReportStore.incidentReportPreviewDocxBase64 = '';
      incidentReportStore.incidentReportPreviewDocxFileName = '';
      incidentReportStore.incidentReportPreviewError = getErrorMessage(
        error,
        '加载预览失败',
      );
      throw error;
    } finally {
      if (requestSeq === previewRequestSeq) {
        incidentReportStore.incidentReportPreviewLoading = false;
        if (previewAbortController === controller) {
          previewAbortController = null;
        }
      }
    }
  };

  const cancelIncidentReportPreview = () => {
    previewRequestSeq += 1;
    previewAbortController?.abort();
    previewAbortController = null;
    incidentReportStore.incidentReportPreviewLoading = false;
  };

  const stopIncidentReportGeneration = () => {
    generationAbortController?.abort();
    generationAbortController = null;
    incidentReportStore.isIncidentReportGenerating = false;
    incidentReportStore.generationState = 'idle';
    incidentReportStore.generationTask = 'none';
    incidentReportStore.incidentReportErrorMessage = '';
  };

  const downloadIncidentReportPreviewDocx = async () => {
    const docxBase64 =
      incidentReportStore.incidentReportPreviewDocxBase64.trim();
    if (!docxBase64) {
      throw new Error('当前预览没有可下载的文档内容。');
    }
    const fileName =
      incidentReportStore.incidentReportPreviewDocxFileName.trim() ||
      'incident-report.docx';
    const docxBlob = decodeBase64ToBlob(
      docxBase64,
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    );
    triggerBlobDownload(docxBlob, fileName);
  };

  const resetGenerationState = () => {
    generationAbortController?.abort();
    generationAbortController = null;
    cancelIncidentReportPreview();
    incidentReportStore.resetGenerationState();
    incidentReportStore.resetPreviewState();
  };

  return {
    quickGenerateBody,
    generateBodySection,
    loadIncidentReportPreview,
    cancelIncidentReportPreview,
    stopIncidentReportGeneration,
    downloadIncidentReportPreviewDocx,
    resetGenerationState,
  };
};
