import { ref } from 'vue';
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
  const activeGeneration = ref<ActiveGenerationState | null>(null);

  const isMessageThinking = (message: ChatMessageNode) => {
    return (
      isLoading.value &&
      message.role === 'assistant' &&
      message.id === activeGeneration.value?.assistantId &&
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
    if (activeGeneration.value?.controller) {
      activeGeneration.value.controller.abort();
      markGenerationStopped();
      activeGeneration.value = null;
      isLoading.value = false;
    }
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
    await streamChatReply(requestSnapshot, signal, (payload) => {
      if (payload.type === 'delta' && payload.content) {
        options.appendMessageContent(assistantMessageId, payload.content);
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

      if (payload.type === 'tool-status' && payload.message) {
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
        options.scrollToBottom();
      }
    });
  };

  const executeAssistantGeneration = async (
    requestSnapshot: ChatRequestSnapshot,
  ) => {
    const assistantNode = options.createAssistantVariant(
      requestSnapshot.userMessageId,
    );
    const abortController = new AbortController();

    isLoading.value = true;
    activeGeneration.value = {
      assistantId: assistantNode.id,
      userMessageId: requestSnapshot.userMessageId,
      controller: abortController,
    };
    options.scrollToBottom();

    try {
      await streamIntoAssistantMessage(
        requestSnapshot,
        assistantNode.id,
        abortController.signal,
      );
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
      activeGeneration.value = null;
      isLoading.value = false;
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
    activeGeneration.value = {
      assistantId: assistantMessageId,
      userMessageId: baseRequestSnapshot.userMessageId,
      controller: abortController,
    };

    const requestSnapshot: ChatRequestSnapshot = {
      ...baseRequestSnapshot,
      interactionAnswer,
    };

    try {
      await streamIntoAssistantMessage(
        requestSnapshot,
        assistantMessageId,
        abortController.signal,
      );
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
      activeGeneration.value = null;
      isLoading.value = false;
      await options.persistCurrentSession();
    }
  };

  return {
    activeGeneration,
    executeAssistantGeneration,
    executeAssistantInteraction,
    isLoading,
    isMessageThinking,
    onStopGeneration,
  };
};
