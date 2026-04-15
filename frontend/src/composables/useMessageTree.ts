import { computed, type Ref } from 'vue';
import type {
  ChatAttachment,
  ChatMessageNode,
  ChatToolStatus,
} from '../types/chat';
import {
  buildDisplayedMessages,
  canSwitchMessageVersion as canSwitchMessageVersionInTree,
  collectPersistedUploadedAttachmentIdsFromPath,
  findAdjacentVersionNodes,
  getMessagePathToNode,
  getMessageVersionCount as getMessageVersionCountInTree,
  getMessageVersionIndex as getMessageVersionIndexInTree,
  findNodeById as findNodeByIdInTree,
  resolveCurrentLeafMessageId,
  resolveLastRoleMessageId,
  resolveTargetVersionMessageId,
} from '../utils/message-tree';
import { prewarmRenderedContentCache } from '../utils/render-markdown';
import { createMessageId } from '../utils/ids';

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

interface UseMessageTreeOptions {
  messageNodes: Ref<Record<string, ChatMessageNode>>;
  rootChildIds: Ref<string[]>;
  selectedRootChildId: Ref<string | null>;
  selectedChildIdByParent: Ref<Record<string, string>>;
  isLoading: () => boolean;
}

export const useMessageTree = (options: UseMessageTreeOptions) => {
  const findNodeById = (messageId: string) => {
    return findNodeByIdInTree(options.messageNodes.value, messageId);
  };

  const displayedMessages = computed(() => {
    return buildDisplayedMessages({
      messageNodes: options.messageNodes.value,
      rootChildIds: options.rootChildIds.value,
      selectedRootChildId: options.selectedRootChildId.value,
      selectedChildIdByParent: options.selectedChildIdByParent.value,
      fallbackMessages: WELCOME_MESSAGES,
    });
  });

  const currentLeafMessageId = computed(() => {
    return resolveCurrentLeafMessageId(
      options.rootChildIds.value,
      displayedMessages.value,
    );
  });

  const lastAssistantMessageId = computed(() => {
    return resolveLastRoleMessageId(displayedMessages.value, 'assistant');
  });

  const createMessageNode = (
    node: Omit<ChatMessageNode, 'id' | 'child_ids'> & { id?: string },
  ) => {
    const messageId = node.id ?? createMessageId();
    const newNode: ChatMessageNode = {
      ...node,
      id: messageId,
      child_ids: [],
    };

    options.messageNodes.value[messageId] = newNode;

    if (node.parent_id) {
      const parentNode = findNodeById(node.parent_id);
      if (parentNode) {
        parentNode.child_ids.push(messageId);
        options.selectedChildIdByParent.value[node.parent_id] = messageId;
      }
    } else {
      options.rootChildIds.value.push(messageId);
      options.selectedRootChildId.value = messageId;
    }

    return newNode;
  };

  const getMessageVersionIndex = (messageId: string) => {
    return getMessageVersionIndexInTree({
      messageNodes: options.messageNodes.value,
      rootChildIds: options.rootChildIds.value,
      messageId,
    });
  };

  const getMessageVersionCount = (messageId: string) => {
    return getMessageVersionCountInTree({
      messageNodes: options.messageNodes.value,
      rootChildIds: options.rootChildIds.value,
      messageId,
    });
  };

  const canSwitchMessageVersion = (messageId: string, direction: -1 | 1) => {
    return canSwitchMessageVersionInTree({
      messageNodes: options.messageNodes.value,
      rootChildIds: options.rootChildIds.value,
      messageId,
      direction,
    });
  };

  const switchMessageVersion = (messageId: string, direction: -1 | 1) => {
    if (options.isLoading()) {
      return;
    }

    const messageNode = findNodeById(messageId);
    if (!messageNode) {
      return;
    }

    const targetMessageId = resolveTargetVersionMessageId({
      messageNodes: options.messageNodes.value,
      rootChildIds: options.rootChildIds.value,
      messageId,
      direction,
    });

    if (!targetMessageId) {
      return;
    }

    if (messageNode.parent_id) {
      options.selectedChildIdByParent.value[messageNode.parent_id] =
        targetMessageId;
    } else {
      options.selectedRootChildId.value = targetMessageId;
    }
  };

  const findMessageById = (messageId: string) => {
    return findNodeById(messageId);
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

  const buildRequestSnapshotForUserMessage = (
    userMessageId: string,
    conversationId: string,
    model: string,
    rerankerModel: string,
  ) => {
    const path = getMessagePathToNode(
      options.messageNodes.value,
      userMessageId,
    );
    const currentUserMessage = findNodeById(userMessageId);
    const selectedSkillIdsFromMessage = Array.from(
      new Set(currentUserMessage?.request_skill_ids ?? []),
    );
    return {
      user_message_id: userMessageId,
      conversation_id: conversationId,
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

  const prewarmDisplayedMessagesCache = (cacheScopeId: string) => {
    prewarmRenderedContentCache(
      displayedMessages.value.map((message) => ({
        cacheScopeId,
        messageId: message.id,
        content: message.content,
        role: message.role,
      })),
    );
  };

  const prewarmAdjacentVersionsCache = (cacheScopeId: string) => {
    const versionCandidates = findAdjacentVersionNodes({
      displayedMessages: displayedMessages.value,
      messageNodes: options.messageNodes.value,
      rootChildIds: options.rootChildIds.value,
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

  const prewarmVisibleConversationCache = (cacheScopeId: string) => {
    prewarmDisplayedMessagesCache(cacheScopeId);
    prewarmAdjacentVersionsCache(cacheScopeId);
  };

  return {
    canSwitchMessageVersion,
    currentLeafMessageId,
    displayedMessages,
    findMessageById,
    appendMessageAttachment,
    appendMessageContent,
    appendMessageToolStatus,
    buildRequestSnapshotForUserMessage,
    createMessageNode,
    getMessageVersionCount,
    getMessageVersionIndex,
    prewarmVisibleConversationCache,
    switchMessageVersion,
    updateMessageContent,
    updateMessageTraceId,
    lastAssistantMessageId,
  };
};
