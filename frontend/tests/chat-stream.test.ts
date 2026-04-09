import { describe, expect, it } from 'vitest';
import { parseStreamEvents } from '../src/utils/chat-stream';

describe('chat stream parser', () => {
  it('解析完整事件并保留未完成缓冲区', () => {
    const parsed = parseStreamEvents(
      [
        'data: {"model":"qwen3","message":{"role":"assistant","content":"你好"},"done":false}',
        '',
        'data: {"model":"qwen3","message":{"role":"assistant","content":""},"done":true,"done_reason":"stop"}',
        '',
        'data: {"model":"qwen3","message":{"role":"assistant","content":"未结束',
      ].join('\n'),
    );

    expect(parsed.events).toEqual([
      {
        model: 'qwen3',
        message: { role: 'assistant', content: '你好' },
        done: false,
      },
      {
        model: 'qwen3',
        message: { role: 'assistant', content: '' },
        done: true,
        done_reason: 'stop',
      },
    ]);
    expect(parsed.rest).toBe(
      'data: {"model":"qwen3","message":{"role":"assistant","content":"未结束',
    );
  });
});
