import { ref } from 'vue';
import { fetchAgentTraceReplay } from '../../api/trace';
import type { TraceReplayPayload } from '../../types/common/trace';

interface UseTraceModalOptions {
  showCopyToast: (message: string, options?: { title?: string }) => void;
}

export const useTraceModal = (options: UseTraceModalOptions) => {
  const isTraceModalVisible = ref(false);
  const activeTraceId = ref('');
  const activeTracePayload = ref<TraceReplayPayload | null>(null);
  const isTraceModalLoading = ref(false);
  const traceModalErrorMessage = ref('');

  const waitFor = (delayMs: number) => {
    return new Promise<void>((resolve) => {
      window.setTimeout(() => {
        resolve();
      }, delayMs);
    });
  };

  const loadTracePayloadWithRetry = async (
    traceId: string,
    retryOptions?: {
      maxAttempts?: number;
      delayMs?: number;
    },
  ) => {
    const maxAttempts = Math.max(1, retryOptions?.maxAttempts ?? 5);
    const delayMs = Math.max(50, retryOptions?.delayMs ?? 300);

    for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
      try {
        const response = await fetchAgentTraceReplay(traceId);
        return response.payload;
      } catch (error) {
        const status = (error as { response?: { status?: number } } | null)
          ?.response?.status;
        const isLastAttempt = attempt >= maxAttempts;
        if (status !== 404 || isLastAttempt) {
          throw error;
        }
        await waitFor(delayMs);
      }
    }

    return null;
  };

  const openTraceModalByTraceId = async (traceId: string) => {
    const normalizedTraceId = traceId.trim();
    if (!normalizedTraceId) {
      return;
    }

    activeTraceId.value = normalizedTraceId;
    activeTracePayload.value = null;
    traceModalErrorMessage.value = '';
    isTraceModalLoading.value = true;
    isTraceModalVisible.value = true;

    try {
      const payload = await loadTracePayloadWithRetry(normalizedTraceId);
      activeTracePayload.value = payload;
    } catch (error) {
      traceModalErrorMessage.value =
        error instanceof Error
          ? error.message
          : '加载链路回放失败，请稍后重试。';
    } finally {
      isTraceModalLoading.value = false;
    }
  };

  const closeTraceModal = () => {
    isTraceModalVisible.value = false;
  };

  const retryTraceModalLoad = async () => {
    if (!activeTraceId.value.trim()) {
      return;
    }
    await openTraceModalByTraceId(activeTraceId.value);
  };

  const copyTraceId = async () => {
    const traceId = activeTraceId.value.trim();
    if (!traceId) {
      return;
    }
    await navigator.clipboard.writeText(traceId);
    options.showCopyToast(traceId, { title: 'Trace ID 已复制' });
  };

  return {
    activeTraceId,
    activeTracePayload,
    closeTraceModal,
    copyTraceId,
    isTraceModalLoading,
    isTraceModalVisible,
    openTraceModalByTraceId,
    retryTraceModalLoad,
    traceModalErrorMessage,
  };
};
