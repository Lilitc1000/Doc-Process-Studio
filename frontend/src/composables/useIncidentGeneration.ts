import {
  generateIncidentBodySection,
  previewIncidentAttachment,
  quickGenerateIncidentBody,
} from '../api/incident-report';
import { useIncidentStore } from '../stores/incident';

const isRequestCanceled = (error: unknown) => {
  if (error instanceof DOMException && error.name === 'AbortError') {
    return true;
  }
  if (typeof error === 'object' && error !== null) {
    const maybeCode = (error as { code?: unknown }).code;
    if (maybeCode === 'ERR_CANCELED') {
      return true;
    }
    const maybeName = (error as { name?: unknown }).name;
    if (maybeName === 'CanceledError') {
      return true;
    }
  }
  return false;
};

interface UseIncidentGenerationOptions {
  flushSaveIncidentSnapshot: () => Promise<void>;
}

const decodeBase64ToBlob = (base64: string, mimeType: string) => {
  const binary = window.atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  return new Blob([bytes], { type: mimeType });
};

const triggerBlobDownload = (blob: Blob, fileName: string) => {
  const objectUrl = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = objectUrl;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(objectUrl);
};

export const useIncidentGeneration = (
  options: UseIncidentGenerationOptions,
) => {
  const incidentStore = useIncidentStore();
  let generationAbortController: AbortController | null = null;
  let previewAbortController: AbortController | null = null;
  let previewRequestSeq = 0;

  const startGeneration = (
    task: 'quick-body' | 'section',
  ): AbortController => {
    generationAbortController?.abort();
    const controller = new AbortController();
    generationAbortController = controller;
    incidentStore.isIncidentGenerating = true;
    incidentStore.generationState = 'generating';
    incidentStore.generationTask = task;
    incidentStore.incidentErrorMessage = '';
    return controller;
  };

  const finishGeneration = (
    task: 'quick-body' | 'section',
    state: 'idle' | 'done',
  ) => {
    incidentStore.generationState = state;
    incidentStore.generationTask = 'none';
    incidentStore.isIncidentGenerating = false;
  };

  const quickGenerateBody = async (model: string, reranker_model?: string) => {
    if (
      !incidentStore.activeIncidentSessionId ||
      !incidentStore.activeIncidentSession
    ) {
      return null;
    }
    await options.flushSaveIncidentSnapshot();
    const controller = startGeneration('quick-body');
    try {
      const response = await quickGenerateIncidentBody(
        incidentStore.activeIncidentSessionId,
        {
          model,
          reranker_model,
        },
        {
          signal: controller.signal,
        },
      );
      incidentStore.applyIncidentDetail({
        ...response.session,
        snapshot: response.snapshot,
      });
      finishGeneration('quick-body', 'idle');
      return response;
    } catch (error) {
      if (isRequestCanceled(error)) {
        finishGeneration('quick-body', 'idle');
        incidentStore.incidentErrorMessage = '';
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
      reranker_model?: string;
      timeline_index?: number;
    },
  ) => {
    if (
      !incidentStore.activeIncidentSessionId ||
      !incidentStore.activeIncidentSession
    ) {
      return null;
    }
    await options.flushSaveIncidentSnapshot();
    const response = await generateIncidentBodySection(
      incidentStore.activeIncidentSessionId,
      {
        model,
        reranker_model: payload?.reranker_model,
        section_id: sectionId,
        timeline_index: payload?.timeline_index,
      },
    );
    incidentStore.applyIncidentDetail({
      ...response.session,
      snapshot: response.snapshot,
    });
    return response;
  };

  const loadIncidentPreview = async (
    payload?: {
      version?: number;
      model?: string;
      reranker_model?: string;
    },
  ) => {
    if (
      !incidentStore.activeIncidentSessionId ||
      !incidentStore.activeIncidentSession
    ) {
      return null;
    }
    previewAbortController?.abort();
    const requestSeq = previewRequestSeq + 1;
    previewRequestSeq = requestSeq;
    const controller = new AbortController();
    previewAbortController = controller;

    incidentStore.incidentPreviewLoading = true;
    incidentStore.incidentPreviewError = '';
    incidentStore.incidentPreviewVersion =
      typeof payload?.version === 'number' ? payload.version : null;
    try {
      await options.flushSaveIncidentSnapshot();
      if (requestSeq !== previewRequestSeq) {
        return null;
      }
      const response = await previewIncidentAttachment(
        incidentStore.activeIncidentSessionId,
        {
          version: payload?.version,
          model: payload?.model,
          reranker_model: payload?.reranker_model,
        },
        {
          signal: controller.signal,
        },
      );
      if (requestSeq !== previewRequestSeq) {
        return null;
      }
      incidentStore.incidentPreviewSource = response.source;
      incidentStore.incidentPreviewHtml = response.html;
      incidentStore.incidentPreviewPdfBase64 = response.pdf_base64 ?? '';
      incidentStore.incidentPreviewDocxBase64 = response.docx_base64 ?? '';
      incidentStore.incidentPreviewDocxFileName = response.docx_file_name ?? '';
      incidentStore.incidentPreviewError = '';
      return response;
    } catch (error) {
      if (isRequestCanceled(error) || requestSeq !== previewRequestSeq) {
        return null;
      }
      incidentStore.incidentPreviewSource = '';
      incidentStore.incidentPreviewHtml = '';
      incidentStore.incidentPreviewPdfBase64 = '';
      incidentStore.incidentPreviewDocxBase64 = '';
      incidentStore.incidentPreviewDocxFileName = '';
      incidentStore.incidentPreviewError =
        error instanceof Error ? error.message : '加载预览失败';
      throw error;
    } finally {
      if (requestSeq !== previewRequestSeq) {
        return null;
      }
      incidentStore.incidentPreviewLoading = false;
      if (previewAbortController === controller) {
        previewAbortController = null;
      }
    }
  };

  const cancelIncidentPreview = () => {
    previewRequestSeq += 1;
    previewAbortController?.abort();
    previewAbortController = null;
    incidentStore.incidentPreviewLoading = false;
  };

  const stopIncidentGeneration = () => {
    generationAbortController?.abort();
    generationAbortController = null;
    incidentStore.isIncidentGenerating = false;
    incidentStore.generationState = 'idle';
    incidentStore.generationTask = 'none';
    incidentStore.incidentErrorMessage = '';
  };

  const downloadIncidentPreviewDocx = async () => {
    const docxBase64 = incidentStore.incidentPreviewDocxBase64.trim();
    if (!docxBase64) {
      throw new Error('当前预览没有可下载的文档内容。');
    }
    const fileName =
      incidentStore.incidentPreviewDocxFileName.trim() || 'incident-report.docx';
    const docxBlob = decodeBase64ToBlob(
      docxBase64,
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    );
    triggerBlobDownload(docxBlob, fileName);
  };

  const resetGenerationState = () => {
    generationAbortController?.abort();
    generationAbortController = null;
    cancelIncidentPreview();
    incidentStore.resetGenerationState();
    incidentStore.resetPreviewState();
  };

  const resumeGenerationMonitorIfNeeded = () => {
    return;
  };

  const refreshGenerationTraceProgress = async () => {
    return;
  };

  return {
    quickGenerateBody,
    generateBodySection,
    loadIncidentPreview,
    cancelIncidentPreview,
    stopIncidentGeneration,
    downloadIncidentPreviewDocx,
    resetGenerationState,
    resumeGenerationMonitorIfNeeded,
    refreshGenerationTraceProgress,
  };
};
