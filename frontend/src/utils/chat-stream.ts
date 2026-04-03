import type { ChatStreamEvent } from '../types/chat';

export const parseStreamEvents = (buffer: string) => {
  const rawChunks = buffer.split('\n\n');
  const rest = rawChunks.pop() ?? '';
  const events: ChatStreamEvent[] = [];

  for (const rawChunk of rawChunks) {
    const lines = rawChunk
      .split('\n')
      .map((line) => line.trim())
      .filter((line) => line.startsWith('data:'));

    for (const line of lines) {
      const payloadText = line.slice(5).trim();
      if (!payloadText) {
        continue;
      }

      try {
        events.push(JSON.parse(payloadText) as ChatStreamEvent);
      } catch {
        // 忽略无法解析的事件片段，避免流式输出中断。
      }
    }
  }

  return {
    events,
    rest,
  };
};
