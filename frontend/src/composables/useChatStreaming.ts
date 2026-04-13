import { computed, ref } from 'vue';
import { streamChatReply } from '../api/chat';
import type {
  ActiveGenerationState,
  ChatAttachment,
  ChatInteractionAnswer,
  ChatInteractionCard,
  ChatMessageNode,
  ChatRequestSnapshot,
  ChatToolStatus,
} from '../types/chat';
import { normalizeInteractionCard } from '../utils/interaction';

interface UseChatStreamingOptions {
  createAssistantVariant: (userMessageId: string) => ChatMessageNode;
  appendMessageContent: (messageId: string, chunk: string) => void;
  appendMessageAttachment: (
    messageId: string,
    attachment: ChatAttachment,
  ) => void;
  appendMessageToolStatus: (
    messageId: string,
    toolStatus: ChatToolStatus,
  ) => void;
  updateMessageTraceId: (messageId: string, traceId: string) => void;
  updateMessageInteraction: (
    messageId: string,
    interaction: ChatInteractionCard | null,
  ) => void;
  updateMessageContent: (messageId: string, content: string) => void;
  findMessageById: (messageId: string) => ChatMessageNode | null;
  scrollToBottom: () => void;
  persistCurrentSession: () => Promise<unknown>;
}

export const useChatStreaming = (options: UseChatStreamingOptions) => {
  const isLoading = ref(false);
  const isInteractionAwaitingUserInput = ref(false);
  const activeGeneration = ref<ActiveGenerationState | null>(null);
  const canSubmitInteraction = computed(() => {
    return !isLoading.value || isInteractionAwaitingUserInput.value;
  });

  const isMessageThinking = (message: ChatMessageNode) => {
    return (
      isLoading.value &&
      !isInteractionAwaitingUserInput.value &&
      message.role === 'assistant' &&
      message.id === activeGeneration.value?.assistantId &&
      !message.interaction &&
      !message.content.trim()
    );
  };

  const markGenerationStopped = () => {
    if (!activeGeneration.value?.assistantId) {
      return;
    }

    const activeMessage = options.findMessageById(
      activeGeneration.value.assistantId,
    );
    if (!activeMessage) {
      return;
    }

    if (activeMessage.content.trim()) {
      if (!activeMessage.content.endsWith('已停止输出')) {
        activeMessage.content += '\n\n已停止输出';
      }
      return;
    }

    activeMessage.content = '已停止输出';
  };

  const onStopGeneration = () => {
    const currentGeneration = activeGeneration.value;
    if (!currentGeneration?.controller) {
      return;
    }

    currentGeneration.controller.abort();

    if (isInteractionAwaitingUserInput.value) {
      options.updateMessageInteraction(currentGeneration.assistantId, null);
    } else {
      markGenerationStopped();
    }

    activeGeneration.value = null;
    isInteractionAwaitingUserInput.value = false;
    isLoading.value = false;
    void options.persistCurrentSession();
  };

  const finalizeAssistantFallback = (assistantId: string) => {
    const streamedAssistantMessage = options.findMessageById(assistantId);
    if (!streamedAssistantMessage) {
      return;
    }

    if (streamedAssistantMessage.content.trim()) {
      return;
    }

    if (streamedAssistantMessage.files?.length) {
      options.updateMessageContent(assistantId, '已生成文件，请下载查看。');
      return;
    }

    if (streamedAssistantMessage.interaction) {
      return;
    }

    options.updateMessageContent(
      assistantId,
      '模型已完成响应，但没有返回可显示的文本内容。',
    );
  };

  const streamIntoAssistantMessage = async (
    requestSnapshot: ChatRequestSnapshot,
    assistantMessageId: string,
    signal: AbortSignal,
  ) => {
    return streamChatReply(requestSnapshot, signal, (payload) => {
      const ollamaMessage =
        payload.message && typeof payload.message === 'object'
          ? payload.message
          : null;

      if (typeof ollamaMessage?.content === 'string' && ollamaMessage.content) {
        options.appendMessageContent(assistantMessageId, ollamaMessage.content);
        options.scrollToBottom();
      }

      if (payload.type === 'attachment' && payload.attachment) {
        options.appendMessageAttachment(assistantMessageId, payload.attachment);
        options.scrollToBottom();
      }

      if (payload.type === 'uploaded-attachment' && payload.attachment) {
        options.appendMessageAttachment(
          requestSnapshot.userMessageId,
          payload.attachment,
        );
      }

      if (
        payload.type === 'trace' &&
        payload.phase === 'start' &&
        typeof payload.trace_id === 'string' &&
        payload.trace_id.trim().length > 0
      ) {
        options.updateMessageTraceId(
          assistantMessageId,
          payload.trace_id.trim(),
        );
      }

      if (
        payload.type === 'tool-status' &&
        typeof payload.message === 'string'
      ) {
        options.appendMessageToolStatus(assistantMessageId, {
          id: `${assistantMessageId}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
          toolName: payload.tool_name,
          label: payload.label,
          message: payload.message,
          phase: payload.phase,
          createdAt: new Date().toISOString(),
        });
      }

      if (payload.type === 'interaction') {
        const nextInteraction =
          payload.status === 'completed'
            ? null
            : normalizeInteractionCard(payload.interaction);
        options.updateMessageInteraction(assistantMessageId, nextInteraction);
        if (payload.status === 'required') {
          options.appendMessageToolStatus(assistantMessageId, {
            id: `${assistantMessageId}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
            label: '交互向导',
            message: '等待你选择当前步骤后继续生成。',
            phase: 'finish',
            createdAt: new Date().toISOString(),
          });
        }
        if (payload.status === 'completed') {
          options.appendMessageToolStatus(assistantMessageId, {
            id: `${assistantMessageId}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
            label: '交互向导',
            message: '已完成向导信息采集，继续生成结果。',
            phase: 'finish',
            createdAt: new Date().toISOString(),
          });
        }
        options.scrollToBottom();
      }
    });
  };

  const shouldKeepGenerationOpen = (finishReason?: string) => {
    return finishReason === 'interaction_required';
  };

  const executeAssistantGeneration = async (
    requestSnapshot: ChatRequestSnapshot,
  ) => {
    const assistantNode = options.createAssistantVariant(
      requestSnapshot.userMessageId,
    );
    const abortController = new AbortController();

    isLoading.value = true;
    isInteractionAwaitingUserInput.value = false;
    activeGeneration.value = {
      assistantId: assistantNode.id,
      userMessageId: requestSnapshot.userMessageId,
      controller: abortController,
    };
    options.scrollToBottom();
    let keepGenerationOpen = false;

    try {
      const streamResult = await streamIntoAssistantMessage(
        requestSnapshot,
        assistantNode.id,
        abortController.signal,
      );

      if (shouldKeepGenerationOpen(streamResult.finishReason)) {
        const assistantMessage = options.findMessageById(assistantNode.id);
        if (!assistantMessage?.interaction) {
          options.appendMessageToolStatus(assistantNode.id, {
            id: `${assistantNode.id}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
            label: '交互向导',
            message: '向导步骤未成功返回，请重试或点击停止后重新提问。',
            phase: 'finish',
            createdAt: new Date().toISOString(),
          });
          finalizeAssistantFallback(assistantNode.id);
          return;
        }
        keepGenerationOpen = true;
        isInteractionAwaitingUserInput.value = true;
        return;
      }

      finalizeAssistantFallback(assistantNode.id);
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') {
        return;
      }

      const errorMessage =
        error instanceof Error ? error.message : '聊天请求失败，请稍后重试。';
      options.updateMessageContent(
        assistantNode.id,
        `请求失败：${errorMessage}`,
      );
    } finally {
      if (!keepGenerationOpen) {
        activeGeneration.value = null;
        isInteractionAwaitingUserInput.value = false;
        isLoading.value = false;
      }
      await options.persistCurrentSession();
    }
  };

  const executeAssistantInteraction = async (
    baseRequestSnapshot: ChatRequestSnapshot,
    assistantMessageId: string,
    interactionAnswer: ChatInteractionAnswer,
  ) => {
    const assistantNode = options.findMessageById(assistantMessageId);
    if (!assistantNode || assistantNode.role !== 'assistant') {
      return;
    }

    const abortController = new AbortController();
    isLoading.value = true;
    isInteractionAwaitingUserInput.value = false;
    activeGeneration.value = {
      assistantId: assistantMessageId,
      userMessageId: baseRequestSnapshot.userMessageId,
      controller: abortController,
    };

    const requestSnapshot: ChatRequestSnapshot = {
      ...baseRequestSnapshot,
      interactionAnswer,
    };
    let keepGenerationOpen = false;

    try {
      const streamResult = await streamIntoAssistantMessage(
        requestSnapshot,
        assistantMessageId,
        abortController.signal,
      );

      if (shouldKeepGenerationOpen(streamResult.finishReason)) {
        const assistantMessage = options.findMessageById(assistantMessageId);
        if (!assistantMessage?.interaction) {
          options.appendMessageToolStatus(assistantMessageId, {
            id: `${assistantMessageId}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
            label: '交互向导',
            message: '向导步骤未成功返回，请重试或点击停止后重新提问。',
            phase: 'finish',
            createdAt: new Date().toISOString(),
          });
          finalizeAssistantFallback(assistantMessageId);
          return;
        }
        keepGenerationOpen = true;
        isInteractionAwaitingUserInput.value = true;
        return;
      }

      finalizeAssistantFallback(assistantMessageId);
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') {
        return;
      }
      const errorMessage =
        error instanceof Error ? error.message : '交互提交失败，请稍后重试。';
      options.appendMessageToolStatus(assistantMessageId, {
        id: `${assistantMessageId}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        label: '交互步骤',
        message: `提交失败：${errorMessage}`,
        phase: 'finish',
        createdAt: new Date().toISOString(),
      });
    } finally {
      if (!keepGenerationOpen) {
        activeGeneration.value = null;
        isInteractionAwaitingUserInput.value = false;
        isLoading.value = false;
      }
      await options.persistCurrentSession();
    }
  };

  return {
    activeGeneration,
    canSubmitInteraction,
    executeAssistantGeneration,
    executeAssistantInteraction,
    isInteractionAwaitingUserInput,
    isLoading,
    isMessageThinking,
    onStopGeneration,
  };
};
