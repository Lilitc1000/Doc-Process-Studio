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
          :version-index="getAssistantVersionIndex(message.id)"
          :version-count="getAssistantVersionCount(message.id)"
          :can-go-prev="canSwitchAssistantVersion(message.id, -1)"
          :can-go-next="canSwitchAssistantVersion(message.id, 1)"
          :can-regenerate="message.role === 'assistant' && !isLoading"
          :can-copy="
            message.role === 'assistant' && message.content.trim().length > 0
          "
          :can-download="
            message.role === 'assistant' && message.content.trim().length > 0
          "
          :is-version-locked="message.role === 'assistant' && isLoading"
          @prev-version="switchAssistantVersion(message.id, -1)"
          @next-version="switchAssistantVersion(message.id, 1)"
          @regenerate="onRegenerate(message.id)"
          @copy="copyAssistantMessage(message.id)"
          @download="downloadAssistantMessage(message.id)"
        />
      </div>
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
import { computed, nextTick, onMounted, ref } from 'vue';
import ChatInput from './ChatInput.vue';
import ChatMessage from './ChatMessage.vue';
import ChatSidebar from './ChatSidebar.vue';

const fallbackModels = [
  'gpt-4o-mini',
  'gpt-4o',
  'claude-3.5-sonnet',
  'deepseek-v3',
];
const processingModes = [
  '快速摘要',
  '智能问答',
  '结构化提取',
  '全文整理',
] as const;

type ProcessingMode = (typeof processingModes)[number];
type ChatMessageRole = 'user' | 'assistant' | 'system';

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
  processingMode: ProcessingMode;
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
    content: '你好！我是文档处理助手。请上传文档或输入问题，我会帮你处理。',
    timestamp: new Date(),
    parentId: null,
    childIds: [],
  },
];

const inputText = ref('');
const selectedFiles = ref<File[]>([]);
const selectedProcessingMode = ref<ProcessingMode>('智能问答');
const selectedModel = ref(fallbackModels[0]);
const availableModels = ref(fallbackModels);
const isLoading = ref(false);
const messageNodes = ref<Record<string, ChatMessageNode>>({});
const rootMessageId = ref<string | null>(null);
const selectedChildIdByParent = ref<Record<string, string>>({});
const activeGeneration = ref<ActiveGenerationState | null>(null);

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
  if (!rootMessageId.value) {
    return welcomeMessages;
  }

  const visibleMessages: ChatMessageNode[] = [];
  let currentMessageId: string | null = rootMessageId.value;

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
  return rootMessageId.value ? displayedMessages.value.length : 0;
});

const currentLeafMessageId = computed(() => {
  if (!rootMessageId.value) {
    return null;
  }

  const lastMessage =
    displayedMessages.value[displayedMessages.value.length - 1] ?? null;
  return lastMessage?.id ?? null;
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
    rootMessageId.value = messageId;
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
    processingMode: selectedProcessingMode.value,
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

const getAssistantSiblingIds = (assistantMessageId: string) => {
  const assistantNode = getNodeById(assistantMessageId);
  if (!assistantNode?.parentId) {
    return [assistantMessageId];
  }

  const parentNode = getNodeById(assistantNode.parentId);
  if (!parentNode) {
    return [assistantMessageId];
  }

  return parentNode.childIds.filter((childId) => {
    return getNodeById(childId)?.role === 'assistant';
  });
};

const getAssistantVersionIndex = (assistantMessageId: string) => {
  const assistantNode = getNodeById(assistantMessageId);
  if (assistantNode?.role !== 'assistant') {
    return 0;
  }

  const siblingIds = getAssistantSiblingIds(assistantMessageId);
  const currentIndex = siblingIds.indexOf(assistantMessageId);
  return currentIndex >= 0 ? currentIndex + 1 : 1;
};

const getAssistantVersionCount = (assistantMessageId: string) => {
  const assistantNode = getNodeById(assistantMessageId);
  if (assistantNode?.role !== 'assistant') {
    return 0;
  }

  return getAssistantSiblingIds(assistantMessageId).length;
};

const canSwitchAssistantVersion = (
  assistantMessageId: string,
  direction: -1 | 1,
) => {
  const assistantNode = getNodeById(assistantMessageId);
  if (assistantNode?.role !== 'assistant') {
    return false;
  }

  const siblingIds = getAssistantSiblingIds(assistantMessageId);
  const currentIndex = siblingIds.indexOf(assistantMessageId);
  const targetIndex = currentIndex + direction;

  return targetIndex >= 0 && targetIndex < siblingIds.length;
};

const switchAssistantVersion = (
  assistantMessageId: string,
  direction: -1 | 1,
) => {
  const assistantNode = getNodeById(assistantMessageId);
  if (
    !assistantNode?.parentId ||
    assistantNode.role !== 'assistant' ||
    isLoading.value
  ) {
    return;
  }

  const siblingIds = getAssistantSiblingIds(assistantMessageId);
  const currentIndex = siblingIds.indexOf(assistantMessageId);
  const targetMessageId = siblingIds[currentIndex + direction];

  if (targetMessageId) {
    selectedChildIdByParent.value[assistantNode.parentId] = targetMessageId;
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
          processing_mode: requestSnapshot.processingMode,
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

const copyAssistantMessage = async (assistantMessageId: string) => {
  const assistantNode = getNodeById(assistantMessageId);
  if (!assistantNode?.content.trim() || !navigator.clipboard) {
    return;
  }

  try {
    await navigator.clipboard.writeText(assistantNode.content);
  } catch (error) {
    console.error('复制 AI 回复失败。', error);
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
  selectedProcessingMode.value = mode as ProcessingMode;
};

const onFilesSelect = (files: File[]) => {
  selectedFiles.value = files;
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
  rootMessageId.value = null;
  selectedChildIdByParent.value = {};
  selectedFiles.value = [];
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

onMounted(() => {
  scrollToBottom();
  void loadAvailableModels();
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
</style>
