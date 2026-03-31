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
      <div class="chat-messages" ref="messageContainerRef">
        <ChatMessage
          v-for="msg in displayedMessages"
          :key="msg.id"
          :message="msg"
          :is-thinking="isMessageThinking(msg)"
        />
      </div>
      <ChatInput
        ref="inputRef"
        v-model:text="inputText"
        :files="selectedFiles"
        :can-regenerate="canRegenerate"
        @upload-files="onFilesSelect"
        @send="onSendMessage"
        @stop="onStopGeneration"
        @regenerate="onRegenerate"
        @clear-all-files="onClearAllFiles"
        @remove-file="onRemoveFile"
        :is-loading="isLoading"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import axios from 'axios';
import { ref, computed, onMounted, nextTick } from 'vue';
import ChatSidebar from './ChatSidebar.vue';
import ChatMessage from './ChatMessage.vue';
import ChatInput from './ChatInput.vue';

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

const welcomeMessages: ChatMessage[] = [
  {
    id: 'welcome-1',
    role: 'system',
    content: '你好！我是文档处理助手。请上传文档或输入问题，我会帮你处理。',
    timestamp: new Date(),
  },
];

const messages = ref<Array<ChatMessage>>([]);

const inputText = ref('');
const selectedFiles = ref<File[]>([]);
const selectedProcessingMode = ref<ProcessingMode>('智能问答');
const selectedModel = ref(fallbackModels[0]);
const availableModels = ref(fallbackModels);
const isLoading = ref(false);
const canRegenerate = ref(false);
const activeStreamController = ref<AbortController | null>(null);
const activeAssistantMessageId = ref<string | null>(null);
const lastRequestSnapshot = ref<ChatRequestSnapshot | null>(null);
const messagesCount = computed(() => messages.value.length);
const displayedMessages = computed(() => {
  return messages.value.length > 0 ? messages.value : welcomeMessages;
});

// DOM 引用
const messageContainerRef = ref<HTMLElement | null>(null);
const inputRef = ref<InstanceType<typeof ChatInput> | null>(null);

// 滚动到底部
const scrollToBottom = () => {
  nextTick(() => {
    if (messageContainerRef.value) {
      messageContainerRef.value.scrollTop =
        messageContainerRef.value.scrollHeight;
    }
  });
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

// 页面初始化时同步处理滚动和模型列表加载。
onMounted(() => {
  scrollToBottom();
  void loadAvailableModels();
});

// 消息类型定义
interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
}

interface ApiChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

interface ChatRequestSnapshot {
  model: string;
  processingMode: ProcessingMode;
  messages: ApiChatMessage[];
}

// 优先使用浏览器原生 UUID，减少首屏依赖体积。
const createMessageId = () => {
  return crypto.randomUUID();
};

// 事件处理
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
  messages.value = [];
  selectedFiles.value = [];
  canRegenerate.value = false;
  lastRequestSnapshot.value = null;
};

const findMessageById = (messageId: string) => {
  return messages.value.find((message) => message.id === messageId) ?? null;
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

const isMessageThinking = (message: ChatMessage) => {
  return (
    isLoading.value &&
    message.role === 'assistant' &&
    message.id === activeAssistantMessageId.value &&
    !message.content.trim()
  );
};

const markGenerationStopped = () => {
  if (!activeAssistantMessageId.value) {
    return;
  }

  const activeMessage = findMessageById(activeAssistantMessageId.value);
  if (!activeMessage) {
    return;
  }

  if (activeMessage.content.trim()) {
    if (!activeMessage.content.includes('[已停止生成]')) {
      activeMessage.content += '\n\n[已停止生成]';
    }
    return;
  }

  activeMessage.content = '已停止生成。';
};

const clearActiveGenerationState = () => {
  activeStreamController.value = null;
  activeAssistantMessageId.value = null;
};

const onStopGeneration = () => {
  if (activeStreamController.value) {
    activeStreamController.value.abort();
    markGenerationStopped();
    canRegenerate.value = true;
    clearActiveGenerationState();
    isLoading.value = false;
  }
};

const streamAssistantReply = async (
  requestSnapshot: ChatRequestSnapshot,
  assistantMessageId: string,
) => {
  const abortController = new AbortController();
  activeStreamController.value = abortController;
  activeAssistantMessageId.value = assistantMessageId;

  const response = await fetch('/api/chat/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    signal: abortController.signal,
    body: JSON.stringify({
      model: requestSnapshot.model,
      processing_mode: requestSnapshot.processingMode,
      messages: requestSnapshot.messages,
    }),
  });

  if (!response.ok || !response.body) {
    throw new Error(`聊天接口请求失败，状态码：${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';

  while (true) {
    const { value, done } = await reader.read();
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

const onSendMessage = async () => {
  const text = inputText.value.trim();
  if ((!text && selectedFiles.value.length === 0) || isLoading.value) return;
  canRegenerate.value = false;

  const userContent =
    text || `（上传了 ${selectedFiles.value.length} 个文件，文件联调尚未接入后端）`;
  const requestMessages: ApiChatMessage[] = [
    ...messages.value.map((message) => ({
      role: message.role,
      content: message.content,
    })),
    {
      role: 'user',
      content: userContent,
    },
  ];
  const requestSnapshot: ChatRequestSnapshot = {
    model: selectedModel.value,
    processingMode: selectedProcessingMode.value,
    messages: requestMessages,
  };
  lastRequestSnapshot.value = requestSnapshot;

  // 添加用户消息
  const userMessage: ChatMessage = {
    id: createMessageId(),
    role: 'user',
    content: userContent,
    timestamp: new Date(),
  };
  messages.value.push(userMessage);
  scrollToBottom();

  // 重置输入
  inputText.value = '';
  selectedFiles.value = [];

  // 模拟 AI 响应
  isLoading.value = true;
  const assistantMessageId = createMessageId();
  messages.value.push({
    id: assistantMessageId,
    role: 'assistant',
    content: '',
    timestamp: new Date(),
  });
  scrollToBottom();

  try {
    await streamAssistantReply(requestSnapshot, assistantMessageId);

    const streamedAssistantMessage = findMessageById(assistantMessageId);
    if (streamedAssistantMessage && !streamedAssistantMessage.content.trim()) {
      updateMessageContent(
        assistantMessageId,
        '模型已完成响应，但没有返回可显示的文本内容。',
      );
    }
    canRegenerate.value = false;
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      return;
    }

    const errorMessage =
      error instanceof Error ? error.message : '聊天请求失败，请稍后重试。';
    updateMessageContent(assistantMessageId, `请求失败：${errorMessage}`);
    canRegenerate.value = true;
  } finally {
    clearActiveGenerationState();
    isLoading.value = false;
  }
};

const onRegenerate = async () => {
  if (!lastRequestSnapshot.value || isLoading.value) {
    return;
  }

  const lastMessage = messages.value.at(-1);
  if (lastMessage?.role === 'assistant') {
    messages.value.pop();
  }

  const assistantMessageId = createMessageId();
  messages.value.push({
    id: assistantMessageId,
    role: 'assistant',
    content: '',
    timestamp: new Date(),
  });
  scrollToBottom();

  isLoading.value = true;
  canRegenerate.value = false;

  try {
    await streamAssistantReply(lastRequestSnapshot.value, assistantMessageId);

    const streamedAssistantMessage = findMessageById(assistantMessageId);
    if (streamedAssistantMessage && !streamedAssistantMessage.content.trim()) {
      updateMessageContent(
        assistantMessageId,
        '模型已完成响应，但没有返回可显示的文本内容。',
      );
    }
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      return;
    }

    const errorMessage =
      error instanceof Error ? error.message : '重新生成失败，请稍后重试。';
    updateMessageContent(assistantMessageId, `请求失败：${errorMessage}`);
    canRegenerate.value = true;
  } finally {
    clearActiveGenerationState();
    isLoading.value = false;
  }
};
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
