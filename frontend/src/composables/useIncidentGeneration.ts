import { downloadAttachment } from '../api/attachments';
import {
  fetchIncidentSessionDetail,
  generateIncidentAttachment,
} from '../api/incident-report';
import { fetchAgentTraceReplay } from '../api/trace';
import { useIncidentStore } from '../stores/incident';
import type { IncidentSessionDetail } from '../types/incident-report';

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

interface UseIncidentGenerationOptions {
  flushSaveIncidentSnapshot: () => Promise<void>;
}

export const useIncidentGeneration = (
  options: UseIncidentGenerationOptions,
) => {
  const incidentStore = useIncidentStore();

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
        incidentStore.incidentGenerationProgress = [
          '链路已创建，等待阶段事件...',
        ];
        return;
      }
      incidentStore.incidentGenerationProgress = events.map((event) =>
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
      if (incidentStore.activeIncidentSessionId !== sessionId) {
        return true;
      }
      incidentStore.applyIncidentDetail(detail);

      const traceId = (detail.snapshot.generated_trace_id ?? '').trim();
      if (traceId) {
        incidentStore.incidentGenerationTraceId = traceId;
        await refreshGenerationTraceProgress(traceId);
      }

      if (detail.status === 'generating') {
        return false;
      }

      if (detail.status === 'generated') {
        if (incidentStore.generationState === 'generating') {
          incidentStore.generationState = 'done';
        }
        incidentStore.isIncidentGenerating = false;
        return true;
      }

      if (detail.status === 'failed') {
        if (incidentStore.generationState === 'generating') {
          incidentStore.generationState = 'idle';
        }
        if (detail.snapshot.polish_error) {
          incidentStore.incidentErrorMessage = detail.snapshot.polish_error;
        }
        incidentStore.isIncidentGenerating = false;
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
    if (
      !incidentStore.activeIncidentSessionId ||
      !incidentStore.activeIncidentSession
    ) {
      return;
    }
    const sessionId = incidentStore.activeIncidentSessionId;
    await options.flushSaveIncidentSnapshot();
    generationAbortController = new AbortController();
    incidentStore.isIncidentGenerating = true;
    incidentStore.generationState = 'generating';
    incidentStore.incidentErrorMessage = '';
    incidentStore.incidentGenerationProgress = ['正在提交生成请求...'];
    incidentStore.incidentGenerationTraceId = (
      incidentStore.activeIncidentSession.snapshot.generated_trace_id ?? ''
    ).trim();
    if (incidentStore.incidentGenerationTraceId) {
      await refreshGenerationTraceProgress(
        incidentStore.incidentGenerationTraceId,
      );
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
      incidentStore.applyIncidentDetail({
        ...response.session,
        snapshot: response.snapshot,
      });
      incidentStore.incidentGenerationTraceId = (
        response.trace_id || incidentStore.incidentGenerationTraceId
      ).trim();
      if (incidentStore.incidentGenerationTraceId) {
        await refreshGenerationTraceProgress(
          incidentStore.incidentGenerationTraceId,
        );
      }
      incidentStore.generationState = 'done';
      clearGenerationMonitor();
    } catch (error) {
      if (isRequestCanceled(error)) {
        incidentStore.generationState = 'idle';
        incidentStore.incidentErrorMessage = '';
        incidentStore.incidentGenerationProgress = [
          ...incidentStore.incidentGenerationProgress,
          '已停止当前请求，正在同步后台状态…',
        ];
        startGenerationMonitor(
          sessionId,
          INCIDENT_GENERATION_BACKGROUND_TRACK_MS,
        );
        return;
      }
      incidentStore.generationState = 'idle';
      incidentStore.incidentErrorMessage =
        error instanceof Error ? error.message : '生成附件失败';
      throw error;
    } finally {
      generationAbortController = null;
      if (incidentStore.generationState !== 'generating') {
        incidentStore.isIncidentGenerating = false;
      }
    }
  };

  const stopIncidentGeneration = () => {
    if (!incidentStore.isIncidentGenerating && !generationAbortController) {
      return;
    }
    generationAbortController?.abort();
    generationAbortController = null;
    incidentStore.isIncidentGenerating = false;
    incidentStore.generationState = 'idle';
    incidentStore.incidentErrorMessage = '';
    incidentStore.incidentGenerationProgress = [
      ...incidentStore.incidentGenerationProgress,
      '已停止当前请求，正在同步后台状态…',
    ];
    if (incidentStore.activeIncidentSessionId) {
      startGenerationMonitor(
        incidentStore.activeIncidentSessionId,
        INCIDENT_GENERATION_BACKGROUND_TRACK_MS,
      );
    }
  };

  const downloadGeneratedIncidentAttachment = async () => {
    const attachment =
      incidentStore.activeIncidentSession?.snapshot.generated_attachment ??
      null;
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
    incidentStore.generationState = 'idle';
  };

  const resetGenerationState = () => {
    generationAbortController?.abort();
    generationAbortController = null;
    clearGenerationMonitor();
    incidentStore.resetGenerationState();
  };

  const resumeGenerationMonitorIfNeeded = (
    sessionId: string,
    status: string,
  ) => {
    if (status === 'generating') {
      incidentStore.isIncidentGenerating = true;
      incidentStore.generationState = 'generating';
      startGenerationMonitor(sessionId, INCIDENT_GENERATION_ACTIVE_TRACK_MS);
    }
  };

  return {
    generateIncident,
    stopIncidentGeneration,
    closeGenerationNotice,
    downloadGeneratedIncidentAttachment,
    resetGenerationState,
    resumeGenerationMonitorIfNeeded,
    refreshGenerationTraceProgress,
  };
};
