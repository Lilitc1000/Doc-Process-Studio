import { ref, type Ref } from 'vue';
import {
  fetchSessionDetail,
  fetchSessionSummaries,
  removeSession,
  renameSession,
  saveSession,
} from '../api/sessions';
import type { ChatMessageNode } from '../types/chat';
import type {
  ChatSessionDetail,
  ChatSessionSnapshotPayload,
  ChatSessionSummary,
} from '../types/session';
import { createConversationId } from '../utils/ids';

interface UseChatSessionsOptions {
  messageNodes: Ref<Record<string, ChatMessageNode>>;
  rootChildIds: Ref<string[]>;
  selectedRootChildId: Ref<string | null>;
  selectedChildIdByParent: Ref<Record<string, string>>;
  selectedModel: Ref<string>;
  selectedRerankerModel: Ref<string>;
  isChatLocked: () => boolean;
  getDisplayedMessages: () => ChatMessageNode[];
  resetEditingState: () => void;
  afterSessionLoaded?: () => Promise<void> | void;
  onDeleteActiveSession?: () => void;
}

export const useChatSessions = (options: UseChatSessionsOptions) => {
  const sessionSummaries = ref<ChatSessionSummary[]>([]);
  const activeSessionId = ref<string | null>(null);
  const conversationId = ref(createConversationId());
  const sessionViewKey = ref(0);

  const bumpSessionViewKey = () => {
    sessionViewKey.value += 1;
  };

  const mapSessionSummary = (
    session: ChatSessionSummary | ChatSessionDetail,
  ) => {
    return {
      id: session.id,
      title: session.title,
      created_at: session.created_at,
      updated_at: session.updated_at,
      selected_model: session.selected_model,
      selected_reranker_model: session.selected_reranker_model ?? null,
    } satisfies ChatSessionSummary;
  };

  const mergeSessionSummary = (
    session: ChatSessionSummary | ChatSessionDetail,
  ) => {
    const nextSessions = sessionSummaries.value.filter((item) => {
      return item.id !== session.id;
    });
    nextSessions.unshift(mapSessionSummary(session));
    nextSessions.sort((left, right) => {
      return (
        new Date(right.updated_at).getTime() -
        new Date(left.updated_at).getTime()
      );
    });
    sessionSummaries.value = nextSessions;
  };

  const buildSessionSnapshotPayload = (): ChatSessionSnapshotPayload => {
    return {
      message_nodes: Object.values(options.messageNodes.value).map(
        (message) => ({
          id: message.id,
          role: message.role,
          content: message.content,
          trace_id: message.trace_id ?? null,
          api_content: message.api_content ?? null,
          request_skill_ids: message.request_skill_ids ?? [],
          files: message.files ?? [],
          tool_statuses: message.tool_statuses ?? [],
          timestamp: message.timestamp.toISOString(),
          parent_id: message.parent_id,
          child_ids: [...message.child_ids],
        }),
      ),
      root_child_ids: [...options.rootChildIds.value],
      selected_root_child_id: options.selectedRootChildId.value,
      selected_child_id_by_parent: { ...options.selectedChildIdByParent.value },
      selected_model: options.selectedModel.value,
      selected_reranker_model: options.selectedRerankerModel.value,
    };
  };

  const buildTitleSourceMessages = () => {
    return options
      .getDisplayedMessages()
      .filter((message) => message.role !== 'system')
      .slice(0, 4)
      .map((message) => message.content.trim())
      .filter((content) => content.length > 0)
      .map((content) => content.slice(0, 180));
  };

  const hydrateSessionSnapshot = (snapshot: ChatSessionSnapshotPayload) => {
    const nextMessageNodes: Record<string, ChatMessageNode> = {};
    for (const message of snapshot.message_nodes) {
      nextMessageNodes[message.id] = {
        id: message.id,
        role: message.role,
        content: message.content,
        trace_id: message.trace_id ?? undefined,
        api_content: message.api_content ?? undefined,
        request_skill_ids: message.request_skill_ids ?? [],
        files: message.files ?? [],
        tool_statuses: message.tool_statuses ?? [],
        timestamp: new Date(message.timestamp),
        parent_id: message.parent_id,
        child_ids: [...message.child_ids],
        request_files: [],
      };
    }

    options.messageNodes.value = nextMessageNodes;
    options.rootChildIds.value = [...snapshot.root_child_ids];
    options.selectedRootChildId.value = snapshot.selected_root_child_id;
    options.selectedChildIdByParent.value = {
      ...snapshot.selected_child_id_by_parent,
    };
    options.selectedModel.value = snapshot.selected_model;
    options.selectedRerankerModel.value =
      snapshot.selected_reranker_model ?? snapshot.selected_model;
    options.resetEditingState();
  };

  const loadSessionSummaries = async () => {
    try {
      const sessions = await fetchSessionSummaries();
      sessionSummaries.value = [...sessions].sort((left, right) => {
        return (
          new Date(right.updated_at).getTime() -
          new Date(left.updated_at).getTime()
        );
      });
    } catch (error) {
      console.error('加载历史会话列表失败。', error);
    }
  };

  const persistCurrentSession = async (optionsWithTitle?: {
    title?: string;
  }) => {
    if (options.rootChildIds.value.length === 0) {
      return null;
    }

    const sessionId = activeSessionId.value ?? conversationId.value;
    activeSessionId.value = sessionId;

    try {
      const sessionSummary = await saveSession(sessionId, {
        title: optionsWithTitle?.title ?? '',
        title_source_messages: buildTitleSourceMessages(),
        snapshot: buildSessionSnapshotPayload(),
      });
      mergeSessionSummary(sessionSummary);
      return sessionSummary;
    } catch (error) {
      console.error('保存历史会话失败。', error);
      return null;
    }
  };

  const loadChatSession = async (sessionId: string) => {
    if (options.isChatLocked()) {
      return;
    }

    try {
      const sessionDetail = await fetchSessionDetail(sessionId);
      hydrateSessionSnapshot(sessionDetail.snapshot);
      activeSessionId.value = sessionDetail.id;
      conversationId.value = sessionDetail.id;
      mergeSessionSummary(sessionDetail);
      bumpSessionViewKey();
      await options.afterSessionLoaded?.();
    } catch (error) {
      console.error('加载历史会话失败。', error);
    }
  };

  const renameChatSession = async (sessionId: string, title: string) => {
    try {
      const sessionSummary = await renameSession(sessionId, title);
      mergeSessionSummary(sessionSummary);
    } catch (error) {
      console.error('修改历史会话标题失败。', error);
    }
  };

  const deleteChatSession = async (sessionId: string) => {
    try {
      await removeSession(sessionId);
      sessionSummaries.value = sessionSummaries.value.filter((session) => {
        return session.id !== sessionId;
      });

      if (activeSessionId.value === sessionId) {
        options.onDeleteActiveSession?.();
      }
    } catch (error) {
      console.error('删除历史会话失败。', error);
    }
  };

  const resetConversationState = () => {
    activeSessionId.value = null;
    conversationId.value = createConversationId();
    bumpSessionViewKey();
  };

  return {
    activeSessionId,
    conversationId,
    deleteChatSession,
    loadChatSession,
    loadSessionSummaries,
    persistCurrentSession,
    renameChatSession,
    resetConversationState,
    sessionSummaries,
    sessionViewKey,
  };
};
