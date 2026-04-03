import { describe, expect, it } from 'vitest';
import { parseStreamEvents } from '../src/utils/chat-stream';

describe('chat stream parser', () => {
  it('解析完整事件并保留未完成缓冲区', () => {
    const parsed = parseStreamEvents(
      [
        'data: {"type":"delta","content":"你好"}',
        '',
        'data: {"type":"done"}',
        '',
        'data: {"type":"delta","content":"未结束',
      ].join('\n'),
    );

    expect(parsed.events).toEqual([
      { type: 'delta', content: '你好' },
      { type: 'done' },
    ]);
    expect(parsed.rest).toBe('data: {"type":"delta","content":"未结束');
  });
});
