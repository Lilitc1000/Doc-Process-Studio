import { useChatStore } from '../stores/chat';
import { streamChatReply } from '../api/chat';
import type { ChatRequestSnapshot } from '../types/chat';

interface UseChatStreamingOptions {
  scrollToBottom: () => void;
  persistCurrentSession: () => Promise<unknown>;
}

export const useChatStreaming = (options: UseChatStreamingOptions) => {
  const chatStore = useChatStore();

  const markGenerationStopped = () => {
    if (!chatStore.activeGeneration?.assistant_id) {
      return;
    }

    const activeMessage = chatStore.findMessageById(
      chatStore.activeGeneration.assistant_id,
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
      '模型已完成响应，但没有返回可显示的文本内容。',
    );
  };

  const executeAssistantGeneration = async (
    requestSnapshot: ChatRequestSnapshot,
  ) => {
    const assistantNode = chatStore.createMessageNode({
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      parent_id: requestSnapshot.user_message_id,
    });
    const abortController = new AbortController();
    chatStore.isLoading = true;
    chatStore.activeGeneration = {
      assistant_id: assistantNode.id,
      user_message_id: requestSnapshot.user_message_id,
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
              requestSnapshot.user_message_id,
              payload.attachment,
            );
          }

          if (
            payload.type === 'trace' &&
            payload.phase === 'start' &&
            typeof payload.trace_id === 'string' &&
            payload.trace_id.trim().length > 0
          ) {
            chatStore.updateMessageTraceId(
              assistantNode.id,
              payload.trace_id.trim(),
            );
          }

          if (
            payload.type === 'tool-status' &&
            typeof payload.message === 'string'
          ) {
            chatStore.appendMessageToolStatus(assistantNode.id, {
              id: `${assistantNode.id}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
              tool_name: payload.tool_name,
              label: payload.label,
              message: payload.message,
              phase: payload.phase,
              created_at: new Date().toISOString(),
            });
          }
        },
      );

      finalizeAssistantFallback(assistantNode.id);
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') {
        return;
      }

      const errorMessage =
        error instanceof Error ? error.message : '聊天请求失败，请稍后重试。';
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
