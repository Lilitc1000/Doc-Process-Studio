import { describe, expect, it, beforeEach } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { useChatStore } from '../../../src/stores/chat';
import type {
  ChatMessageNode,
  ChatAttachment,
  ChatToolStatus,
} from '../../../src/types/chat/chat';

function makeNode(
  id: string,
  role: ChatMessageNode['role'],
  content: string,
  parentId: string | null = null,
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

function makeCreateNodePayload(
  overrides: Partial<Omit<ChatMessageNode, 'id' | 'childIds'>> & {
    id?: string;
  },
): Omit<ChatMessageNode, 'id' | 'childIds'> & { id?: string } {
  return {
    role: 'user',
    content: '',
    parentId: null,
    files: [],
    toolStatuses: [],
    timestamp: new Date(),
    ...overrides,
  };
}

describe('useChatStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  describe('初始状态', () => {
    it('isLoading 为 false', () => {
      const store = useChatStore();
      expect(store.isLoading).toBe(false);
    });

    it('inputText 为空', () => {
      const store = useChatStore();
      expect(store.inputText).toBe('');
    });

    it('selectedFiles 为空', () => {
      const store = useChatStore();
      expect(store.selectedFiles).toEqual([]);
    });

    it('selectedSkillIds 为空', () => {
      const store = useChatStore();
      expect(store.selectedSkillIds).toEqual([]);
    });

    it('editingMessageId 为 null', () => {
      const store = useChatStore();
      expect(store.editingMessageId).toBeNull();
    });

    it('conversationId 非空', () => {
      const store = useChatStore();
      expect(store.conversationId).toBeTruthy();
    });

    it('activeSessionId 为 null', () => {
      const store = useChatStore();
      expect(store.activeSessionId).toBeNull();
    });
  });

  describe('createMessageNode', () => {
    it('创建根消息节点', () => {
      const store = useChatStore();
      const node = store.createMessageNode(
        makeCreateNodePayload({ role: 'user', content: '你好' }),
      );

      expect(node.id).toBeTruthy();
      expect(node.role).toBe('user');
      expect(node.content).toBe('你好');
      expect(node.childIds).toEqual([]);
      expect(store.rootChildIds).toContain(node.id);
    });

    it('创建子消息节点', () => {
      const store = useChatStore();
      const parent = store.createMessageNode(
        makeCreateNodePayload({ role: 'user', content: '问题' }),
      );

      const child = store.createMessageNode(
        makeCreateNodePayload({
          role: 'assistant',
          content: '回答',
          parentId: parent.id,
        }),
      );

      expect(child.parentId).toBe(parent.id);
      expect(parent.childIds).toContain(child.id);
    });

    it('使用自定义 id', () => {
      const store = useChatStore();
      const node = store.createMessageNode(
        makeCreateNodePayload({
          id: 'custom-id',
          role: 'user',
          content: 'test',
        }),
      );
      expect(node.id).toBe('custom-id');
    });
  });

  describe('updateMessageContent', () => {
    it('更新消息内容', () => {
      const store = useChatStore();
      const node = store.createMessageNode(
        makeCreateNodePayload({ role: 'assistant', content: '初始内容' }),
      );

      store.updateMessageContent(node.id, '更新内容');
      expect(store.findMessageById(node.id)?.content).toBe('更新内容');
    });

    it('消息不存在时不报错', () => {
      const store = useChatStore();
      expect(() =>
        store.updateMessageContent('non-existent', 'test'),
      ).not.toThrow();
    });
  });

  describe('appendMessageContent', () => {
    it('追加消息内容', () => {
      const store = useChatStore();
      const node = store.createMessageNode(
        makeCreateNodePayload({ role: 'assistant', content: 'Hello' }),
      );

      store.appendMessageContent(node.id, ' World');
      expect(store.findMessageById(node.id)?.content).toBe('Hello World');
    });

    it('消息不存在时不报错', () => {
      const store = useChatStore();
      expect(() =>
        store.appendMessageContent('non-existent', 'test'),
      ).not.toThrow();
    });
  });

  describe('appendMessageAttachment', () => {
    it('添加新附件', () => {
      const store = useChatStore();
      const node = store.createMessageNode(
        makeCreateNodePayload({ role: 'assistant', content: '回复' }),
      );

      const attachment: ChatAttachment = {
        attachmentId: 'att-1',
        name: 'file.pdf',
        source: 'generated',
        sizeLabel: '10 KB',
        downloadUrl: '/api/attachments/att-1/download',
        mimeType: 'application/pdf',
        expiresAt: '2026-12-31T00:00:00Z',
      };

      store.appendMessageAttachment(node.id, attachment);
      const found1 = store.findMessageById(node.id)!;
      expect(found1.files).toHaveLength(1);
      expect(found1.files![0].name).toBe('file.pdf');
    });

    it('重复 attachmentId 的附件被替换', () => {
      const store = useChatStore();
      const node = store.createMessageNode(
        makeCreateNodePayload({ role: 'assistant', content: '回复' }),
      );

      const att1: ChatAttachment = {
        attachmentId: 'att-1',
        name: 'old.pdf',
        source: 'generated',
        sizeLabel: '10 KB',
        downloadUrl: '/api/old',
        mimeType: 'application/pdf',
        expiresAt: '2026-12-31T00:00:00Z',
      };

      const att2: ChatAttachment = {
        attachmentId: 'att-1',
        name: 'new.pdf',
        source: 'generated',
        sizeLabel: '20 KB',
        downloadUrl: '/api/new',
        mimeType: 'application/pdf',
        expiresAt: '2026-12-31T00:00:00Z',
      };

      store.appendMessageAttachment(node.id, att1);
      store.appendMessageAttachment(node.id, att2);
      const found2 = store.findMessageById(node.id)!;
      expect(found2.files).toHaveLength(1);
      expect(found2.files![0].name).toBe('new.pdf');
    });

    it('消息不存在时不报错', () => {
      const store = useChatStore();
      expect(() =>
        store.appendMessageAttachment('non-existent', {} as ChatAttachment),
      ).not.toThrow();
    });
  });

  describe('appendMessageToolStatus', () => {
    it('添加工具状态', () => {
      const store = useChatStore();
      const node = store.createMessageNode(
        makeCreateNodePayload({ role: 'assistant', content: '回复' }),
      );

      const status: ChatToolStatus = {
        id: 'tool-1',
        toolName: 'search',
        phase: 'start',
        label: '搜索中',
        message: '正在搜索...',
        createdAt: new Date().toISOString(),
      };

      store.appendMessageToolStatus(node.id, status);
      expect(store.findMessageById(node.id)?.toolStatuses).toHaveLength(1);
    });

    it('消息不存在时不报错', () => {
      const store = useChatStore();
      expect(() =>
        store.appendMessageToolStatus('non-existent', {} as ChatToolStatus),
      ).not.toThrow();
    });
  });

  describe('updateMessageTraceId', () => {
    it('更新 assistant 消息的 traceId', () => {
      const store = useChatStore();
      const node = store.createMessageNode(
        makeCreateNodePayload({ role: 'assistant', content: '回复' }),
      );

      store.updateMessageTraceId(node.id, 'trace-123');
      expect(store.findMessageById(node.id)?.traceId).toBe('trace-123');
    });

    it('不更新非 assistant 消息的 traceId', () => {
      const store = useChatStore();
      const node = store.createMessageNode(
        makeCreateNodePayload({ role: 'user', content: '问题' }),
      );

      store.updateMessageTraceId(node.id, 'trace-123');
      expect(store.findMessageById(node.id)?.traceId).toBeUndefined();
    });

    it('消息不存在时不报错', () => {
      const store = useChatStore();
      expect(() =>
        store.updateMessageTraceId('non-existent', 'trace-123'),
      ).not.toThrow();
    });
  });

  describe('resetEditingState', () => {
    it('重置编辑状态', () => {
      const store = useChatStore();
      store.editingMessageId = 'msg-1';
      store.editingDraftText = '草稿';
      store.editingDraftFiles = [
        { attachmentId: 'att-1', name: 'f.pdf' },
      ] as any;
      store.editingDraftSkillIds = ['skill-1'];

      store.resetEditingState();

      expect(store.editingMessageId).toBeNull();
      expect(store.editingDraftText).toBe('');
      expect(store.editingDraftFiles).toEqual([]);
      expect(store.editingDraftSkillIds).toEqual([]);
    });
  });

  describe('resetChatState', () => {
    it('重置所有聊天状态', () => {
      const store = useChatStore();
      store.createMessageNode(
        makeCreateNodePayload({ role: 'user', content: 'test' }),
      );
      store.inputText = '输入文本';
      store.selectedFiles = [new File([''], 'test.txt')];
      store.selectedSkillIds = ['skill-1'];

      store.resetChatState();

      expect(store.inputText).toBe('');
      expect(store.selectedFiles).toEqual([]);
      expect(store.selectedSkillIds).toEqual([]);
      expect(store.rootChildIds).toEqual([]);
      expect(store.editingMessageId).toBeNull();
    });
  });

  describe('displayedMessages', () => {
    it('无消息时显示欢迎消息', () => {
      const store = useChatStore();
      expect(store.displayedMessages.length).toBeGreaterThan(0);
      expect(store.displayedMessages[0].role).toBe('system');
    });

    it('有消息时显示消息链', () => {
      const store = useChatStore();
      store.createMessageNode(
        makeCreateNodePayload({ role: 'user', content: '问题' }),
      );
      expect(store.displayedMessages.some((m) => m.content === '问题')).toBe(
        true,
      );
    });
  });

  describe('isMessageThinking', () => {
    it('非加载状态返回 false', () => {
      const store = useChatStore();
      const node = makeNode('1', 'assistant', '');
      expect(store.isMessageThinking(node)).toBe(false);
    });
  });

  describe('isMessageStreaming', () => {
    it('非加载状态返回 false', () => {
      const store = useChatStore();
      const node = makeNode('1', 'assistant', '内容');
      expect(store.isMessageStreaming(node)).toBe(false);
    });
  });

  describe('canConfirmEdit', () => {
    it('无编辑内容时返回 false', () => {
      const store = useChatStore();
      expect(store.canConfirmEdit).toBe(false);
    });

    it('有编辑文本时返回 true', () => {
      const store = useChatStore();
      store.editingDraftText = '修改内容';
      expect(store.canConfirmEdit).toBe(true);
    });
  });

  describe('latestLiveToolStatus', () => {
    it('非加载状态返回 null', () => {
      const store = useChatStore();
      expect(store.latestLiveToolStatus).toBeNull();
    });
  });

  describe('buildTitleSourceMessages', () => {
    it('返回非系统消息的内容片段', () => {
      const store = useChatStore();
      store.createMessageNode(
        makeCreateNodePayload({ role: 'user', content: '用户消息' }),
      );
      const titles = store.buildTitleSourceMessages();
      expect(titles).toContain('用户消息');
    });
  });

  describe('hydrateSessionSnapshot', () => {
    it('从快照恢复消息状态', () => {
      const store = useChatStore();
      store.hydrateSessionSnapshot({
        messageNodes: [
          {
            id: 'msg-1',
            role: 'user',
            content: '快照消息',
            traceId: null,
            apiContent: null,
            requestSkillIds: [],
            files: [],
            toolStatuses: [],
            timestamp: '2026-01-01T00:00:00Z',
            parentId: null,
            childIds: [],
          },
        ],
        rootChildIds: ['msg-1'],
        selectedRootChildId: 'msg-1',
        selectedChildIdByParent: {},
        selectedModel: 'qwen3:8b',
        selectedRerankerModel: 'qwen3:8b',
      });

      expect(store.findMessageById('msg-1')).toBeDefined();
      expect(store.findMessageById('msg-1')?.content).toBe('快照消息');
    });
  });

  describe('buildSessionSnapshotPayload', () => {
    it('构建快照包含消息节点', () => {
      const store = useChatStore();
      store.createMessageNode(
        makeCreateNodePayload({ role: 'user', content: '测试' }),
      );

      const snapshot = store.buildSessionSnapshotPayload(
        'qwen3:8b',
        'qwen3:8b',
      );
      expect(snapshot.messageNodes.length).toBeGreaterThan(0);
      expect(snapshot.selectedModel).toBe('qwen3:8b');
      expect(snapshot.selectedRerankerModel).toBe('qwen3:8b');
    });
  });

  describe('mergeSessionSummary', () => {
    it('添加新会话摘要', () => {
      const store = useChatStore();
      store.mergeSessionSummary({
        id: 'session-1',
        title: '测试会话',
        createdAt: '2026-01-01T00:00:00Z',
        updatedAt: '2026-01-02T00:00:00Z',
        selectedModel: 'qwen3:8b',
      });

      expect(store.sessionSummaries).toHaveLength(1);
      expect(store.sessionSummaries[0].id).toBe('session-1');
    });

    it('更新已有会话摘要', () => {
      const store = useChatStore();
      store.mergeSessionSummary({
        id: 'session-1',
        title: '旧标题',
        createdAt: '2026-01-01T00:00:00Z',
        updatedAt: '2026-01-01T00:00:00Z',
      });

      store.mergeSessionSummary({
        id: 'session-1',
        title: '新标题',
        createdAt: '2026-01-01T00:00:00Z',
        updatedAt: '2026-01-03T00:00:00Z',
      });

      expect(store.sessionSummaries).toHaveLength(1);
      expect(store.sessionSummaries[0].title).toBe('新标题');
    });

    it('按 updatedAt 降序排列', () => {
      const store = useChatStore();
      store.mergeSessionSummary({
        id: 'session-1',
        title: '旧会话',
        createdAt: '2026-01-01T00:00:00Z',
        updatedAt: '2026-01-01T00:00:00Z',
      });

      store.mergeSessionSummary({
        id: 'session-2',
        title: '新会话',
        createdAt: '2026-01-02T00:00:00Z',
        updatedAt: '2026-01-03T00:00:00Z',
      });

      expect(store.sessionSummaries[0].id).toBe('session-2');
    });
  });

  describe('switchMessageVersion', () => {
    it('加载中不切换版本', () => {
      const store = useChatStore();
      store.isLoading = true;
      store.switchMessageVersion('msg-1', 1);
    });
  });

  describe('bumpSessionViewKey', () => {
    it('递增 sessionViewKey', () => {
      const store = useChatStore();
      const initialKey = store.sessionViewKey;
      store.bumpSessionViewKey();
      expect(store.sessionViewKey).toBe(initialKey + 1);
    });
  });

  describe('resetConversationState', () => {
    it('重置会话 ID', () => {
      const store = useChatStore();
      const oldId = store.conversationId;
      store.resetConversationState();
      expect(store.conversationId).not.toBe(oldId);
      expect(store.activeSessionId).toBeNull();
    });
  });
});
