import { useChatStore } from '../../../stores/chat';
import { streamChatReply } from '../../../api/chat-stream';
import type { ChatRequestSnapshot } from '../../../types/chat/chat';
import { isRequestCanceled } from '../../../utils/common/cancel';
import { getErrorMessage } from '../../../utils/common/error';

interface UseChatStreamingOptions {
  scrollToBottom: () => void;
  persistCurrentSession: () => Promise<unknown>;
}

export const useChatStreaming = (options: UseChatStreamingOptions) => {
  const chatStore = useChatStore();

  const markGenerationStopped = () => {
    if (!chatStore.activeGeneration?.assistantId) {
      return;
    }

    const activeMessage = chatStore.findMessageById(
      chatStore.activeGeneration.assistantId,
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
    const currentGeneration = chatStore.activeGeneration;
    if (!currentGeneration?.controller) {
      return;
    }
    currentGeneration.controller.abort();
    markGenerationStopped();
    chatStore.activeGeneration = null;
    chatStore.isLoading = false;
    void options.persistCurrentSession();
  };

  const finalizeAssistantFallback = (assistantId: string) => {
    const streamedAssistantMessage = chatStore.findMessageById(assistantId);
    if (!streamedAssistantMessage) {
      return;
    }

    if (streamedAssistantMessage.content.trim()) {
      return;
    }

    if (streamedAssistantMessage.files?.length) {
      chatStore.updateMessageContent(assistantId, '已生成文件，请下载查看。');
      return;
    }

    chatStore.updateMessageContent(
      assistantId,
      '抱歉，我暂时无法回答这个问题。',
    );
  };

  const executeAssistantGeneration = async (
    requestSnapshot: ChatRequestSnapshot,
  ) => {
    const assistantNode = chatStore.createMessageNode({
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      parentId: requestSnapshot.userMessageId,
    });
    const abortController = new AbortController();
    chatStore.isLoading = true;
    chatStore.activeGeneration = {
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
          const ollamaMessage =
            payload.message && typeof payload.message === 'object'
              ? payload.message
              : null;

          if (
            typeof ollamaMessage?.content === 'string' &&
            ollamaMessage.content
          ) {
            chatStore.appendMessageContent(
              assistantNode.id,
              ollamaMessage.content,
            );
            options.scrollToBottom();
          }

          if (payload.type === 'attachment' && payload.attachment) {
            chatStore.appendMessageAttachment(
              assistantNode.id,
              payload.attachment,
            );
            options.scrollToBottom();
          }

          if (payload.type === 'uploaded-attachment' && payload.attachment) {
            chatStore.appendMessageAttachment(
              requestSnapshot.userMessageId,
              payload.attachment,
            );
          }

          if (
            payload.type === 'trace' &&
            payload.phase === 'start' &&
            typeof payload.traceId === 'string' &&
            payload.traceId.trim().length > 0
          ) {
            chatStore.updateMessageTraceId(
              assistantNode.id,
              payload.traceId.trim(),
            );
          }

          if (
            payload.type === 'tool-status' &&
            typeof payload.message === 'string'
          ) {
            chatStore.appendMessageToolStatus(assistantNode.id, {
              id: `${assistantNode.id}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
              toolName: payload.toolName,
              label: payload.label,
              message: payload.message,
              phase: payload.phase,
              createdAt: new Date().toISOString(),
            });
          }
        },
      );

      finalizeAssistantFallback(assistantNode.id);
    } catch (error) {
      if (isRequestCanceled(error)) {
        return;
      }

      const errorMessage = getErrorMessage(error, '聊天请求失败，请稍后重试。');
      chatStore.updateMessageContent(
        assistantNode.id,
        `请求失败：${errorMessage}`,
      );
    } finally {
      chatStore.activeGeneration = null;
      chatStore.isLoading = false;
      await options.persistCurrentSession();
    }
  };

  return {
    executeAssistantGeneration,
    onStopGeneration,
  };
};
