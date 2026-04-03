<template>
  <div class="chat-layout">
    <ChatSidebar
      :processing-modes="processingModes"
      :selected-processing-mode="selectedProcessingMode"
      :models="availableModels"
      :selected-model="selectedModel"
      :messages-count="messagesCount"
      :is-locked="isLoading"
      @select-processing-mode="onSelectProcessingMode"
      @select-model="onSelectModel"
      @clear-chat="onClearChat"
    />
    <div class="chat-main">
      <div ref="messageContainerRef" class="chat-messages">
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
        />
      </div>
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
            <span class="copy-toast-title">复制成功</span>
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
import axios from 'axios';
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue';
import ChatInput from './ChatInput.vue';
import ChatMessage from './ChatMessage.vue';
import ChatSidebar from './ChatSidebar.vue';

const fallbackModels = [
  'gpt-4o-mini',
  'gpt-4o',
  'claude-3.5-sonnet',
  'deepseek-v3',
];
type ChatMessageRole = 'user' | 'assistant' | 'system';
type SkillOption = {
  id: string;
  displayName: string;
  shortDescription?: string;
};

interface ChatAttachment {
  name: string;
  sizeLabel: string;
}

interface ChatMessageNode {
  id: string;
  role: ChatMessageRole;
  content: string;
  apiContent?: string;
  files?: ChatAttachment[];
  requestFiles?: File[];
  timestamp: Date;
  parentId: string | null;
  childIds: string[];
}

interface ApiChatMessage {
  role: ChatMessageRole;
  content: string;
}

interface ChatRequestSnapshot {
  userMessageId: string;
  model: string;
  skillId: string;
  messages: ApiChatMessage[];
  files: File[];
}

interface ActiveGenerationState {
  assistantId: string;
  userMessageId: string;
  controller: AbortController;
}

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
const isLoading = ref(false);
const messageNodes = ref<Record<string, ChatMessageNode>>({});
const rootChildIds = ref<string[]>([]);
const selectedRootChildId = ref<string | null>(null);
const selectedChildIdByParent = ref<Record<string, string>>({});
const activeGeneration = ref<ActiveGenerationState | null>(null);
const editingMessageId = ref<string | null>(null);
const editingDraftText = ref('');
const editingDraftFiles = ref<File[]>([]);
const copyToastMessage = ref('复制成功');
const isCopyToastVisible = ref(false);
let copyToastTimer: ReturnType<typeof setTimeout> | null = null;

const messageContainerRef = ref<HTMLElement | null>(null);

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

const canConfirmEdit = computed(() => {
  return (
    !isLoading.value &&
    (editingDraftText.value.trim().length > 0 ||
      editingDraftFiles.value.length > 0)
  );
});

const scrollToBottom = () => {
  nextTick(() => {
    if (messageContainerRef.value) {
      messageContainerRef.value.scrollTop =
        messageContainerRef.value.scrollHeight;
    }
  });
};

const createMessageId = () => {
  return crypto.randomUUID();
};

const formatAttachmentSize = (file: File) => {
  if (file.size < 1024) return `${file.size} B`;
  if (file.size < 1024 * 1024) return `${(file.size / 1024).toFixed(1)} KB`;
  return `${(file.size / (1024 * 1024)).toFixed(1)} MB`;
};

const createAttachmentPreview = (files: File[]): ChatAttachment[] => {
  return files.map((file) => ({
    name: file.name,
    sizeLabel: formatAttachmentSize(file),
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
      return;
    }

    selectedRootChildId.value = targetMessageId;
  }
};

const isMessageThinking = (message: ChatMessageNode) => {
  return (
    isLoading.value &&
    message.role === 'assistant' &&
    message.id === activeGeneration.value?.assistantId &&
    !message.content.trim()
  );
};

const markGenerationStopped = () => {
  if (!activeGeneration.value?.assistantId) {
    return;
  }

  const activeMessage = findMessageById(activeGeneration.value.assistantId);
  if (!activeMessage) {
    return;
  }

  if (activeMessage.content.trim()) {
    if (!activeMessage.content.endsWith('已停止输出')) {
      activeMessage.content += '\n\n已停止输出';
    }
    return;
  }

  activeMessage.content = '已停止输出';
};

const onStopGeneration = () => {
  if (activeGeneration.value?.controller) {
    activeGeneration.value.controller.abort();
    markGenerationStopped();
    activeGeneration.value = null;
    isLoading.value = false;
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

const streamAssistantReply = async (
  requestSnapshot: ChatRequestSnapshot,
  assistantMessageId: string,
  abortController: AbortController,
) => {
  const response = await fetch('/api/chat/stream', {
    method: 'POST',
    signal: abortController.signal,
    body: (() => {
      const formData = new FormData();
      formData.append(
        'payload',
        JSON.stringify({
          model: requestSnapshot.model,
          skill_id: requestSnapshot.skillId,
          messages: requestSnapshot.messages,
        }),
      );

      for (const file of requestSnapshot.files) {
        formData.append('files', file);
      }

      return formData;
    })(),
  });

  if (!response.ok || !response.body) {
    throw new Error(`聊天接口请求失败，状态码：${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';

  let isDone = false;

  while (!isDone) {
    const { value, done } = await reader.read();
    isDone = done;
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split('\n\n');
    buffer = events.pop() ?? '';

    for (const eventChunk of events) {
      const lines = eventChunk
        .split('\n')
        .map((line) => line.trim())
        .filter((line) => line.startsWith('data:'));

      for (const line of lines) {
        const payloadText = line.slice(5).trim();
        if (!payloadText) {
          continue;
        }

        const payload = JSON.parse(payloadText) as {
          type?: string;
          content?: string;
          message?: string;
        };

        if (payload.type === 'delta' && payload.content) {
          appendMessageContent(assistantMessageId, payload.content);
          scrollToBottom();
        }

        if (payload.type === 'error') {
          throw new Error(payload.message || '聊天流返回了错误事件');
        }

        if (payload.type === 'done') {
          return;
        }
      }
    }
  }
};

const executeAssistantGeneration = async (
  requestSnapshot: ChatRequestSnapshot,
) => {
  const assistantNode = createAssistantVariant(requestSnapshot.userMessageId);
  const abortController = new AbortController();

  isLoading.value = true;
  activeGeneration.value = {
    assistantId: assistantNode.id,
    userMessageId: requestSnapshot.userMessageId,
    controller: abortController,
  };
  scrollToBottom();

  try {
    await streamAssistantReply(
      requestSnapshot,
      assistantNode.id,
      abortController,
    );

    const streamedAssistantMessage = findMessageById(assistantNode.id);
    if (streamedAssistantMessage && !streamedAssistantMessage.content.trim()) {
      updateMessageContent(
        assistantNode.id,
        '模型已完成响应，但没有返回可显示的文本内容。',
      );
    }
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      return;
    }

    const errorMessage =
      error instanceof Error ? error.message : '聊天请求失败，请稍后重试。';
    updateMessageContent(assistantNode.id, `请求失败：${errorMessage}`);
  } finally {
    activeGeneration.value = null;
    isLoading.value = false;
  }
};

const resetEditingState = () => {
  editingMessageId.value = null;
  editingDraftText.value = '';
  editingDraftFiles.value = [];
};

const showCopyToast = (message: string) => {
  copyToastMessage.value = message;
  isCopyToastVisible.value = true;

  if (copyToastTimer) {
    clearTimeout(copyToastTimer);
  }

  copyToastTimer = setTimeout(() => {
    isCopyToastVisible.value = false;
  }, 1600);
};

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

const onSelectModel = (model: string) => {
  selectedModel.value = model;
};

const onSelectProcessingMode = (mode: string) => {
  selectedProcessingMode.value = mode;
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
  resetEditingState();
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

  await executeAssistantGeneration(
    buildRequestSnapshotForUserMessage(assistantNode.parentId),
  );
};

const loadAvailableModels = async () => {
  try {
    const response = await axios.get<{
      models?: Array<{ name?: string; model?: string; id?: string }>;
      data?: Array<{ name?: string; model?: string; id?: string }>;
    }>('/api/models');
    const rawModels = response.data.models ?? response.data.data ?? [];
    const modelNames = rawModels
      .map((item) => item.name ?? item.model ?? item.id ?? '')
      .map((name) => name.trim())
      .filter((name) => name.length > 0);

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
    const response = await axios.get<{
      skills?: Array<{
        id?: string;
        display_name?: string;
        displayName?: string;
        short_description?: string;
        shortDescription?: string;
      }>;
      default_skill_id?: string;
      defaultSkillId?: string;
    }>('/api/skills');

    const rawSkills = response.data.skills ?? [];
    const nextSkills = rawSkills
      .map((skill) => {
        const id = skill.id?.trim() ?? '';
        const displayName = (
          skill.display_name ??
          skill.displayName ??
          skill.id ??
          ''
        ).trim();
        const shortDescription = (
          skill.short_description ??
          skill.shortDescription ??
          ''
        ).trim();

        if (!id || !displayName) {
          return null;
        }

        return {
          id,
          displayName,
          shortDescription,
        } satisfies SkillOption;
      })
      .filter((skill): skill is SkillOption => skill !== null);

    if (nextSkills.length === 0) {
      return;
    }

    processingModes.value = nextSkills;
    const defaultSkillId =
      response.data.default_skill_id?.trim() ||
      response.data.defaultSkillId?.trim() ||
      'document-assistant';

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
  void loadAvailableSkills();
  void loadAvailableModels();
});

onBeforeUnmount(() => {
  if (copyToastTimer) {
    clearTimeout(copyToastTimer);
  }
});
</script>

<style scoped>
.chat-layout {
  display: flex;
  height: 100vh;
  background: #f5f5f5;
  overflow: hidden;
}

.chat-main {
  position: relative;
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  background: white;
  border-left: 1px solid #e0e0e0;
  overflow: hidden;
}

.chat-messages {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.copy-toast-enter-active,
.copy-toast-leave-active {
  transition:
    opacity 0.26s ease,
    transform 0.26s ease,
    filter 0.26s ease;
}

.copy-toast-enter-from,
.copy-toast-leave-to {
  opacity: 0;
  transform: translate(-50%, -10px) scale(0.96);
  filter: blur(6px);
}

.copy-toast {
  position: fixed;
  left: 50%;
  top: 1.25rem;
  transform: translateX(-50%);
  min-width: 240px;
  display: flex;
  align-items: center;
  gap: 0.8rem;
  padding: 0.85rem 1rem;
  border-radius: 18px;
  border: 1px solid rgba(255, 255, 255, 0.72);
  background: rgba(255, 255, 255, 0.92);
  color: #1f2937;
  backdrop-filter: blur(14px);
  box-shadow:
    0 18px 40px rgba(15, 23, 42, 0.14),
    0 6px 16px rgba(15, 23, 42, 0.08);
  pointer-events: none;
  z-index: 30;
}

.copy-toast-icon {
  width: 2rem;
  height: 2rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: linear-gradient(135deg, #16a34a, #22c55e);
  color: white;
  flex-shrink: 0;
  box-shadow: 0 10px 18px rgba(34, 197, 94, 0.24);
}

.copy-toast-icon-svg {
  width: 1rem;
  height: 1rem;
}

.copy-toast-content {
  display: flex;
  flex-direction: column;
  gap: 0.08rem;
}

.copy-toast-title {
  font-size: 0.92rem;
  font-weight: 700;
  letter-spacing: 0.01em;
}

.copy-toast-description {
  font-size: 0.8rem;
  color: #5b6472;
}
</style>
