<template>
  <div class="chat-layout">
    <ChatSidebar
      :processing-modes="processingModes"
      :selected-processing-mode="selectedProcessingMode"
      :models="availableModels"
      :selected-model="selectedModel"
      :messages-count="messagesCount"
      :sessions="sessionSummaries"
      :active-session-id="activeSessionId"
      :is-locked="isLoading"
      @select-processing-mode="onSelectProcessingMode"
      @select-model="onSelectModel"
      @clear-chat="onClearChat"
      @load-session="onLoadSession"
      @rename-session="onRenameSession"
      @delete-session="onDeleteSession"
    />
    <div class="chat-main">
      <Transition name="session-switch" mode="out-in">
        <div
          :key="sessionViewKey"
          ref="messageContainerRef"
          class="chat-messages"
        >
          <ChatMessage
            v-for="message in displayedMessages"
            :key="message.id"
            :message="message"
            :is-thinking="isMessageThinking(message)"
            :is-streaming="isMessageStreaming(message)"
            :version-index="getMessageVersionIndex(message.id)"
            :version-count="getMessageVersionCount(message.id)"
            :show-version-switcher="getMessageVersionCount(message.id) > 1"
            :can-go-prev="canSwitchMessageVersion(message.id, -1)"
            :can-go-next="canSwitchMessageVersion(message.id, 1)"
            :can-edit="message.role === 'user' && !isLoading"
            :can-regenerate="message.role === 'assistant' && !isLoading"
            :can-copy="message.content.trim().length > 0"
            :can-download="
              message.role === 'assistant' && message.content.trim().length > 0
            "
            :is-version-locked="message.role !== 'system' && isLoading"
            :is-editing="editingMessageId === message.id"
            :editing-text="editingDraftText"
            :editing-files="
              editingMessageId === message.id ? editingDraftFiles : []
            "
            :can-confirm-edit="canConfirmEdit"
            :show-toolbar-by-default="message.id === lastAssistantMessageId"
            :cache-scope-id="activeSessionId ?? conversationId"
            :can-submit-interaction="!isLoading"
            :live-tool-status="
              message.id === activeGeneration?.assistantId
                ? latestLiveToolStatus
                : null
            "
            @prev-version="switchMessageVersion(message.id, -1)"
            @next-version="switchMessageVersion(message.id, 1)"
            @start-edit="startEditingMessage(message.id)"
            @update-edit-text="updateEditingText"
            @upload-edit-files="appendEditingFiles"
            @remove-edit-file="removeEditingFile"
            @cancel-edit="cancelEditingMessage"
            @confirm-edit="confirmEditingMessage"
            @regenerate="onRegenerate(message.id)"
            @copy="copyMessage(message.id)"
            @download="downloadAssistantMessage(message.id)"
            @download-file="downloadMessageFile"
            @submit-interaction="submitMessageInteraction(message.id, $event)"
          />
        </div>
      </Transition>
      <Transition name="copy-toast">
        <div v-if="isCopyToastVisible" class="copy-toast">
          <div class="copy-toast-icon" aria-hidden="true">
            <svg viewBox="0 0 20 20" class="copy-toast-icon-svg">
              <path
                d="M5 10.5L8.25 13.75L15 7"
                fill="none"
                stroke="currentColor"
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
              />
            </svg>
          </div>
          <div class="copy-toast-content">
            <span class="copy-toast-title">{{ copyToastTitle }}</span>
            <span class="copy-toast-description">{{ copyToastMessage }}</span>
          </div>
        </div>
      </Transition>
      <ChatInput
        v-model:text="inputText"
        :files="selectedFiles"
        :is-loading="isLoading"
        @upload-files="onFilesSelect"
        @send="onSendMessage"
        @stop="onStopGeneration"
        @clear-all-files="onClearAllFiles"
        @remove-file="onRemoveFile"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue';
import { downloadAttachment } from '../api/attachments';
import { fallbackModels } from '../api/catalog';
import { useCatalogLoader } from '../composables/useCatalogLoader';
import { useChatSessions } from '../composables/useChatSessions';
import { useChatStreaming } from '../composables/useChatStreaming';
import { useCopyToast } from '../composables/useCopyToast';
import { useMessageActions } from '../composables/useMessageActions';
import type {
  ChatAttachment,
  ChatEditAttachment,
  ChatMessageNode,
  ChatRequestSnapshot,
  ChatToolStatus,
} from '../types/chat';
import type { SkillOption } from '../types/skill';
import { createMessageId } from '../utils/ids';
import {
  buildDisplayedMessages,
  canSwitchMessageVersion as canSwitchMessageVersionInTree,
  collectPersistedUploadedAttachmentIdsFromPath,
  findAdjacentVersionNodes,
  getMessagePathToNode,
  getMessageVersionCount as getMessageVersionCountInTree,
  getMessageVersionIndex as getMessageVersionIndexInTree,
  getNodeById as getNodeByIdInTree,
  resolveCurrentLeafMessageId,
  resolveLastRoleMessageId,
  resolveTargetVersionMessageId,
} from '../utils/message-tree';
import { prewarmRenderedContentCache } from '../utils/render-markdown';
import ChatInput from './ChatInput.vue';
import ChatMessage from './ChatMessage.vue';
import ChatSidebar from './ChatSidebar.vue';

const welcomeMessages: ChatMessageNode[] = [
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

const inputText = ref('');
const selectedFiles = ref<File[]>([]);
const processingModes = ref<SkillOption[]>([
  {
    id: 'document-assistant',
    displayName: '文档助手',
  },
]);
const selectedProcessingMode = ref('document-assistant');
const selectedModel = ref(fallbackModels[0]);
const availableModels = ref(fallbackModels);
const messageNodes = ref<Record<string, ChatMessageNode>>({});
const rootChildIds = ref<string[]>([]);
const selectedRootChildId = ref<string | null>(null);
const selectedChildIdByParent = ref<Record<string, string>>({});
const editingMessageId = ref<string | null>(null);
const editingDraftText = ref('');
const editingDraftFiles = ref<ChatEditAttachment[]>([]);
const { copyToastMessage, copyToastTitle, isCopyToastVisible, showCopyToast } =
  useCopyToast();

const messageContainerRef = ref<HTMLElement | null>(null);

const resetEditingState = () => {
  editingMessageId.value = null;
  editingDraftText.value = '';
  editingDraftFiles.value = [];
};

const getNodeById = (messageId: string) => {
  return getNodeByIdInTree(messageNodes.value, messageId);
};

const displayedMessages = computed(() => {
  return buildDisplayedMessages({
    messageNodes: messageNodes.value,
    rootChildIds: rootChildIds.value,
    selectedRootChildId: selectedRootChildId.value,
    selectedChildIdByParent: selectedChildIdByParent.value,
    fallbackMessages: welcomeMessages,
  });
});

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

const prewarmVisibleConversationCache = (cacheScopeId: string) => {
  prewarmDisplayedMessagesCache(cacheScopeId);
  prewarmAdjacentVersionsCache(cacheScopeId);
};

const messagesCount = computed(() => {
  return rootChildIds.value.length > 0 ? displayedMessages.value.length : 0;
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

const scrollToBottom = () => {
  nextTick(() => {
    if (messageContainerRef.value) {
      messageContainerRef.value.scrollTop =
        messageContainerRef.value.scrollHeight;
    }
  });
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
    const parentNode = getNodeById(node.parentId);
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

const buildRequestSnapshotForUserMessage = (userMessageId: string) => {
  const path = getMessagePathToNode(messageNodes.value, userMessageId);
  const currentUserMessage = getNodeById(userMessageId);
  return {
    userMessageId,
    conversationId: conversationId.value,
    model: selectedModel.value,
    skillId: selectedProcessingMode.value,
    messages: path.map((message) => ({
      role: message.role,
      content: message.apiContent ?? message.content,
    })),
    files: currentUserMessage?.requestFiles ?? [],
    attachmentIds: collectPersistedUploadedAttachmentIdsFromPath(path),
  } satisfies ChatRequestSnapshot;
};

const findMessageById = (messageId: string) => {
  return getNodeById(messageId);
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

const updateMessageInteraction = (
  messageId: string,
  interaction: ChatMessageNode['interaction'],
) => {
  const targetMessage = findMessageById(messageId);
  if (!targetMessage) {
    return;
  }
  targetMessage.interaction = interaction ?? null;
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

  const messageNode = getNodeById(messageId);
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

  prewarmVisibleConversationCache(
    activeSessionId.value ?? conversationId.value,
  );
};

const createAssistantVariant = (userMessageId: string) => {
  return createMessageNode({
    role: 'assistant',
    content: '',
    timestamp: new Date(),
    parentId: userMessageId,
  });
};

const {
  activeGeneration,
  executeAssistantGeneration,
  executeAssistantInteraction,
  isLoading,
  isMessageThinking,
  onStopGeneration,
} = useChatStreaming({
  createAssistantVariant,
  appendMessageContent,
  appendMessageAttachment,
  appendMessageToolStatus,
  updateMessageInteraction,
  updateMessageContent,
  findMessageById,
  scrollToBottom,
  persistCurrentSession: async () => {
    await persistCurrentSession();
  },
});

const {
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
} = useChatSessions({
  messageNodes,
  rootChildIds,
  selectedRootChildId,
  selectedChildIdByParent,
  selectedProcessingMode,
  selectedModel,
  isChatLocked: () => isLoading.value,
  getDisplayedMessages: () => displayedMessages.value,
  resetEditingState: () => {
    inputText.value = '';
    selectedFiles.value = [];
    resetEditingState();
  },
  afterSessionLoaded: async () => {
    inputText.value = '';
    selectedFiles.value = [];
    await nextTick();
    prewarmVisibleConversationCache(
      activeSessionId.value ?? conversationId.value,
    );
    scrollToBottom();
  },
  onDeleteActiveSession: () => {
    onClearChat();
  },
});

const isMessageStreaming = (message: ChatMessageNode) => {
  return (
    isLoading.value &&
    message.role === 'assistant' &&
    message.id === activeGeneration.value?.assistantId
  );
};

const activeStreamingAssistantMessage = computed(() => {
  const activeAssistantId = activeGeneration.value?.assistantId;
  if (!activeAssistantId) {
    return null;
  }
  return getNodeById(activeAssistantId);
});

const liveToolStatuses = computed<ChatToolStatus[]>(() => {
  return activeStreamingAssistantMessage.value?.toolStatuses ?? [];
});

const latestLiveToolStatus = computed<ChatToolStatus | null>(() => {
  if (!isLoading.value || liveToolStatuses.value.length === 0) {
    return null;
  }

  for (let index = liveToolStatuses.value.length - 1; index >= 0; index -= 1) {
    const status = liveToolStatuses.value[index];
    if (status?.phase === 'start') {
      return status;
    }
  }
  return liveToolStatuses.value[liveToolStatuses.value.length - 1] ?? null;
});

const {
  canConfirmEdit,
  onFilesSelect,
  onRemoveFile,
  onClearAllFiles,
  onClearChat,
  startEditingMessage,
  updateEditingText,
  appendEditingFiles,
  removeEditingFile,
  cancelEditingMessage,
  confirmEditingMessage,
  onSendMessage,
  onRegenerate,
  submitMessageInteraction,
  copyMessage,
  downloadAssistantMessage,
  downloadMessageFile,
} = useMessageActions({
  inputText,
  selectedFiles,
  editingMessageId,
  editingDraftText,
  editingDraftFiles,
  isLoading,
  activeSessionId,
  conversationId,
  rootChildIds,
  messageNodes,
  selectedRootChildId,
  selectedChildIdByParent,
  currentLeafMessageId,
  getNodeById,
  createMessageNode,
  buildRequestSnapshotForUserMessage,
  executeAssistantGeneration,
  executeAssistantInteraction,
  persistCurrentSession: async () => {
    await persistCurrentSession();
  },
  resetEditingState,
  scrollToBottom,
  onStopGeneration,
  resetConversationState,
  showCopyToast,
  downloadAttachment,
});

const onSelectModel = (model: string) => {
  selectedModel.value = model;
  if (activeSessionId.value && rootChildIds.value.length > 0) {
    void persistCurrentSession();
  }
};

const onSelectProcessingMode = (mode: string) => {
  selectedProcessingMode.value = mode;
  if (activeSessionId.value && rootChildIds.value.length > 0) {
    void persistCurrentSession();
  }
};

const onLoadSession = async (sessionId: string) => {
  await loadChatSession(sessionId);
};

const onRenameSession = async (payload: {
  sessionId: string;
  title: string;
}) => {
  await renameChatSession(payload.sessionId, payload.title);
};

const onDeleteSession = async (sessionId: string) => {
  await deleteChatSession(sessionId);
};

const { loadAvailableModels, loadAvailableSkills } = useCatalogLoader({
  availableModels,
  selectedModel,
  processingModes,
  selectedProcessingMode,
});

onMounted(() => {
  scrollToBottom();
  void loadSessionSummaries();
  void loadAvailableSkills();
  void loadAvailableModels();
  prewarmVisibleConversationCache(
    activeSessionId.value ?? conversationId.value,
  );
});
</script>

<style scoped src="../styles/components/chat-layout.css"></style>
