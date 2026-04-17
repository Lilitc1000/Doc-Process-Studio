<template>
  <div class="chat-layout">
    <ChatSidebar
      :models="appStore.availableModels"
      :selected-model="appStore.selectedModel"
      :selected-reranker-model="appStore.selectedRerankerModel"
      :sessions="sidebarSessions"
      :active-session-id="sidebarActiveSessionId"
      :workspaces="workspaceTabs"
      :active-workspace-id="appStore.activeWorkspaceId"
      :is-locked="isSidebarLocked"
      @select-workspace="onSelectWorkspace"
      @select-model="onSelectModel"
      @select-reranker-model="onSelectRerankerModel"
      @load-session="onLoadSession"
      @rename-session="onRenameSession"
      @delete-session="onDeleteSession"
    />
    <div class="chat-main">
      <Transition name="workspace-switch" mode="out-in">
        <div :key="appStore.activeWorkspaceId" class="workspace-panel">
          <template v-if="appStore.activeWorkspaceId === 'chat'">
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
                  :can-go-prev="
                    chatStore.canSwitchMessageVersion(message.id, -1)
                  "
                  :can-go-next="
                    chatStore.canSwitchMessageVersion(message.id, 1)
                  "
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
                  <span class="copy-toast-description">{{
                    copyToastMessage
                  }}</span>
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
          </template>

          <template v-else>
            <IncidentReportWorkspace
              :schema="incidentStore.incidentSchema"
              :session="incidentStore.activeIncidentSession"
              :is-generating="incidentStore.isIncidentGenerating"
              :generation-state="incidentStore.generationState"
              :generation-trace-id="incidentStore.incidentGenerationTraceId"
              :generation-progress-lines="
                incidentStore.incidentGenerationProgress
              "
              @start="onStartIncident"
              @update-answers="onIncidentAnswersUpdate"
              @generate="onIncidentGenerate"
              @stop-generation="onIncidentStopGeneration"
              @download="onIncidentDownload"
              @open-trace="onIncidentOpenTrace"
              @close-notice="closeGenerationNotice"
            />
          </template>
        </div>
      </Transition>
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
import { useIncidentStore } from '../stores/incident';
import { useCatalogLoader } from '../composables/useCatalogLoader';
import { useChatSessions } from '../composables/useChatSessions';
import { useChatStreaming } from '../composables/useChatStreaming';
import { useCopyToast } from '../composables/useCopyToast';
import { useIncidentReportSessions } from '../composables/useIncidentReportSessions';
import { useMessageActions } from '../composables/useMessageActions';
import { useTraceModal } from '../composables/useTraceModal';
import type { IncidentFormAnswer } from '../types/incident-report';
import ChatInput from './ChatInput.vue';
import ChatMessage from './ChatMessage.vue';
import ChatSidebar from './ChatSidebar.vue';
import IncidentReportWorkspace from './IncidentReportWorkspace.vue';
import TraceReplayModal from './TraceReplayModal.vue';

const appStore = useAppStore();
const chatStore = useChatStore();
const incidentStore = useIncidentStore();

const workspaceTabs = [
  { id: 'chat', label: '对话' },
  { id: 'incident-report', label: '事故报告' },
];

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

const {
  clearActiveIncidentSession,
  closeGenerationNotice,
  deleteIncident,
  downloadGeneratedIncidentAttachment,
  generateIncident,
  loadIncidentSchema,
  loadIncidentSession,
  loadIncidentSessionSummaries,
  renameIncident,
  startIncidentSession,
  stopIncidentGeneration,
  updateIncidentAnswers,
} = useIncidentReportSessions();

const isSidebarLocked = computed(() => {
  return chatStore.isLoading || incidentStore.isIncidentGenerating;
});

const sidebarSessions = computed(() => {
  return appStore.activeWorkspaceId === 'chat'
    ? chatStore.sessionSummaries
    : incidentStore.incidentSidebarSessions;
});

const sidebarActiveSessionId = computed(() => {
  return appStore.activeWorkspaceId === 'chat'
    ? chatStore.activeSessionId
    : incidentStore.activeIncidentSessionId;
});

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

const onSelectWorkspace = async (workspaceId: string) => {
  if (workspaceId === 'chat') {
    appStore.activeWorkspaceId = 'chat';
    onClearChat();
    return;
  }

  appStore.activeWorkspaceId = 'incident-report';
  clearActiveIncidentSession();
};

const onSelectModel = (model: string) => {
  appStore.selectedModel = model;
  if (!appStore.availableModels.includes(appStore.selectedRerankerModel)) {
    appStore.selectedRerankerModel = model;
  }
  if (chatStore.activeSessionId && chatStore.rootChildIds.length > 0) {
    void persistCurrentSession();
  }
};

const onSelectRerankerModel = (model: string) => {
  appStore.selectedRerankerModel = model;
  if (chatStore.activeSessionId && chatStore.rootChildIds.length > 0) {
    void persistCurrentSession();
  }
};

const updateSelectedSkillIds = (skillIds: string[]) => {
  chatStore.selectedSkillIds = [...skillIds];
};

const updateEditingSkillIds = (skillIds: string[]) => {
  chatStore.editingDraftSkillIds = [...skillIds];
};

const onLoadSession = async (sessionId: string) => {
  if (appStore.activeWorkspaceId === 'chat') {
    await loadChatSession(sessionId);
    return;
  }
  await loadIncidentSession(sessionId);
};

const onRenameSession = async (payload: {
  sessionId: string;
  title: string;
}) => {
  if (appStore.activeWorkspaceId === 'chat') {
    await renameChatSession(payload.sessionId, payload.title);
    return;
  }
  await renameIncident(payload.sessionId, payload.title);
};

const onDeleteSession = async (sessionId: string) => {
  if (appStore.activeWorkspaceId === 'chat') {
    await deleteChatSession(sessionId);
    return;
  }
  await deleteIncident(sessionId);
};

const onStartIncident = async () => {
  await startIncidentSession();
};

const onIncidentAnswersUpdate = (
  answers: Record<string, IncidentFormAnswer>,
) => {
  updateIncidentAnswers(answers);
};

const onIncidentGenerate = async () => {
  try {
    await generateIncident(
      appStore.selectedModel,
      appStore.selectedRerankerModel,
    );
    await loadIncidentSessionSummaries();
  } catch (error) {
    const message =
      error instanceof Error ? error.message : '生成附件失败，请稍后重试。';
    showCopyToast(message, { title: '生成失败' });
  }
};

const onIncidentStopGeneration = () => {
  stopIncidentGeneration();
};

const onIncidentDownload = async () => {
  try {
    await downloadGeneratedIncidentAttachment();
  } catch (error) {
    const message =
      error instanceof Error ? error.message : '下载失败，请稍后重试。';
    showCopyToast(message, { title: '下载失败' });
  }
};

const onIncidentOpenTrace = (traceId: string) => {
  void openTraceModalByTraceId(traceId);
};

const { loadAvailableModels, loadAvailableSkills } = useCatalogLoader();

onMounted(() => {
  scrollToBottom();
  void loadSessionSummaries();
  void loadIncidentSchema();
  void loadIncidentSessionSummaries();
  void loadAvailableSkills();
  void loadAvailableModels();
  chatStore.prewarmVisibleConversationCache(
    chatStore.activeSessionId ?? chatStore.conversationId,
  );
});
</script>

<style scoped src="../styles/components/chat-layout.css"></style>
