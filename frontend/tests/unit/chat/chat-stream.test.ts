import { describe, expect, it } from 'vitest';
import { parseStreamEvents } from '../../../src/utils/chat/chat-stream';

describe('parseStreamEvents', () => {
  it('parses single SSE event', () => {
    const buffer = 'data: {"type":"content","data":"hello"}\n\n';
    const result = parseStreamEvents(buffer);
    expect(result.events).toHaveLength(1);
    expect(result.events[0]).toEqual({ type: 'content', data: 'hello' });
    expect(result.rest).toBe('');
  });

  it('parses multiple SSE events', () => {
    const buffer =
      'data: {"type":"content","data":"hi"}\n\ndata: {"type":"done"}\n\n';
    const result = parseStreamEvents(buffer);
    expect(result.events).toHaveLength(2);
    expect(result.events[0]).toEqual({ type: 'content', data: 'hi' });
    expect(result.events[1]).toEqual({ type: 'done' });
  });

  it('handles incomplete event as rest', () => {
    const buffer =
      'data: {"type":"content","data":"hello"}\n\ndata: {"type":"don';
    const result = parseStreamEvents(buffer);
    expect(result.events).toHaveLength(1);
    expect(result.rest).toBe('data: {"type":"don');
  });

  it('skips [DONE] marker', () => {
    const buffer = 'data: [DONE]\n\n';
    const result = parseStreamEvents(buffer);
    expect(result.events).toHaveLength(0);
  });

  it('skips malformed JSON', () => {
    const buffer = 'data: not-json\n\n';
    const result = parseStreamEvents(buffer);
    expect(result.events).toHaveLength(0);
  });

  it('handles empty buffer', () => {
    const result = parseStreamEvents('');
    expect(result.events).toHaveLength(0);
    expect(result.rest).toBe('');
  });
});
