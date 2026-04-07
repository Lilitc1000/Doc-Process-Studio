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
import { downloadGeneratedArtifact } from '../api/artifacts';
import {
  fetchAvailableModels,
  fetchAvailableSkills,
  fallbackModels,
} from '../api/catalog';
import { useChatSessions } from '../composables/useChatSessions';
import { useChatStreaming } from '../composables/useChatStreaming';
import { useCopyToast } from '../composables/useCopyToast';
import type {
  ChatAttachment,
  ChatMessageNode,
  ChatRequestSnapshot,
  ChatToolStatus,
} from '../types/chat';
import type { SkillOption } from '../types/skill';
import { formatFileSize } from '../utils/file';
import { createMessageId } from '../utils/ids';
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
const editingDraftFiles = ref<File[]>([]);
const { copyToastMessage, copyToastTitle, isCopyToastVisible, showCopyToast } =
  useCopyToast();

const messageContainerRef = ref<HTMLElement | null>(null);

const resetEditingState = () => {
  editingMessageId.value = null;
  editingDraftText.value = '';
  editingDraftFiles.value = [];
};

const getNodeById = (messageId: string) => {
  return messageNodes.value[messageId] ?? null;
};

const getSelectedChildId = (messageId: string) => {
  const currentNode = getNodeById(messageId);
  if (!currentNode || currentNode.childIds.length === 0) {
    return null;
  }

  return (
    selectedChildIdByParent.value[messageId] ?? currentNode.childIds[0] ?? null
  );
};

const displayedMessages = computed(() => {
  const rootMessageId =
    selectedRootChildId.value ?? rootChildIds.value[0] ?? null;
  if (!rootMessageId) {
    return welcomeMessages;
  }

  const visibleMessages: ChatMessageNode[] = [];
  let currentMessageId: string | null = rootMessageId;

  while (currentMessageId) {
    const currentNode = getNodeById(currentMessageId);
    if (!currentNode) {
      break;
    }

    visibleMessages.push(currentNode);
    currentMessageId = getSelectedChildId(currentNode.id);
  }

  return visibleMessages;
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
  const versionCandidates: ChatMessageNode[] = [];

  for (const message of displayedMessages.value) {
    const siblingIds = getMessageSiblingIds(message.id);
    const currentIndex = siblingIds.indexOf(message.id);

    if (currentIndex < 0) {
      continue;
    }

    const adjacentSiblingIds = [
      siblingIds[currentIndex - 1] ?? null,
      siblingIds[currentIndex + 1] ?? null,
    ];

    for (const siblingId of adjacentSiblingIds) {
      if (!siblingId) {
        continue;
      }

      const siblingNode = getNodeById(siblingId);
      if (siblingNode) {
        versionCandidates.push(siblingNode);
      }
    }
  }

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

const messagesCount = computed(() => {
  return rootChildIds.value.length > 0 ? displayedMessages.value.length : 0;
});

const currentLeafMessageId = computed(() => {
  if (rootChildIds.value.length === 0) {
    return null;
  }

  const lastMessage =
    displayedMessages.value[displayedMessages.value.length - 1] ?? null;
  return lastMessage?.id ?? null;
});

const lastAssistantMessageId = computed(() => {
  for (let index = displayedMessages.value.length - 1; index >= 0; index -= 1) {
    const message = displayedMessages.value[index];
    if (message?.role === 'assistant') {
      return message.id;
    }
  }

  return null;
});

const scrollToBottom = () => {
  nextTick(() => {
    if (messageContainerRef.value) {
      messageContainerRef.value.scrollTop =
        messageContainerRef.value.scrollHeight;
    }
  });
};

const createAttachmentPreview = (files: File[]): ChatAttachment[] => {
  return files.map((file) => ({
    name: file.name,
    sizeLabel: formatFileSize(file),
  }));
};

const createUserApiContent = (text: string, files: File[]) => {
  const trimmedText = text.trim();
  if (files.length === 0) {
    return trimmedText;
  }

  const fileNames = files.map((file) => file.name).join('、');
  const fileSummary = `[用户上传了 ${files.length} 个文件：${fileNames}]`;

  if (!trimmedText) {
    return `请结合我上传的文件进行处理。\n${fileSummary}`;
  }

  return `${trimmedText}\n${fileSummary}`;
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

const getMessagePathToNode = (messageId: string) => {
  const path: ChatMessageNode[] = [];
  let currentMessageId: string | null = messageId;

  while (currentMessageId !== null) {
    const currentNode = getNodeById(currentMessageId);
    if (!currentNode) {
      break;
    }

    path.push(currentNode);
    currentMessageId = currentNode.parentId;
  }

  return path.reverse();
};

const collectRequestFilesFromPath = (path: ChatMessageNode[]) => {
  return path.flatMap((message) => message.requestFiles ?? []);
};

const buildRequestSnapshotForUserMessage = (userMessageId: string) => {
  const path = getMessagePathToNode(userMessageId);
  return {
    userMessageId,
    conversationId: conversationId.value,
    model: selectedModel.value,
    skillId: selectedProcessingMode.value,
    messages: path.map((message) => ({
      role: message.role,
      content: message.apiContent ?? message.content,
    })),
    files: collectRequestFilesFromPath(path),
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
    if (file.artifactId && attachment.artifactId) {
      return file.artifactId === attachment.artifactId;
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

const getMessageSiblingIds = (messageId: string) => {
  const messageNode = getNodeById(messageId);
  if (!messageNode) {
    return [];
  }

  const siblingSourceIds = messageNode.parentId
    ? (getNodeById(messageNode.parentId)?.childIds ?? [])
    : rootChildIds.value;

  return siblingSourceIds.filter((childId) => {
    return getNodeById(childId)?.role === messageNode.role;
  });
};

const getMessageVersionIndex = (messageId: string) => {
  const siblingIds = getMessageSiblingIds(messageId);
  const currentIndex = siblingIds.indexOf(messageId);
  return currentIndex >= 0 ? currentIndex + 1 : 1;
};

const getMessageVersionCount = (messageId: string) => {
  return getMessageSiblingIds(messageId).length;
};

const canSwitchMessageVersion = (messageId: string, direction: -1 | 1) => {
  const messageNode = getNodeById(messageId);
  if (!messageNode) {
    return false;
  }

  const siblingIds = getMessageSiblingIds(messageId);
  const currentIndex = siblingIds.indexOf(messageId);
  const targetIndex = currentIndex + direction;

  return targetIndex >= 0 && targetIndex < siblingIds.length;
};

const switchMessageVersion = (messageId: string, direction: -1 | 1) => {
  const messageNode = getNodeById(messageId);
  if (!messageNode || isLoading.value) {
    return;
  }

  const siblingIds = getMessageSiblingIds(messageId);
  const currentIndex = siblingIds.indexOf(messageId);
  const targetMessageId = siblingIds[currentIndex + direction];

  if (targetMessageId) {
    if (messageNode.parentId) {
      selectedChildIdByParent.value[messageNode.parentId] = targetMessageId;
      prewarmVisibleConversationCache(
        activeSessionId.value ?? conversationId.value,
      );
      return;
    }

    selectedRootChildId.value = targetMessageId;
    prewarmVisibleConversationCache(
      activeSessionId.value ?? conversationId.value,
    );
  }
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
  executeAssistantGeneration,
  isLoading,
  isMessageThinking,
  onStopGeneration,
} = useChatStreaming({
  createAssistantVariant,
  appendMessageContent,
  appendMessageAttachment,
  appendMessageToolStatus,
  updateMessageContent,
  findMessageById,
  scrollToBottom,
  persistCurrentSession: async () => {
    await persistCurrentSession();
  },
});

const canConfirmEdit = computed(() => {
  return (
    !isLoading.value &&
    (editingDraftText.value.trim().length > 0 ||
      editingDraftFiles.value.length > 0)
  );
});

const copyMessage = async (messageId: string) => {
  const messageNode = getNodeById(messageId);
  if (!messageNode?.content.trim() || !navigator.clipboard) {
    return;
  }

  try {
    await navigator.clipboard.writeText(messageNode.content);
    showCopyToast('内容已复制到剪贴板');
  } catch (error) {
    console.error('复制消息失败。', error);
  }
};

const downloadAssistantMessage = (assistantMessageId: string) => {
  const assistantNode = getNodeById(assistantMessageId);
  if (!assistantNode?.content.trim()) {
    return;
  }

  const blob = new Blob([assistantNode.content], {
    type: 'text/markdown;charset=utf-8',
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  const safeTimestamp = assistantNode.timestamp
    .toISOString()
    .replace(/[:.]/g, '-');

  link.href = url;
  link.download = `assistant-reply-${safeTimestamp}.md`;
  link.click();
  URL.revokeObjectURL(url);
};

const downloadMessageFile = async (file: ChatAttachment) => {
  if (!file.artifactId) {
    return;
  }

  try {
    await downloadGeneratedArtifact(file.artifactId);
  } catch (error) {
    const errorMessage =
      error instanceof Error ? error.message : '下载文件失败，请稍后重试。';
    showCopyToast(errorMessage, { title: '下载失败' });
  }
};

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

const onFilesSelect = (files: File[]) => {
  selectedFiles.value = [...selectedFiles.value, ...files];
};

const onRemoveFile = (index: number) => {
  selectedFiles.value.splice(index, 1);
};

const onClearAllFiles = () => {
  selectedFiles.value = [];
};

const onClearChat = () => {
  onStopGeneration();
  messageNodes.value = {};
  rootChildIds.value = [];
  selectedRootChildId.value = null;
  selectedChildIdByParent.value = {};
  selectedFiles.value = [];
  resetConversationState();
  resetEditingState();
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

const startEditingMessage = (messageId: string) => {
  if (isLoading.value) {
    return;
  }

  const messageNode = getNodeById(messageId);
  if (!messageNode || messageNode.role !== 'user') {
    return;
  }

  editingMessageId.value = messageId;
  editingDraftText.value = messageNode.content;
  editingDraftFiles.value = [...(messageNode.requestFiles ?? [])];
};

const updateEditingText = (value: string) => {
  editingDraftText.value = value;
};

const appendEditingFiles = (files: File[]) => {
  editingDraftFiles.value = [...editingDraftFiles.value, ...files];
};

const removeEditingFile = (index: number) => {
  editingDraftFiles.value.splice(index, 1);
};

const cancelEditingMessage = () => {
  resetEditingState();
};

const confirmEditingMessage = async () => {
  if (!editingMessageId.value || !canConfirmEdit.value) {
    return;
  }

  const sourceMessage = getNodeById(editingMessageId.value);
  if (!sourceMessage || sourceMessage.role !== 'user') {
    resetEditingState();
    return;
  }

  const nextText = editingDraftText.value.trim();
  const nextFiles = [...editingDraftFiles.value];

  const editedUserMessage = createMessageNode({
    role: 'user',
    content: nextText,
    apiContent: createUserApiContent(nextText, nextFiles),
    files: createAttachmentPreview(nextFiles),
    requestFiles: nextFiles,
    timestamp: new Date(),
    parentId: sourceMessage.parentId,
  });

  resetEditingState();
  scrollToBottom();
  await persistCurrentSession();

  await executeAssistantGeneration(
    buildRequestSnapshotForUserMessage(editedUserMessage.id),
  );
};

const onSendMessage = async () => {
  const text = inputText.value.trim();
  if ((!text && selectedFiles.value.length === 0) || isLoading.value) {
    return;
  }

  const currentRequestFiles = [...selectedFiles.value];
  const userMessage = createMessageNode({
    role: 'user',
    content: text,
    apiContent: createUserApiContent(text, currentRequestFiles),
    files: createAttachmentPreview(currentRequestFiles),
    requestFiles: currentRequestFiles,
    timestamp: new Date(),
    parentId: currentLeafMessageId.value,
  });
  scrollToBottom();

  inputText.value = '';
  selectedFiles.value = [];
  activeSessionId.value = conversationId.value;
  await persistCurrentSession();

  await executeAssistantGeneration(
    buildRequestSnapshotForUserMessage(userMessage.id),
  );
};

const onRegenerate = async (assistantMessageId: string) => {
  if (isLoading.value) {
    return;
  }

  const assistantNode = getNodeById(assistantMessageId);
  if (!assistantNode?.parentId || assistantNode.role !== 'assistant') {
    return;
  }

  await persistCurrentSession();
  await executeAssistantGeneration(
    buildRequestSnapshotForUserMessage(assistantNode.parentId),
  );
};

const loadAvailableModels = async () => {
  try {
    const modelNames = await fetchAvailableModels();
    if (modelNames.length === 0) {
      return;
    }

    availableModels.value = modelNames;
    if (!modelNames.includes(selectedModel.value)) {
      selectedModel.value = modelNames[0];
    }
  } catch (error) {
    console.error('加载远程模型列表失败，继续使用前端兜底模型列表。', error);
  }
};

const loadAvailableSkills = async () => {
  try {
    const { skills: nextSkills, defaultSkillId } = await fetchAvailableSkills();
    if (nextSkills.length === 0) {
      return;
    }

    processingModes.value = nextSkills;
    const resolvedSkillId = nextSkills.some((skill) => {
      return skill.id === selectedProcessingMode.value;
    })
      ? selectedProcessingMode.value
      : nextSkills.some((skill) => skill.id === defaultSkillId)
        ? defaultSkillId
        : nextSkills[0].id;

    selectedProcessingMode.value = resolvedSkillId;
  } catch (error) {
    console.error('加载 skill 列表失败，继续使用前端兜底选项。', error);
  }
};

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
