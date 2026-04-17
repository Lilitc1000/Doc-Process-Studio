import { defineStore } from 'pinia';
import { computed, ref } from 'vue';
import type {
  ActiveGenerationState,
  ChatAttachment,
  ChatEditAttachment,
  ChatMessageNode,
  ChatToolStatus,
} from '../types/chat';
import type {
  ChatSessionSnapshotPayload,
  ChatSessionSummary,
} from '../types/session';
import {
  buildDisplayedMessages,
  canSwitchMessageVersion as canSwitchMessageVersionInTree,
  collectPersistedUploadedAttachmentIdsFromPath,
  findAdjacentVersionNodes,
  findNodeById as findNodeByIdInTree,
  getMessagePathToNode,
  getMessageVersionCount as getMessageVersionCountInTree,
  getMessageVersionIndex as getMessageVersionIndexInTree,
  resolveCurrentLeafMessageId,
  resolveLastRoleMessageId,
  resolveTargetVersionMessageId,
} from '../utils/message-tree';
import { prewarmRenderedContentCache } from '../utils/render-markdown';
import { createConversationId, createMessageId } from '../utils/ids';

const WELCOME_MESSAGES: ChatMessageNode[] = [
  {
    id: 'welcome-1',
    role: 'system',
    content: [
      '### 欢迎来到文档处理助手',
      '',
      '**上传一份文档，或者直接问我一个问题。**',
      '',
      '我会根据你选择的处理方式和模型，帮你更快地读懂、提炼和整理内容。',
      '',
      '你可以试试这些开始方式：',
      '',
      '- 上传 PDF、Word、Excel、PPT 等常见文档',
      '- 直接提问，快速拿到摘要、答案或重点结论',
      '- 围绕同一批文件连续追问，进行多轮对话',
      '- 让我输出提纲、表格、要点或结构化结果',
    ].join('\n'),
    timestamp: new Date(),
    parent_id: null,
    child_ids: [],
  },
];

export const useChatStore = defineStore('chat', () => {
  const messageNodes = ref<Record<string, ChatMessageNode>>({});
  const rootChildIds = ref<string[]>([]);
  const selectedRootChildId = ref<string | null>(null);
  const selectedChildIdByParent = ref<Record<string, string>>({});
  const activeSessionId = ref<string | null>(null);
  const conversationId = ref(createConversationId());
  const sessionSummaries = ref<ChatSessionSummary[]>([]);
  const sessionViewKey = ref(0);
  const isLoading = ref(false);
  const activeGeneration = ref<ActiveGenerationState | null>(null);
  const inputText = ref('');
  const selectedFiles = ref<File[]>([]);
  const selectedSkillIds = ref<string[]>([]);
  const editingMessageId = ref<string | null>(null);
  const editingDraftText = ref('');
  const editingDraftFiles = ref<ChatEditAttachment[]>([]);
  const editingDraftSkillIds = ref<string[]>([]);

  const displayedMessages = computed(() => {
    return buildDisplayedMessages({
      messageNodes: messageNodes.value,
      rootChildIds: rootChildIds.value,
      selectedRootChildId: selectedRootChildId.value,
      selectedChildIdByParent: selectedChildIdByParent.value,
      fallbackMessages: WELCOME_MESSAGES,
    });
  });

  const currentLeafMessageId = computed(() => {
    return resolveCurrentLeafMessageId(
      rootChildIds.value,
      displayedMessages.value,
    );
  });

  const lastAssistantMessageId = computed(() => {
    return resolveLastRoleMessageId(displayedMessages.value, 'assistant');
  });

  const activeStreamingAssistantMessage = computed(() => {
    const activeAssistantId = activeGeneration.value?.assistant_id;
    if (!activeAssistantId) {
      return null;
    }
    return findMessageById(activeAssistantId);
  });

  const liveToolStatuses = computed<ChatToolStatus[]>(() => {
    return activeStreamingAssistantMessage.value?.tool_statuses ?? [];
  });

  const latestLiveToolStatus = computed<ChatToolStatus | null>(() => {
    if (!isLoading.value || liveToolStatuses.value.length === 0) {
      return null;
    }

    for (
      let index = liveToolStatuses.value.length - 1;
      index >= 0;
      index -= 1
    ) {
      const status = liveToolStatuses.value[index];
      if (status?.phase === 'start') {
        return status;
      }
    }
    return liveToolStatuses.value[liveToolStatuses.value.length - 1] ?? null;
  });

  const canConfirmEdit = computed(() => {
    return (
      !isLoading.value &&
      (editingDraftText.value.trim().length > 0 ||
        editingDraftFiles.value.length > 0)
    );
  });

  const isMessageThinking = (message: ChatMessageNode) => {
    return (
      isLoading.value &&
      message.role === 'assistant' &&
      message.id === activeGeneration.value?.assistant_id &&
      !message.content.trim()
    );
  };

  const isMessageStreaming = (message: ChatMessageNode) => {
    return (
      isLoading.value &&
      message.role === 'assistant' &&
      message.id === activeGeneration.value?.assistant_id
    );
  };

  const bumpSessionViewKey = () => {
    sessionViewKey.value += 1;
  };

  const resetEditingState = () => {
    editingMessageId.value = null;
    editingDraftText.value = '';
    editingDraftFiles.value = [];
    editingDraftSkillIds.value = [];
  };

  const resetConversationState = () => {
    activeSessionId.value = null;
    conversationId.value = createConversationId();
    bumpSessionViewKey();
  };

  const resetChatState = () => {
    messageNodes.value = {};
    rootChildIds.value = [];
    selectedRootChildId.value = null;
    selectedChildIdByParent.value = {};
    selectedFiles.value = [];
    selectedSkillIds.value = [];
    inputText.value = '';
    resetConversationState();
    resetEditingState();
  };

  const findMessageById = (messageId: string) => {
    return findNodeByIdInTree(messageNodes.value, messageId);
  };

  const createMessageNode = (
    node: Omit<ChatMessageNode, 'id' | 'child_ids'> & { id?: string },
  ) => {
    const messageId = node.id ?? createMessageId();
    const newNode: ChatMessageNode = {
      ...node,
      id: messageId,
      child_ids: [],
    };

    messageNodes.value[messageId] = newNode;

    if (node.parent_id) {
      const parentNode = findMessageById(node.parent_id);
      if (parentNode) {
        parentNode.child_ids.push(messageId);
        selectedChildIdByParent.value[node.parent_id] = messageId;
      }
    } else {
      rootChildIds.value.push(messageId);
      selectedRootChildId.value = messageId;
    }

    return newNode;
  };

  const updateMessageContent = (messageId: string, content: string) => {
    const targetMessage = findMessageById(messageId);
    if (targetMessage) {
      targetMessage.content = content;
    }
  };

  const appendMessageContent = (messageId: string, chunk: string) => {
    const targetMessage = findMessageById(messageId);
    if (targetMessage) {
      targetMessage.content += chunk;
    }
  };

  const appendMessageAttachment = (
    messageId: string,
    attachment: ChatAttachment,
  ) => {
    const targetMessage = findMessageById(messageId);
    if (!targetMessage) {
      return;
    }

    const nextFiles = [...(targetMessage.files ?? [])];
    const duplicateIndex = nextFiles.findIndex((file) => {
      if (file.attachment_id && attachment.attachment_id) {
        return file.attachment_id === attachment.attachment_id;
      }

      return (
        file.name === attachment.name &&
        file.size_label === attachment.size_label
      );
    });

    if (duplicateIndex >= 0) {
      nextFiles[duplicateIndex] = attachment;
    } else {
      nextFiles.push(attachment);
    }

    targetMessage.files = nextFiles;
  };

  const appendMessageToolStatus = (
    messageId: string,
    toolStatus: ChatToolStatus,
  ) => {
    const targetMessage = findMessageById(messageId);
    if (!targetMessage) {
      return;
    }

    targetMessage.tool_statuses = [
      ...(targetMessage.tool_statuses ?? []),
      toolStatus,
    ];
  };

  const updateMessageTraceId = (messageId: string, traceId: string) => {
    const targetMessage = findMessageById(messageId);
    if (!targetMessage || targetMessage.role !== 'assistant') {
      return;
    }
    targetMessage.trace_id = traceId;
  };

  const getMessageVersionIndex = (messageId: string) => {
    return getMessageVersionIndexInTree({
      messageNodes: messageNodes.value,
      rootChildIds: rootChildIds.value,
      messageId,
    });
  };

  const getMessageVersionCount = (messageId: string) => {
    return getMessageVersionCountInTree({
      messageNodes: messageNodes.value,
      rootChildIds: rootChildIds.value,
      messageId,
    });
  };

  const canSwitchMessageVersion = (messageId: string, direction: -1 | 1) => {
    return canSwitchMessageVersionInTree({
      messageNodes: messageNodes.value,
      rootChildIds: rootChildIds.value,
      messageId,
      direction,
    });
  };

  const switchMessageVersion = (messageId: string, direction: -1 | 1) => {
    if (isLoading.value) {
      return;
    }

    const messageNode = findMessageById(messageId);
    if (!messageNode) {
      return;
    }

    const targetMessageId = resolveTargetVersionMessageId({
      messageNodes: messageNodes.value,
      rootChildIds: rootChildIds.value,
      messageId,
      direction,
    });

    if (!targetMessageId) {
      return;
    }

    if (messageNode.parent_id) {
      selectedChildIdByParent.value[messageNode.parent_id] = targetMessageId;
    } else {
      selectedRootChildId.value = targetMessageId;
    }
  };

  const buildRequestSnapshotForUserMessage = (
    userMessageId: string,
    model: string,
    rerankerModel: string,
  ) => {
    const path = getMessagePathToNode(messageNodes.value, userMessageId);
    const currentUserMessage = findMessageById(userMessageId);
    const selectedSkillIdsFromMessage = Array.from(
      new Set(currentUserMessage?.request_skill_ids ?? []),
    );
    return {
      user_message_id: userMessageId,
      conversation_id: conversationId.value,
      model,
      reranker_model: rerankerModel,
      selected_skill_ids: selectedSkillIdsFromMessage,
      messages: path.map((message) => ({
        role: message.role,
        content: message.api_content ?? message.content,
      })),
      files: currentUserMessage?.request_files ?? [],
      attachment_ids: collectPersistedUploadedAttachmentIdsFromPath(path),
    };
  };

  const prewarmVisibleConversationCache = (cacheScopeId: string) => {
    prewarmRenderedContentCache(
      displayedMessages.value.map((message) => ({
        cacheScopeId,
        messageId: message.id,
        content: message.content,
        role: message.role,
      })),
    );

    const versionCandidates = findAdjacentVersionNodes({
      displayedMessages: displayedMessages.value,
      messageNodes: messageNodes.value,
      rootChildIds: rootChildIds.value,
    });

    prewarmRenderedContentCache(
      versionCandidates.map((message) => ({
        cacheScopeId,
        messageId: message.id,
        content: message.content,
        role: message.role,
      })),
    );
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

    messageNodes.value = nextMessageNodes;
    rootChildIds.value = [...snapshot.root_child_ids];
    selectedRootChildId.value = snapshot.selected_root_child_id;
    selectedChildIdByParent.value = {
      ...snapshot.selected_child_id_by_parent,
    };
    resetEditingState();
  };

  const buildSessionSnapshotPayload = (
    selectedModel: string,
    selectedRerankerModel: string,
  ): ChatSessionSnapshotPayload => {
    return {
      message_nodes: Object.values(messageNodes.value).map((message) => ({
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
      })),
      root_child_ids: [...rootChildIds.value],
      selected_root_child_id: selectedRootChildId.value,
      selected_child_id_by_parent: { ...selectedChildIdByParent.value },
      selected_model: selectedModel,
      selected_reranker_model: selectedRerankerModel,
    };
  };

  const buildTitleSourceMessages = () => {
    return displayedMessages.value
      .filter((message) => message.role !== 'system')
      .slice(0, 4)
      .map((message) => message.content.trim())
      .filter((content) => content.length > 0)
      .map((content) => content.slice(0, 180));
  };

  const mergeSessionSummary = (
    session:
      | ChatSessionSummary
      | {
          id: string;
          title: string;
          created_at: string;
          updated_at: string;
          selected_model?: string;
          selected_reranker_model?: string | null;
        },
  ) => {
    const mapped = {
      id: session.id,
      title: session.title,
      created_at: session.created_at,
      updated_at: session.updated_at,
      selected_model: session.selected_model ?? '',
      selected_reranker_model: session.selected_reranker_model ?? null,
    } satisfies ChatSessionSummary;

    const nextSessions = sessionSummaries.value.filter((item) => {
      return item.id !== session.id;
    });
    nextSessions.unshift(mapped);
    nextSessions.sort((left, right) => {
      return (
        new Date(right.updated_at).getTime() -
        new Date(left.updated_at).getTime()
      );
    });
    sessionSummaries.value = nextSessions;
  };

  return {
    activeGeneration,
    activeSessionId,
    activeStreamingAssistantMessage,
    appendMessageAttachment,
    appendMessageContent,
    appendMessageToolStatus,
    buildRequestSnapshotForUserMessage,
    buildSessionSnapshotPayload,
    buildTitleSourceMessages,
    bumpSessionViewKey,
    canConfirmEdit,
    canSwitchMessageVersion,
    conversationId,
    createMessageNode,
    currentLeafMessageId,
    displayedMessages,
    editingDraftFiles,
    editingDraftSkillIds,
    editingDraftText,
    editingMessageId,
    findMessageById,
    getMessageVersionCount,
    getMessageVersionIndex,
    hydrateSessionSnapshot,
    inputText,
    isMessageStreaming,
    isMessageThinking,
    isLoading,
    lastAssistantMessageId,
    latestLiveToolStatus,
    mergeSessionSummary,
    messageNodes,
    prewarmVisibleConversationCache,
    resetChatState,
    resetConversationState,
    resetEditingState,
    rootChildIds,
    selectedChildIdByParent,
    selectedFiles,
    selectedRootChildId,
    selectedSkillIds,
    sessionSummaries,
    sessionViewKey,
    switchMessageVersion,
    updateMessageContent,
    updateMessageTraceId,
  };
});
