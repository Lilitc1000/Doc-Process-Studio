import { describe, expect, it } from 'vitest';
import {
  findNodeById,
  buildDisplayedMessages,
  getMessageSiblingIds,
  getMessageVersionCount,
  getMessageVersionIndex,
  resolveCurrentLeafMessageId,
} from '../../../src/utils/chat/message-tree';
import type { ChatMessageNode } from '../../../src/types/chat/chat';

function makeNode(
  id: string,
  role: ChatMessageNode['role'],
  content: string,
  parentId: string | null,
  childIds: string[] = [],
): ChatMessageNode {
  return {
    id,
    role,
    content,
    parentId,
    childIds,
    files: [],
    toolStatuses: [],
    timestamp: new Date(),
  };
}

describe('findNodeById', () => {
  it('finds existing node', () => {
    const node = makeNode('a', 'user', 'hello', null);
    expect(findNodeById({ a: node }, 'a')).toBe(node);
  });

  it('returns null for missing node', () => {
    expect(findNodeById({}, 'missing')).toBeNull();
  });
});

describe('buildDisplayedMessages', () => {
  it('returns fallback for empty tree', () => {
    const result = buildDisplayedMessages({
      messageNodes: {},
      rootChildIds: [],
      selectedRootChildId: null,
      selectedChildIdByParent: {},
      fallbackMessages: [],
    });
    expect(result).toHaveLength(0);
  });

  it('builds linear message chain', () => {
    const user = makeNode('u1', 'user', 'hello', null, ['a1']);
    const assistant = makeNode('a1', 'assistant', 'world', 'u1');
    const nodes = { u1: user, a1: assistant };

    const messages = buildDisplayedMessages({
      messageNodes: nodes,
      rootChildIds: ['u1'],
      selectedRootChildId: 'u1',
      selectedChildIdByParent: {},
      fallbackMessages: [],
    });
    expect(messages).toHaveLength(2);
    expect(messages[0].id).toBe('u1');
    expect(messages[1].id).toBe('a1');
  });
});

describe('getMessageSiblingIds', () => {
  it('returns root siblings for root message', () => {
    const u1 = makeNode('u1', 'user', 'hello', null);
    const u2 = makeNode('u2', 'user', 'hi', null);
    const nodes = { u1, u2 };
    expect(
      getMessageSiblingIds({
        messageNodes: nodes,
        rootChildIds: ['u1', 'u2'],
        messageId: 'u1',
      }),
    ).toEqual(['u1', 'u2']);
  });

  it('returns child siblings for non-root message', () => {
    const parent = makeNode('p', 'user', 'hello', null, ['a1', 'a2']);
    const a1 = makeNode('a1', 'assistant', 'world', 'p');
    const a2 = makeNode('a2', 'assistant', 'earth', 'p');
    const nodes = { p: parent, a1, a2 };
    expect(
      getMessageSiblingIds({
        messageNodes: nodes,
        rootChildIds: ['p'],
        messageId: 'a1',
      }),
    ).toEqual(['a1', 'a2']);
  });
});

describe('getMessageVersionCount', () => {
  it('counts siblings correctly', () => {
    const parent = makeNode('p', 'user', 'hello', null, ['a1', 'a2']);
    const a1 = makeNode('a1', 'assistant', 'world', 'p');
    const a2 = makeNode('a2', 'assistant', 'earth', 'p');
    const nodes = { p: parent, a1, a2 };
    expect(
      getMessageVersionCount({
        messageNodes: nodes,
        rootChildIds: ['p'],
        messageId: 'a1',
      }),
    ).toBe(2);
  });
});

describe('getMessageVersionIndex', () => {
  it('returns correct index', () => {
    const parent = makeNode('p', 'user', 'hello', null, ['a1', 'a2']);
    const a1 = makeNode('a1', 'assistant', 'world', 'p');
    const a2 = makeNode('a2', 'assistant', 'earth', 'p');
    const nodes = { p: parent, a1, a2 };
    expect(
      getMessageVersionIndex({
        messageNodes: nodes,
        rootChildIds: ['p'],
        messageId: 'a1',
      }),
    ).toBe(1);
    expect(
      getMessageVersionIndex({
        messageNodes: nodes,
        rootChildIds: ['p'],
        messageId: 'a2',
      }),
    ).toBe(2);
  });
});

describe('resolveCurrentLeafMessageId', () => {
  it('returns null for empty tree', () => {
    expect(resolveCurrentLeafMessageId([], [])).toBeNull();
  });

  it('resolves leaf node in linear chain', () => {
    const u1 = makeNode('u1', 'user', 'hello', null, ['a1']);
    const a1 = makeNode('a1', 'assistant', 'world', 'u1');
    expect(resolveCurrentLeafMessageId(['u1'], [u1, a1])).toBe('a1');
  });
});
