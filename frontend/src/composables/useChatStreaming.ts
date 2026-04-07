import { ref } from 'vue';
import { streamChatReply } from '../api/chat';
import type {
  ActiveGenerationState,
  ChatAttachment,
  ChatMessageNode,
  ChatRequestSnapshot,
  ChatToolStatus,
} from '../types/chat';

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
      await streamChatReply(
        requestSnapshot,
        abortController.signal,
        (payload) => {
          if (payload.type === 'delta' && payload.content) {
            options.appendMessageContent(assistantNode.id, payload.content);
            options.scrollToBottom();
          }

          if (payload.type === 'attachment' && payload.attachment) {
            options.appendMessageAttachment(
              assistantNode.id,
              payload.attachment,
            );
            options.scrollToBottom();
          }

          if (payload.type === 'uploaded-attachment' && payload.attachment) {
            options.appendMessageAttachment(
              requestSnapshot.userMessageId,
              payload.attachment,
            );
          }

          if (payload.type === 'tool-status' && payload.message) {
            options.appendMessageToolStatus(assistantNode.id, {
              id: `${assistantNode.id}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
              toolName: payload.tool_name,
              label: payload.label,
              message: payload.message,
              phase: payload.phase,
              createdAt: new Date().toISOString(),
            });
          }
        },
      );

      const streamedAssistantMessage = options.findMessageById(
        assistantNode.id,
      );
      if (
        streamedAssistantMessage &&
        !streamedAssistantMessage.content.trim()
      ) {
        options.updateMessageContent(
          assistantNode.id,
          streamedAssistantMessage.files?.length
            ? '已生成文件，请下载查看。'
            : '模型已完成响应，但没有返回可显示的文本内容。',
        );
      }
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

  return {
    activeGeneration,
    executeAssistantGeneration,
    isLoading,
    isMessageThinking,
    onStopGeneration,
  };
};
