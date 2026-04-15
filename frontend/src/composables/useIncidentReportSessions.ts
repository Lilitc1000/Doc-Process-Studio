import { computed, ref } from 'vue';
import { downloadAttachment } from '../api/attachments';
import {
  createIncidentSession,
  fetchIncidentFormSchema,
  fetchIncidentSessionDetail,
  fetchIncidentSessionSummaries,
  generateIncidentAttachment,
  removeIncidentSession,
  renameIncidentSession,
  saveIncidentSessionSnapshot,
} from '../api/incident-report';
import { fetchAgentTraceReplay } from '../api/trace';
import type { ChatSessionSummary } from '../types/session';
import type {
  IncidentFormAnswer,
  IncidentFormSchemaPayload,
  IncidentSessionDetail,
  IncidentSessionSummary,
} from '../types/incident-report';

const INCIDENT_DOCX_MIME_TYPE =
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
const INCIDENT_GENERATION_POLL_INTERVAL_MS = 1500;
const INCIDENT_GENERATION_ACTIVE_TRACK_MS = 20 * 60 * 1000;
const INCIDENT_GENERATION_BACKGROUND_TRACK_MS = 60 * 1000;

const formatIncidentStatusLabel = (
  status: IncidentSessionSummary['status'],
) => {
  if (status === 'generated') {
    return '已生成';
  }
  if (status === 'generating') {
    return '生成中';
  }
  if (status === 'failed') {
    return '失败';
  }
  return '未生成';
};

const buildIncidentSessionTitle = () => {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  const hour = String(now.getHours()).padStart(2, '0');
  const minute = String(now.getMinutes()).padStart(2, '0');
  return `事故报告-${year}/${month}/${day} ${hour}:${minute}`;
};

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

export const useIncidentReportSessions = () => {
  const incidentSchema = ref<IncidentFormSchemaPayload | null>(null);
  const incidentSessionSummaries = ref<IncidentSessionSummary[]>([]);
  const activeIncidentSessionId = ref<string | null>(null);
  const activeIncidentSession = ref<IncidentSessionDetail | null>(null);
  const isIncidentGenerating = ref(false);
  const generationState = ref<'idle' | 'generating' | 'done'>('idle');
  const incidentErrorMessage = ref('');
  const incidentGenerationTraceId = ref('');
  const incidentGenerationProgress = ref<string[]>([]);

  let saveDebounceTimer: number | null = null;
  let hasQueuedSnapshotSave = false;
  let isSnapshotSaveInFlight = false;
  let snapshotSavePromise: Promise<void> | null = null;
  let generationAbortController: AbortController | null = null;
  let generationMonitorTimer: number | null = null;
  let generationMonitorDeadline = 0;
  let generationMonitorRunning = false;

  const cloneFormAnswers = (answers: Record<string, IncidentFormAnswer>) => {
    return JSON.parse(JSON.stringify(answers)) as Record<
      string,
      IncidentFormAnswer
    >;
  };

  const mergeSummary = (summary: IncidentSessionSummary) => {
    const next = incidentSessionSummaries.value.filter((item) => {
      return item.id !== summary.id;
    });
    next.unshift(summary);
    next.sort((left, right) => {
      return (
        new Date(right.updated_at).getTime() -
        new Date(left.updated_at).getTime()
      );
    });
    incidentSessionSummaries.value = next;
  };

  const incidentSidebarSessions = computed<ChatSessionSummary[]>(() => {
    return incidentSessionSummaries.value.map((summary) => ({
      id: summary.id,
      title: summary.title,
      status: summary.status,
      status_label: formatIncidentStatusLabel(summary.status),
      created_at: summary.created_at,
      updated_at: summary.updated_at,
      selected_model: '',
      selected_reranker_model: null,
    }));
  });

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

  const applyIncidentDetail = (detail: IncidentSessionDetail) => {
    if (activeIncidentSessionId.value !== detail.id) {
      return;
    }
    activeIncidentSession.value = detail;
    mergeSummary({
      id: detail.id,
      title: detail.title,
      status: detail.status,
      created_at: detail.created_at,
      updated_at: detail.updated_at,
    });
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

  const loadIncidentSchema = async () => {
    try {
      incidentSchema.value = await fetchIncidentFormSchema();
    } catch (error) {
      console.error('加载事故报告表单定义失败。', error);
    }
  };

  const loadIncidentSessionSummaries = async () => {
    try {
      const sessions = await fetchIncidentSessionSummaries();
      incidentSessionSummaries.value = [...sessions].sort((left, right) => {
        return (
          new Date(right.updated_at).getTime() -
          new Date(left.updated_at).getTime()
        );
      });
    } catch (error) {
      console.error('加载事故报告历史会话失败。', error);
    }
  };

  const loadIncidentSession = async (sessionId: string) => {
    try {
      const detail = await fetchIncidentSessionDetail(sessionId);
      activeIncidentSessionId.value = sessionId;
      applyIncidentDetail(detail);
      incidentErrorMessage.value = '';

      incidentGenerationTraceId.value = (
        detail.snapshot.generated_trace_id ?? ''
      ).trim();
      if (incidentGenerationTraceId.value) {
        await refreshGenerationTraceProgress(incidentGenerationTraceId.value);
      } else {
        incidentGenerationProgress.value = [];
      }

      if (detail.status === 'generating') {
        isIncidentGenerating.value = true;
        generationState.value = 'generating';
        startGenerationMonitor(sessionId, INCIDENT_GENERATION_ACTIVE_TRACK_MS);
      }
    } catch (error) {
      console.error('加载事故报告会话失败。', error);
      incidentErrorMessage.value =
        error instanceof Error ? error.message : '加载会话失败';
    }
  };

  const clearActiveIncidentSession = () => {
    if (saveDebounceTimer !== null) {
      window.clearTimeout(saveDebounceTimer);
      saveDebounceTimer = null;
    }
    generationAbortController?.abort();
    generationAbortController = null;
    clearGenerationMonitor();
    activeIncidentSessionId.value = null;
    activeIncidentSession.value = null;
    incidentErrorMessage.value = '';
    generationState.value = 'idle';
    incidentGenerationTraceId.value = '';
    incidentGenerationProgress.value = [];
    isIncidentGenerating.value = false;
    hasQueuedSnapshotSave = false;
  };

  const startIncidentSession = async () => {
    const summary = await createIncidentSession({
      title: buildIncidentSessionTitle(),
    });
    mergeSummary(summary);
    await loadIncidentSession(summary.id);
  };

  const flushSaveIncidentSnapshot = async () => {
    if (isSnapshotSaveInFlight) {
      hasQueuedSnapshotSave = true;
      if (snapshotSavePromise) {
        await snapshotSavePromise;
      }
      return;
    }

    isSnapshotSaveInFlight = true;
    snapshotSavePromise = (async () => {
      let shouldContinue = true;
      while (shouldContinue) {
        hasQueuedSnapshotSave = false;

        const session = activeIncidentSession.value;
        const sessionId = activeIncidentSessionId.value;
        if (!session || !sessionId || session.snapshot.is_locked) {
          return;
        }

        try {
          const detail = await saveIncidentSessionSnapshot(
            sessionId,
            session.snapshot,
          );
          if (!detail || typeof detail.id !== 'string') {
            return;
          }

          if (
            activeIncidentSessionId.value !== sessionId ||
            activeIncidentSession.value?.id !== sessionId
          ) {
            return;
          }

          if (hasQueuedSnapshotSave && activeIncidentSession.value) {
            const latestLocalAnswers = cloneFormAnswers(
              activeIncidentSession.value.snapshot.form_answers,
            );
            activeIncidentSession.value = {
              ...detail,
              snapshot: {
                ...detail.snapshot,
                form_answers: latestLocalAnswers,
              },
            };
          } else {
            activeIncidentSession.value = detail;
          }

          mergeSummary({
            id: detail.id,
            title: detail.title,
            status: detail.status,
            created_at: detail.created_at,
            updated_at: detail.updated_at,
          });
        } catch (error) {
          console.error('保存事故报告会话失败。', error);
        }

        shouldContinue = hasQueuedSnapshotSave;
      }
    })().finally(() => {
      isSnapshotSaveInFlight = false;
      snapshotSavePromise = null;
    });

    await snapshotSavePromise;
  };

  const scheduleSaveIncidentSnapshot = () => {
    if (saveDebounceTimer !== null) {
      window.clearTimeout(saveDebounceTimer);
      saveDebounceTimer = null;
    }
    saveDebounceTimer = window.setTimeout(() => {
      void flushSaveIncidentSnapshot();
    }, 450);
  };

  const updateIncidentAnswers = (
    answers: Record<string, IncidentFormAnswer>,
  ) => {
    if (
      !activeIncidentSession.value ||
      activeIncidentSession.value.snapshot.is_locked
    ) {
      return;
    }
    activeIncidentSession.value = {
      ...activeIncidentSession.value,
      snapshot: {
        ...activeIncidentSession.value.snapshot,
        form_answers: cloneFormAnswers(answers),
      },
      status: 'draft',
    };
    if (isSnapshotSaveInFlight) {
      hasQueuedSnapshotSave = true;
    }
    scheduleSaveIncidentSnapshot();
  };

  const renameIncident = async (sessionId: string, title: string) => {
    const summary = await renameIncidentSession(sessionId, title);
    mergeSummary(summary);
    if (activeIncidentSession.value?.id === sessionId) {
      activeIncidentSession.value = {
        ...activeIncidentSession.value,
        title: summary.title,
        updated_at: summary.updated_at,
      };
    }
  };

  const deleteIncident = async (sessionId: string) => {
    await removeIncidentSession(sessionId);
    incidentSessionSummaries.value = incidentSessionSummaries.value.filter(
      (item) => item.id !== sessionId,
    );
    if (activeIncidentSessionId.value === sessionId) {
      clearActiveIncidentSession();
    }
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

  return {
    activeIncidentSession,
    activeIncidentSessionId,
    clearActiveIncidentSession,
    closeGenerationNotice,
    deleteIncident,
    downloadGeneratedIncidentAttachment,
    flushSaveIncidentSnapshot,
    generateIncident,
    generationState,
    incidentErrorMessage,
    incidentGenerationProgress,
    incidentGenerationTraceId,
    incidentSchema,
    incidentSessionSummaries,
    incidentSidebarSessions,
    isIncidentGenerating,
    loadIncidentSchema,
    loadIncidentSession,
    loadIncidentSessionSummaries,
    renameIncident,
    startIncidentSession,
    stopIncidentGeneration,
    updateIncidentAnswers,
  };
};
