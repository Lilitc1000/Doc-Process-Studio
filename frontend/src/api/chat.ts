import type { ChatRequestSnapshot } from '../types/chat';
import { parseStreamEvents } from '../utils/chat-stream';

export const streamChatReply = async (
  requestSnapshot: ChatRequestSnapshot,
  signal: AbortSignal,
  onEvent: (event: {
    type?: string;
    content?: string;
    message?: string;
  }) => void,
) => {
  const formData = new FormData();
  formData.append(
    'payload',
    JSON.stringify({
      conversation_id: requestSnapshot.conversationId,
      model: requestSnapshot.model,
      skill_id: requestSnapshot.skillId,
      messages: requestSnapshot.messages,
    }),
  );

  for (const file of requestSnapshot.files) {
    formData.append('files', file);
  }

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
        throw new Error(event.message || '聊天流返回了错误事件');
      }

      if (event.type === 'done') {
        return;
      }
    }
  }
};
