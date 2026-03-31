<template>
  <div class="chat-layout">
    <ChatSidebar
      :models="availableModels"
      :selected-model="selectedModel"
      :messages-count="messagesCount"
      @select-model="onSelectModel"
      @clear-chat="onClearChat"
    />
    <div class="chat-main">
      <div class="chat-messages" ref="messageContainerRef">
        <ChatMessage v-for="msg in messages" :key="msg.id" :message="msg" />
        <div v-if="isLoading" class="loading-indicator">
          <span class="loading-text">正在思考中...</span>
          <div class="loading-dots">
            <span></span><span></span><span></span>
          </div>
        </div>
      </div>
      <ChatInput
        ref="inputRef"
        v-model:text="inputText"
        :files="selectedFiles"
        @upload-files="onFilesSelect"
        @send="onSendMessage"
        @clear-all-files="onClearAllFiles"
        @remove-file="onRemoveFile"
        :is-loading="isLoading"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue';
import ChatSidebar from './ChatSidebar.vue';
import ChatMessage from './ChatMessage.vue';
import ChatInput from './ChatInput.vue';
import { v4 as uuidv4 } from 'uuid';

// 状态
const messages = ref<Array<ChatMessage>>([
  {
    id: 'welcome-1',
    role: 'system',
    content: '你好！我是文档处理助手。请上传文档或输入问题，我会帮你处理。',
    timestamp: new Date(),
  },
]);

const inputText = ref('');
const selectedFiles = ref<File[]>([]);
const selectedModel = ref('gpt-4o-mini');
const availableModels = ref([
  'gpt-4o-mini',
  'gpt-4o',
  'claude-3.5-sonnet',
  'deepseek-v3',
]);
const isLoading = ref(false);
const messagesCount = computed(() => messages.value.length);

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

// 监听消息变化，自动滚动
onMounted(() => {
  scrollToBottom();
});

// 消息类型定义
interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
}

// 事件处理
const onSelectModel = (model: string) => {
  selectedModel.value = model;
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
  messages.value = [];
  selectedFiles.value = [];
};

const onSendMessage = async () => {
  const text = inputText.value.trim();
  if (!text && selectedFiles.value.length === 0) return;

  // 添加用户消息
  const userMessage: ChatMessage = {
    id: uuidv4(),
    role: 'user',
    content: text || `（上传了 ${selectedFiles.value.length} 个文件）`,
    timestamp: new Date(),
  };
  messages.value.push(userMessage);
  scrollToBottom();

  // 重置输入
  inputText.value = '';
  const uploadedFiles = selectedFiles.value.length;
  selectedFiles.value = [];

  // 模拟 AI 响应
  isLoading.value = true;

  try {
    // 模拟网络延迟
    await new Promise((resolve) =>
      setTimeout(resolve, 1000 + Math.random() * 1500),
    );

    const assistantMessage: ChatMessage = {
      id: uuidv4(),
      role: 'assistant',
      content: `收到！你正在使用模型 **${selectedModel.value}** 处理文档。\n\n> 这是一个模拟回复，展示了消息格式。后续会连接后端 API 获取真实响应。\n\n当前消息数量：${messages.value.length}\n\n已上传文件数：${uploadedFiles}`,
      timestamp: new Date(),
    };
    messages.value.push(assistantMessage);
    scrollToBottom();
  } finally {
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

.loading-indicator {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: #f0f0f0;
  border-radius: 1rem;
  width: fit-content;
  margin: 0 auto;
}

.loading-dots span {
  display: inline-block;
  width: 6px;
  height: 6px;
  background: #666;
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out both;
}

.loading-dots span:nth-child(1) {
  animation-delay: -0.32s;
}

.loading-dots span:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes bounce {
  0%,
  80%,
  100% {
    transform: scale(0);
  }

  40% {
    transform: scale(1);
  }
}
</style>
