import { ref } from 'vue';
import { downloadAttachment } from '../api/attachments';
import {
  fetchIncidentSessionDetail,
  generateIncidentAttachment,
} from '../api/incident-report';
import { fetchAgentTraceReplay } from '../api/trace';
import type {
  IncidentSessionDetail,
  IncidentSessionSummary,
} from '../types/incident-report';

const INCIDENT_DOCX_MIME_TYPE =
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
const INCIDENT_GENERATION_POLL_INTERVAL_MS = 1500;
const INCIDENT_GENERATION_ACTIVE_TRACK_MS = 20 * 60 * 1000;
const INCIDENT_GENERATION_BACKGROUND_TRACK_MS = 60 * 1000;

const isDocxAttachment = (
  attachment:
    | IncidentSessionDetail['snapshot']['generated_attachment']
    | null
    | undefined,
) => {
  if (!attachment) {
    return false;
  }

  const attachmentName = attachment.name.toLowerCase().trim();
  const attachmentMime = (attachment.mime_type ?? '').toLowerCase().trim();
  return (
    attachmentName.endsWith('.docx') &&
    attachmentMime === INCIDENT_DOCX_MIME_TYPE
  );
};

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

const formatTraceEventLine = (event: {
  type?: string;
  at?: string;
  detail?: Record<string, unknown>;
}) => {
  const detail = event.detail ?? {};
  let message = '';

  if (event.type === 'form_validation') {
    message = '表单校验通过';
  } else if (event.type === 'incident_data_uploaded') {
    message = '已写入 incident_data.json';
  } else if (event.type === 'skill_chat_round') {
    const round = Number(detail.round ?? 0);
    const toolCalls = Number(detail.tool_call_count ?? 0);
    message = `AI 第 ${round} 轮处理中（工具调用 ${toolCalls} 次）`;
  } else if (event.type === 'attachment_generated') {
    if (detail.ok === true) {
      message = '附件生成完成';
    } else {
      const errorMessage =
        typeof detail.error === 'string'
          ? detail.error
          : typeof detail.message === 'string'
            ? detail.message
            : '附件生成失败';
      message = `生成失败：${errorMessage}`;
    }
  } else if (typeof detail.message === 'string' && detail.message.trim()) {
    message = detail.message.trim();
  } else if (typeof event.type === 'string' && event.type.trim()) {
    message = `${event.type.trim()} 已完成`;
  } else {
    message = '已收到阶段更新';
  }

  const timestamp =
    typeof event.at === 'string' && event.at
      ? new Date(event.at).toLocaleTimeString('zh-CN', {
          hour12: false,
        })
      : '';
  return timestamp ? `${timestamp} ${message}` : message;
};

export interface IncidentGenerationDeps {
  activeIncidentSessionId: ReturnType<typeof ref<string | null>>;
  activeIncidentSession: ReturnType<typeof ref<IncidentSessionDetail | null>>;
  applyIncidentDetail: (detail: IncidentSessionDetail) => void;
  mergeSummary: (summary: IncidentSessionSummary) => void;
  flushSaveIncidentSnapshot: () => Promise<void>;
}

export const useIncidentGeneration = (deps: IncidentGenerationDeps) => {
  const {
    activeIncidentSessionId,
    activeIncidentSession,
    applyIncidentDetail,
    flushSaveIncidentSnapshot,
  } = deps;

  const isIncidentGenerating = ref(false);
  const generationState = ref<'idle' | 'generating' | 'done'>('idle');
  const incidentErrorMessage = ref('');
  const incidentGenerationTraceId = ref('');
  const incidentGenerationProgress = ref<string[]>([]);

  let generationAbortController: AbortController | null = null;
  let generationMonitorTimer: number | null = null;
  let generationMonitorDeadline = 0;
  let generationMonitorRunning = false;

  const clearGenerationMonitor = () => {
    if (generationMonitorTimer !== null) {
      window.clearTimeout(generationMonitorTimer);
      generationMonitorTimer = null;
    }
    generationMonitorDeadline = 0;
  };

  const refreshGenerationTraceProgress = async (traceId: string) => {
    const normalizedTraceId = traceId.trim();
    if (!normalizedTraceId) {
      return;
    }
    try {
      const response = await fetchAgentTraceReplay(normalizedTraceId);
      const events = response.payload.events ?? [];
      if (!events.length) {
        incidentGenerationProgress.value = ['链路已创建，等待阶段事件...'];
        return;
      }
      incidentGenerationProgress.value = events.map((event) =>
        formatTraceEventLine(event),
      );
    } catch {
      // 生成初期 trace 可能尚未落盘，静默重试。
    }
  };

  const syncIncidentGenerationSnapshot = async (
    sessionId: string,
  ): Promise<boolean> => {
    try {
      const detail = await fetchIncidentSessionDetail(sessionId);
      if (activeIncidentSessionId.value !== sessionId) {
        return true;
      }
      applyIncidentDetail(detail);

      const traceId = (detail.snapshot.generated_trace_id ?? '').trim();
      if (traceId) {
        incidentGenerationTraceId.value = traceId;
        await refreshGenerationTraceProgress(traceId);
      }

      if (detail.status === 'generating') {
        return false;
      }

      if (detail.status === 'generated') {
        if (generationState.value === 'generating') {
          generationState.value = 'done';
        }
        isIncidentGenerating.value = false;
        return true;
      }

      if (detail.status === 'failed') {
        if (generationState.value === 'generating') {
          generationState.value = 'idle';
        }
        if (detail.snapshot.polish_error) {
          incidentErrorMessage.value = detail.snapshot.polish_error;
        }
        isIncidentGenerating.value = false;
        return true;
      }

      return true;
    } catch (error) {
      console.error('同步事故报告生成状态失败。', error);
      return false;
    }
  };

  const scheduleGenerationMonitor = (sessionId: string) => {
    generationMonitorTimer = window.setTimeout(async () => {
      if (generationMonitorRunning) {
        scheduleGenerationMonitor(sessionId);
        return;
      }
      generationMonitorRunning = true;
      let settled = false;
      try {
        settled = await syncIncidentGenerationSnapshot(sessionId);
      } finally {
        generationMonitorRunning = false;
      }

      if (settled) {
        clearGenerationMonitor();
        return;
      }

      if (Date.now() > generationMonitorDeadline) {
        clearGenerationMonitor();
        return;
      }
      scheduleGenerationMonitor(sessionId);
    }, INCIDENT_GENERATION_POLL_INTERVAL_MS);
  };

  const startGenerationMonitor = (sessionId: string, maxDurationMs: number) => {
    clearGenerationMonitor();
    generationMonitorDeadline = Date.now() + maxDurationMs;
    scheduleGenerationMonitor(sessionId);
  };

  const generateIncident = async (model: string, reranker_model?: string) => {
    if (!activeIncidentSessionId.value || !activeIncidentSession.value) {
      return;
    }
    const sessionId = activeIncidentSessionId.value;
    await flushSaveIncidentSnapshot();
    generationAbortController = new AbortController();
    isIncidentGenerating.value = true;
    generationState.value = 'generating';
    incidentErrorMessage.value = '';
    incidentGenerationProgress.value = ['正在提交生成请求...'];
    incidentGenerationTraceId.value = (
      activeIncidentSession.value.snapshot.generated_trace_id ?? ''
    ).trim();
    if (incidentGenerationTraceId.value) {
      await refreshGenerationTraceProgress(incidentGenerationTraceId.value);
    }
    startGenerationMonitor(sessionId, INCIDENT_GENERATION_ACTIVE_TRACK_MS);

    try {
      const response = await generateIncidentAttachment(
        sessionId,
        {
          model,
          reranker_model,
        },
        {
          signal: generationAbortController.signal,
        },
      );
      applyIncidentDetail({
        ...response.session,
        snapshot: response.snapshot,
      });
      incidentGenerationTraceId.value = (
        response.trace_id || incidentGenerationTraceId.value
      ).trim();
      if (incidentGenerationTraceId.value) {
        await refreshGenerationTraceProgress(incidentGenerationTraceId.value);
      }
      generationState.value = 'done';
      clearGenerationMonitor();
    } catch (error) {
      if (isRequestCanceled(error)) {
        generationState.value = 'idle';
        incidentErrorMessage.value = '';
        incidentGenerationProgress.value = [
          ...incidentGenerationProgress.value,
          '已停止当前请求，正在同步后台状态…',
        ];
        startGenerationMonitor(
          sessionId,
          INCIDENT_GENERATION_BACKGROUND_TRACK_MS,
        );
        return;
      }
      generationState.value = 'idle';
      incidentErrorMessage.value =
        error instanceof Error ? error.message : '生成附件失败';
      throw error;
    } finally {
      generationAbortController = null;
      if (generationState.value !== 'generating') {
        isIncidentGenerating.value = false;
      }
    }
  };

  const stopIncidentGeneration = () => {
    if (!isIncidentGenerating.value && !generationAbortController) {
      return;
    }
    generationAbortController?.abort();
    generationAbortController = null;
    isIncidentGenerating.value = false;
    generationState.value = 'idle';
    incidentErrorMessage.value = '';
    incidentGenerationProgress.value = [
      ...incidentGenerationProgress.value,
      '已停止当前请求，正在同步后台状态…',
    ];
    if (activeIncidentSessionId.value) {
      startGenerationMonitor(
        activeIncidentSessionId.value,
        INCIDENT_GENERATION_BACKGROUND_TRACK_MS,
      );
    }
  };

  const downloadGeneratedIncidentAttachment = async () => {
    const attachment =
      activeIncidentSession.value?.snapshot.generated_attachment ?? null;
    if (!attachment) {
      return;
    }
    if (!isDocxAttachment(attachment)) {
      throw new Error('当前仅支持下载 DOCX 附件。请重新生成事故报告附件。');
    }
    const attachmentId = attachment.attachment_id ?? '';
    if (!attachmentId) {
      throw new Error('附件缺少下载标识，无法下载。');
    }
    await downloadAttachment(attachmentId);
  };

  const closeGenerationNotice = () => {
    generationState.value = 'idle';
  };

  const resetGenerationState = () => {
    generationAbortController?.abort();
    generationAbortController = null;
    clearGenerationMonitor();
    generationState.value = 'idle';
    incidentErrorMessage.value = '';
    incidentGenerationTraceId.value = '';
    incidentGenerationProgress.value = [];
    isIncidentGenerating.value = false;
  };

  const resumeGenerationMonitorIfNeeded = (
    sessionId: string,
    status: string,
  ) => {
    if (status === 'generating') {
      isIncidentGenerating.value = true;
      generationState.value = 'generating';
      startGenerationMonitor(sessionId, INCIDENT_GENERATION_ACTIVE_TRACK_MS);
    }
  };

  return {
    isIncidentGenerating,
    generationState,
    incidentErrorMessage,
    incidentGenerationTraceId,
    incidentGenerationProgress,
    generateIncident,
    stopIncidentGeneration,
    closeGenerationNotice,
    downloadGeneratedIncidentAttachment,
    resetGenerationState,
    resumeGenerationMonitorIfNeeded,
    refreshGenerationTraceProgress,
  };
};
