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
import { prewarmRenderedContentCache } from '@shared/utils/render-markdown';
import { createConversationId, createMessageId } from '@shared/utils/ids';

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
    parentId: null,
    childIds: [],
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
    const activeAssistantId = activeGeneration.value?.assistantId;
    if (!activeAssistantId) {
      return null;
    }
    return findMessageById(activeAssistantId);
  });

  const liveToolStatuses = computed<ChatToolStatus[]>(() => {
    return activeStreamingAssistantMessage.value?.toolStatuses ?? [];
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
      message.id === activeGeneration.value?.assistantId &&
      !message.content.trim()
    );
  };

  const isMessageStreaming = (message: ChatMessageNode) => {
    return (
      isLoading.value &&
      message.role === 'assistant' &&
      message.id === activeGeneration.value?.assistantId
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
    node: Omit<ChatMessageNode, 'id' | 'childIds'> & { id?: string },
  ) => {
    const messageId = node.id ?? createMessageId();
    const newNode: ChatMessageNode = {
      ...node,
      id: messageId,
      childIds: [],
    };

    messageNodes.value[messageId] = newNode;

    if (node.parentId) {
      const parentNode = findMessageById(node.parentId);
      if (parentNode) {
        parentNode.childIds.push(messageId);
        selectedChildIdByParent.value[node.parentId] = messageId;
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
      if (file.attachmentId && attachment.attachmentId) {
        return file.attachmentId === attachment.attachmentId;
      }

      return (
        file.name === attachment.name && file.sizeLabel === attachment.sizeLabel
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

    targetMessage.toolStatuses = [
      ...(targetMessage.toolStatuses ?? []),
      toolStatus,
    ];
  };

  const updateMessageTraceId = (messageId: string, traceId: string) => {
    const targetMessage = findMessageById(messageId);
    if (!targetMessage || targetMessage.role !== 'assistant') {
      return;
    }
    targetMessage.traceId = traceId;
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

    if (messageNode.parentId) {
      selectedChildIdByParent.value[messageNode.parentId] = targetMessageId;
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
      new Set(currentUserMessage?.requestSkillIds ?? []),
    );
    return {
      userMessageId,
      conversationId: conversationId.value,
      model,
      rerankerModel,
      selectedSkillIds: selectedSkillIdsFromMessage,
      messages: path.map((message) => ({
        role: message.role,
        content: message.apiContent ?? message.content,
      })),
      files: currentUserMessage?.requestFiles ?? [],
      attachmentIds: collectPersistedUploadedAttachmentIdsFromPath(path),
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
    for (const message of snapshot.messageNodes) {
      nextMessageNodes[message.id] = {
        id: message.id,
        role: message.role,
        content: message.content,
        traceId: message.traceId ?? undefined,
        apiContent: message.apiContent ?? undefined,
        requestSkillIds: message.requestSkillIds ?? [],
        files: message.files ?? [],
        toolStatuses: message.toolStatuses ?? [],
        timestamp: new Date(message.timestamp),
        parentId: message.parentId,
        childIds: [...message.childIds],
        requestFiles: [],
      };
    }

    messageNodes.value = nextMessageNodes;
    rootChildIds.value = [...snapshot.rootChildIds];
    selectedRootChildId.value = snapshot.selectedRootChildId;
    selectedChildIdByParent.value = {
      ...snapshot.selectedChildIdByParent,
    };
    resetEditingState();
  };

  const buildSessionSnapshotPayload = (
    selectedModel: string,
    selectedRerankerModel: string,
  ): ChatSessionSnapshotPayload => {
    return {
      messageNodes: Object.values(messageNodes.value).map((message) => ({
        id: message.id,
        role: message.role,
        content: message.content,
        traceId: message.traceId ?? null,
        apiContent: message.apiContent ?? null,
        requestSkillIds: message.requestSkillIds ?? [],
        files: message.files ?? [],
        toolStatuses: message.toolStatuses ?? [],
        timestamp: message.timestamp.toISOString(),
        parentId: message.parentId,
        childIds: [...message.childIds],
      })),
      rootChildIds: [...rootChildIds.value],
      selectedRootChildId: selectedRootChildId.value,
      selectedChildIdByParent: { ...selectedChildIdByParent.value },
      selectedModel,
      selectedRerankerModel,
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
          createdAt: string;
          updatedAt: string;
          selectedModel?: string;
          selectedRerankerModel?: string | null;
        },
  ) => {
    const mapped = {
      id: session.id,
      title: session.title,
      createdAt: session.createdAt,
      updatedAt: session.updatedAt,
      selectedModel: session.selectedModel ?? '',
      selectedRerankerModel: session.selectedRerankerModel ?? null,
    } satisfies ChatSessionSummary;

    const nextSessions = sessionSummaries.value.filter((item) => {
      return item.id !== session.id;
    });
    nextSessions.unshift(mapped);
    nextSessions.sort((left, right) => {
      return (
        new Date(right.updatedAt).getTime() - new Date(left.updatedAt).getTime()
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
