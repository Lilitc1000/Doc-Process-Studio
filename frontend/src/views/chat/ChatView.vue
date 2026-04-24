<template>
  <div class="chat-page">
    <div class="chat-page-body">
      <session-sidebar
        :sessions="chatStore.sessionSummaries"
        :active-session-id="chatStore.activeSessionId"
        :is-locked="isSidebarLocked"
        @load-session="onLoadSession"
        @rename-session="onRenameSession"
        @delete-session="onDeleteSession"
      />
      <div class="chat-main">
        <transition name="session-switch" mode="out-in">
          <div
            :key="chatStore.sessionViewKey"
            ref="messageContainerRef"
            class="chat-messages"
          >
            <chat-message
              v-for="message in chatStore.displayedMessages"
              :key="message.id"
              :message="message"
              :cache-scope-id="
                chatStore.activeSessionId ?? chatStore.conversationId
              "
              :is-thinking="chatStore.isMessageThinking(message)"
              :is-streaming="chatStore.isMessageStreaming(message)"
              :is-editing="chatStore.editingMessageId === message.id"
              :editing-text="chatStore.editingDraftText"
              :editing-files="chatStore.editingDraftFiles"
              :editing-skill-ids="chatStore.editingDraftSkillIds"
              :available-skills="appStore.processingModes"
              :is-loading="chatStore.isLoading"
              :live-tool-status="chatStore.latestLiveToolStatus"
              :show-version-switcher="
                chatStore.getMessageVersionCount(message.id) > 1
              "
              :version-index="chatStore.getMessageVersionIndex(message.id)"
              :version-count="chatStore.getMessageVersionCount(message.id)"
              :can-go-prev="chatStore.canSwitchMessageVersion(message.id, -1)"
              :can-go-next="chatStore.canSwitchMessageVersion(message.id, 1)"
              :can-open-trace="!!message.traceId"
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
        </transition>
        <floating-toast
          :visible="isCopyToastVisible"
          :title="copyToastTitle"
          :message="copyToastMessage"
        />
        <chat-input
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
    <trace-replay-modal
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
import { useAppStore } from '../../stores/app';
import { useChatStore } from '../../stores/chat';
import { useCatalogLoader } from '../../composables/business/useCatalogLoader';
import { useChatSessions } from './composables/useChatSessions';
import { useChatStreaming } from './composables/useChatStreaming';
import { useCopyToast } from '../../composables/business/useCopyToast';
import { useMessageActions } from './composables/useMessageActions';
import { useTraceModal } from '../../composables/business/useTraceModal';
import FloatingToast from '../../components/business/FloatingToast.vue';
import SessionSidebar from '../../components/business/SessionSidebar.vue';
import TraceReplayModal from '../../components/business/TraceReplayModal.vue';
import ChatInput from './components/ChatInput.vue';
import ChatMessage from './components/ChatMessage.vue';

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

const onHeaderTitleClick = async () => {
  onClearChat();
};

const openMessageTrace = async (messageId: string) => {
  const targetMessage = chatStore.findMessageById(messageId);
  const traceId = targetMessage?.traceId?.trim() ?? '';
  if (!traceId) {
    showCopyToast('这条回复还没有可查看的链路信息。', {
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

const isTitleClickable = computed(() => !chatStore.isLoading);

defineExpose({
  onHeaderTitleClick,
  isTitleClickable,
});

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

<style scoped src="./styles/chat-page.css"></style>
