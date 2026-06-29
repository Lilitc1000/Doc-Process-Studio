import { describe, expect, it } from 'vitest';
import { createConversationId, createMessageId } from '@shared/utils/ids';

describe('createConversationId', () => {
  it('返回非空字符串', () => {
    const id = createConversationId();
    expect(id).toBeTruthy();
    expect(typeof id).toBe('string');
  });

  it('每次调用返回不同的 ID', () => {
    const id1 = createConversationId();
    const id2 = createConversationId();
    expect(id1).not.toBe(id2);
  });

  it('crypto.randomUUID 可用时返回 UUID 格式', () => {
    const id = createConversationId();
    expect(id).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/,
    );
  });

  it('crypto.randomUUID 不可用时返回 fallback 格式', () => {
    const originalRandomUUID = globalThis.crypto.randomUUID;
    Object.defineProperty(globalThis.crypto, 'randomUUID', {
      value: undefined,
      configurable: true,
    });

    const id = createConversationId();
    expect(id).toContain('conversation-');

    Object.defineProperty(globalThis.crypto, 'randomUUID', {
      value: originalRandomUUID,
      configurable: true,
    });
  });
});

describe('createMessageId', () => {
  it('返回非空字符串', () => {
    const id = createMessageId();
    expect(id).toBeTruthy();
    expect(typeof id).toBe('string');
  });

  it('每次调用返回不同的 ID', () => {
    const id1 = createMessageId();
    const id2 = createMessageId();
    expect(id1).not.toBe(id2);
  });

  it('crypto.randomUUID 可用时返回 UUID 格式', () => {
    const id = createMessageId();
    expect(id).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/,
    );
  });

  it('crypto.randomUUID 不可用时返回 fallback 格式', () => {
    const originalRandomUUID = globalThis.crypto.randomUUID;
    Object.defineProperty(globalThis.crypto, 'randomUUID', {
      value: undefined,
      configurable: true,
    });

    const id = createMessageId();
    expect(id).toContain('message-');

    Object.defineProperty(globalThis.crypto, 'randomUUID', {
      value: originalRandomUUID,
      configurable: true,
    });
  });
});
