<template>
  <div class="chat-page">
    <AppHeader
      page-id="chat"
      :title-clickable="!isSidebarLocked"
      @go-home="$emit('go-home')"
      @title-click="onHeaderTitleClick"
    />
    <div class="chat-page-body">
      <ChatSidebar
        :sessions="chatStore.sessionSummaries"
        :active-session-id="chatStore.activeSessionId"
        :is-locked="isSidebarLocked"
        @load-session="onLoadSession"
        @rename-session="onRenameSession"
        @delete-session="onDeleteSession"
      />
      <div class="chat-main">
        <Transition name="session-switch" mode="out-in">
          <div
            :key="chatStore.sessionViewKey"
            ref="messageContainerRef"
            class="chat-messages"
          >
            <ChatMessage
              v-for="message in chatStore.displayedMessages"
              :key="message.id"
              :message="message"
              :is-thinking="chatStore.isMessageThinking(message)"
              :is-streaming="chatStore.isMessageStreaming(message)"
              :version-index="chatStore.getMessageVersionIndex(message.id)"
              :version-count="chatStore.getMessageVersionCount(message.id)"
              :show-version-switcher="
                chatStore.getMessageVersionCount(message.id) > 1
              "
              :can-go-prev="chatStore.canSwitchMessageVersion(message.id, -1)"
              :can-go-next="chatStore.canSwitchMessageVersion(message.id, 1)"
              :can-edit="message.role === 'user' && !chatStore.isLoading"
              :can-regenerate="
                message.role === 'assistant' && !chatStore.isLoading
              "
              :can-copy="message.content.trim().length > 0"
              :can-download="
                message.role === 'assistant' &&
                message.content.trim().length > 0
              "
              :is-version-locked="
                message.role !== 'system' && chatStore.isLoading
              "
              :is-editing="chatStore.editingMessageId === message.id"
              :editing-text="chatStore.editingDraftText"
              :editing-files="
                chatStore.editingMessageId === message.id
                  ? chatStore.editingDraftFiles
                  : []
              "
              :editing-skill-ids="
                chatStore.editingMessageId === message.id
                  ? chatStore.editingDraftSkillIds
                  : []
              "
              :available-skills="appStore.processingModes"
              :can-confirm-edit="chatStore.canConfirmEdit"
              :show-toolbar-by-default="
                message.id === chatStore.lastAssistantMessageId
              "
              :cache-scope-id="
                chatStore.activeSessionId ?? chatStore.conversationId
              "
              :can-open-trace="
                message.role === 'assistant' &&
                typeof message.trace_id === 'string' &&
                message.trace_id.trim().length > 0 &&
                !chatStore.isMessageStreaming(message)
              "
              :live-tool-status="
                message.id === chatStore.activeGeneration?.assistant_id
                  ? chatStore.latestLiveToolStatus
                  : null
              "
              @prev-version="chatStore.switchMessageVersion(message.id, -1)"
              @next-version="chatStore.switchMessageVersion(message.id, 1)"
              @start-edit="startEditingMessage(message.id)"
              @update-edit-text="updateEditingText"
              @update-edit-skill-ids="updateEditingSkillIds"
              @upload-edit-files="appendEditingFiles"
              @remove-edit-file="removeEditingFile"
              @cancel-edit="cancelEditingMessage"
              @confirm-edit="confirmEditingMessage"
              @regenerate="onRegenerate(message.id)"
              @copy="copyMessage(message.id)"
              @download="downloadAssistantMessage(message.id)"
              @download-file="downloadMessageFile"
              @open-trace="openMessageTrace(message.id)"
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
          v-model:text="chatStore.inputText"
          :files="chatStore.selectedFiles"
          :available-skills="appStore.processingModes"
          :selected-skill-ids="chatStore.selectedSkillIds"
          :is-loading="chatStore.isLoading"
          @update:selected-skill-ids="updateSelectedSkillIds"
          @upload-files="onFilesSelect"
          @send="onSendMessage"
          @stop="onStopGeneration"
          @clear-all-files="onClearAllFiles"
          @remove-file="onRemoveFile"
        />
      </div>
    </div>
    <TraceReplayModal
      :visible="isTraceModalVisible"
      :trace-id="activeTraceId"
      :loading="isTraceModalLoading"
      :error-message="traceModalErrorMessage"
      :payload="activeTracePayload"
      @close="closeTraceModal"
      @retry="retryTraceModalLoad"
      @copy-trace-id="copyTraceId"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue';
import { useAppStore } from '../stores/app';
import { useChatStore } from '../stores/chat';
import { useCatalogLoader } from '../composables/useCatalogLoader';
import { useChatSessions } from '../composables/useChatSessions';
import { useChatStreaming } from '../composables/useChatStreaming';
import { useCopyToast } from '../composables/useCopyToast';
import { useMessageActions } from '../composables/useMessageActions';
import { useTraceModal } from '../composables/useTraceModal';
import AppHeader from '../components/AppHeader.vue';
import ChatInput from '../components/ChatInput.vue';
import ChatMessage from '../components/ChatMessage.vue';
import ChatSidebar from '../components/ChatSidebar.vue';
import TraceReplayModal from '../components/TraceReplayModal.vue';

defineEmits<{
  (e: 'go-home'): void;
}>();

const appStore = useAppStore();
const chatStore = useChatStore();

const { copyToastMessage, copyToastTitle, isCopyToastVisible, showCopyToast } =
  useCopyToast();

const messageContainerRef = ref<HTMLElement | null>(null);

const {
  activeTraceId,
  activeTracePayload,
  closeTraceModal,
  copyTraceId,
  isTraceModalLoading,
  isTraceModalVisible,
  openTraceModalByTraceId,
  retryTraceModalLoad,
  traceModalErrorMessage,
} = useTraceModal({
  showCopyToast,
});

const scrollToBottom = () => {
  nextTick(() => {
    if (messageContainerRef.value) {
      messageContainerRef.value.scrollTop =
        messageContainerRef.value.scrollHeight;
    }
  });
};

const {
  deleteChatSession,
  loadChatSession,
  loadSessionSummaries,
  persistCurrentSession,
  renameChatSession,
} = useChatSessions({
  afterSessionLoaded: async () => {
    chatStore.inputText = '';
    chatStore.selectedFiles = [];
    chatStore.selectedSkillIds = [];
    await nextTick();
    chatStore.prewarmVisibleConversationCache(
      chatStore.activeSessionId ?? chatStore.conversationId,
    );
    scrollToBottom();
  },
  onDeleteActiveSession: () => {
    onClearChat();
  },
});

const { executeAssistantGeneration, onStopGeneration } = useChatStreaming({
  scrollToBottom,
  persistCurrentSession: async () => {
    await persistCurrentSession();
  },
});

const {
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
  copyMessage,
  downloadAssistantMessage,
  downloadMessageFile,
} = useMessageActions({
  executeAssistantGeneration,
  scrollToBottom,
  persistCurrentSession: async () => {
    await persistCurrentSession();
  },
  onStopGeneration,
  showCopyToast,
});

const isSidebarLocked = computed(() => chatStore.isLoading);

const openMessageTrace = async (messageId: string) => {
  const targetMessage = chatStore.findMessageById(messageId);
  const traceId = targetMessage?.trace_id?.trim() ?? '';
  if (!traceId) {
    showCopyToast('这条回复还没有可查看的 trace_id。', {
      title: '暂无链路信息',
    });
    return;
  }
  await openTraceModalByTraceId(traceId);
};

const updateSelectedSkillIds = (skillIds: string[]) => {
  chatStore.selectedSkillIds = [...skillIds];
};

const updateEditingSkillIds = (skillIds: string[]) => {
  chatStore.editingDraftSkillIds = [...skillIds];
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

const onNewChat = async () => {
  if (chatStore.isLoading) {
    onStopGeneration();
  }
  if (chatStore.activeSessionId && chatStore.rootChildIds.length > 0) {
    await persistCurrentSession();
  }
  chatStore.resetChatState();
};

const onHeaderTitleClick = async () => {
  await onNewChat();
};

const { loadAvailableModels, loadAvailableSkills } = useCatalogLoader();

onMounted(() => {
  scrollToBottom();
  void loadSessionSummaries();
  void loadAvailableSkills();
  void loadAvailableModels();
  chatStore.prewarmVisibleConversationCache(
    chatStore.activeSessionId ?? chatStore.conversationId,
  );
});
</script>

<style scoped src="../styles/components/chat-page.css"></style>
