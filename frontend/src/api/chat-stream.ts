import type { ChatRequestSnapshot, ChatStreamEvent } from '../types/chat/chat';
import { parseStreamEvents } from '../utils/chat/chat-stream';

export const streamChatReply = async (
  requestSnapshot: ChatRequestSnapshot,
  signal: AbortSignal,
  onEvent: (event: ChatStreamEvent) => void,
) => {
  const formData = new FormData();
  formData.append(
    'payload',
    JSON.stringify({
      user_message_id: requestSnapshot.userMessageId,
      conversation_id: requestSnapshot.conversationId,
      model: requestSnapshot.model,
      reranker_model: requestSnapshot.rerankerModel,
      selected_skill_ids: requestSnapshot.selectedSkillIds,
      messages: requestSnapshot.messages,
      attachment_ids: requestSnapshot.attachmentIds,
    }),
  );

  for (const file of requestSnapshot.files) {
    formData.append('files', file);
  }

  // 使用原生 fetch 而非 axios，因为 SSE 流式接口需要 ReadableStream 逐块读取，
  // axios 不原生支持 ReadableStream，无法实现实时流式输出。
  const response = await fetch('/api/chat/stream', {
    method: 'POST',
    signal,
    body: formData,
  });

  if (!response.ok || !response.body) {
    throw new Error(`聊天接口请求失败，状态码：${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';
  let isDone = false;
  let finishReason: string | undefined;

  while (!isDone) {
    const { value, done } = await reader.read();
    isDone = done;
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const parsed = parseStreamEvents(buffer);
    buffer = parsed.rest;

    for (const event of parsed.events) {
      onEvent(event);

      if (event.type === 'error') {
        const errorMessage =
          typeof event.message === 'string'
            ? event.message
            : '聊天流返回了错误事件';
        throw new Error(errorMessage);
      }

      if (event.done === true) {
        finishReason = event.doneReason;
        return {
          finishReason,
        };
      }
    }
  }

  return {
    finishReason,
  };
};
