<template>
  <div class="chat-layout">
    <ChatSidebar
      :models="availableModels"
      :selected-model="selectedModel"
      :selected-reranker-model="selectedRerankerModel"
      :sessions="sidebarSessions"
      :active-session-id="sidebarActiveSessionId"
      :workspaces="workspaceTabs"
      :active-workspace-id="activeWorkspaceId"
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
        <div :key="activeWorkspaceId" class="workspace-panel">
          <template v-if="activeWorkspaceId === 'chat'">
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
                  :show-version-switcher="
                    getMessageVersionCount(message.id) > 1
                  "
                  :can-go-prev="canSwitchMessageVersion(message.id, -1)"
                  :can-go-next="canSwitchMessageVersion(message.id, 1)"
                  :can-edit="message.role === 'user' && !isLoading"
                  :can-regenerate="message.role === 'assistant' && !isLoading"
                  :can-copy="message.content.trim().length > 0"
                  :can-download="
                    message.role === 'assistant' &&
                    message.content.trim().length > 0
                  "
                  :is-version-locked="message.role !== 'system' && isLoading"
                  :is-editing="editingMessageId === message.id"
                  :editing-text="editingDraftText"
                  :editing-files="
                    editingMessageId === message.id ? editingDraftFiles : []
                  "
                  :editing-skill-ids="
                    editingMessageId === message.id ? editingDraftSkillIds : []
                  "
                  :available-skills="processingModes"
                  :can-confirm-edit="canConfirmEdit"
                  :show-toolbar-by-default="
                    message.id === lastAssistantMessageId
                  "
                  :cache-scope-id="activeSessionId ?? conversationId"
                  :can-open-trace="
                    message.role === 'assistant' &&
                    typeof message.trace_id === 'string' &&
                    message.trace_id.trim().length > 0 &&
                    !isMessageStreaming(message)
                  "
                  :live-tool-status="
                    message.id === activeGeneration?.assistant_id
                      ? latestLiveToolStatus
                      : null
                  "
                  @prev-version="switchMessageVersion(message.id, -1)"
                  @next-version="switchMessageVersion(message.id, 1)"
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
              v-model:text="inputText"
              :files="selectedFiles"
              :available-skills="processingModes"
              :selected-skill-ids="selectedSkillIds"
              :is-loading="isLoading"
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
              :schema="incidentSchema"
              :session="activeIncidentSession"
              :is-generating="isIncidentGenerating"
              :generation-state="generationState"
              :generation-trace-id="incidentGenerationTraceId"
              :generation-progress-lines="incidentGenerationProgress"
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
import { downloadAttachment } from '../api/attachments';
import { useCatalogLoader } from '../composables/useCatalogLoader';
import { useChatSessions } from '../composables/useChatSessions';
import { useChatStreaming } from '../composables/useChatStreaming';
import { useCopyToast } from '../composables/useCopyToast';
import { useIncidentReportSessions } from '../composables/useIncidentReportSessions';
import { useMessageActions } from '../composables/useMessageActions';
import { useMessageTree } from '../composables/useMessageTree';
import { useTraceModal } from '../composables/useTraceModal';
import type {
  ChatEditAttachment,
  ChatMessageNode,
  ChatToolStatus,
} from '../types/chat';
import type { IncidentFormAnswer } from '../types/incident-report';
import type { SkillOption } from '../types/skill';
import ChatInput from './ChatInput.vue';
import ChatMessage from './ChatMessage.vue';
import ChatSidebar from './ChatSidebar.vue';
import IncidentReportWorkspace from './IncidentReportWorkspace.vue';
import TraceReplayModal from './TraceReplayModal.vue';

const defaultModels = [
  'gpt-4o-mini',
  'gpt-4o',
  'claude-3.5-sonnet',
  'deepseek-v3',
];

const workspaceTabs = [
  { id: 'chat', label: '对话' },
  { id: 'incident-report', label: '事故报告' },
];

const activeWorkspaceId = ref<'chat' | 'incident-report'>('chat');
const inputText = ref('');
const selectedFiles = ref<File[]>([]);
const selectedSkillIds = ref<string[]>([]);
const processingModes = ref<SkillOption[]>([]);
const selectedModel = ref(defaultModels[0]);
const selectedRerankerModel = ref(defaultModels[0]);
const availableModels = ref(defaultModels);
const messageNodes = ref<Record<string, ChatMessageNode>>({});
const rootChildIds = ref<string[]>([]);
const selectedRootChildId = ref<string | null>(null);
const selectedChildIdByParent = ref<Record<string, string>>({});
const editingMessageId = ref<string | null>(null);
const editingDraftText = ref('');
const editingDraftFiles = ref<ChatEditAttachment[]>([]);
const editingDraftSkillIds = ref<string[]>([]);
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

const resetEditingState = () => {
  editingMessageId.value = null;
  editingDraftText.value = '';
  editingDraftFiles.value = [];
  editingDraftSkillIds.value = [];
};

const {
  canSwitchMessageVersion,
  currentLeafMessageId,
  displayedMessages,
  findMessageById,
  appendMessageAttachment,
  appendMessageContent,
  appendMessageToolStatus,
  buildRequestSnapshotForUserMessage: buildRequestSnapshotBase,
  createMessageNode,
  getMessageVersionCount,
  getMessageVersionIndex,
  prewarmVisibleConversationCache,
  switchMessageVersion,
  updateMessageContent,
  updateMessageTraceId,
  lastAssistantMessageId,
} = useMessageTree({
  messageNodes,
  rootChildIds,
  selectedRootChildId,
  selectedChildIdByParent,
  isLoading: () => isLoading.value,
});

const buildRequestSnapshotForUserMessage = (userMessageId: string) => {
  return buildRequestSnapshotBase(
    userMessageId,
    conversationId.value,
    selectedModel.value,
    selectedRerankerModel.value,
  );
};

const scrollToBottom = () => {
  nextTick(() => {
    if (messageContainerRef.value) {
      messageContainerRef.value.scrollTop =
        messageContainerRef.value.scrollHeight;
    }
  });
};

const createAssistantVariant = (userMessageId: string) => {
  return createMessageNode({
    role: 'assistant',
    content: '',
    timestamp: new Date(),
    parent_id: userMessageId,
  });
};

const {
  activeGeneration,
  executeAssistantGeneration,
  isLoading,
  isMessageThinking,
  onStopGeneration,
} = useChatStreaming({
  createAssistantVariant,
  appendMessageContent,
  appendMessageAttachment,
  appendMessageToolStatus,
  updateMessageTraceId,
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
  selectedModel,
  selectedRerankerModel,
  isChatLocked: () => isLoading.value,
  getDisplayedMessages: () => displayedMessages.value,
  resetEditingState: () => {
    inputText.value = '';
    selectedFiles.value = [];
    selectedSkillIds.value = [];
    resetEditingState();
  },
  afterSessionLoaded: async () => {
    inputText.value = '';
    selectedFiles.value = [];
    selectedSkillIds.value = [];
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

const {
  activeIncidentSession,
  activeIncidentSessionId,
  clearActiveIncidentSession,
  closeGenerationNotice,
  deleteIncident,
  downloadGeneratedIncidentAttachment,
  generateIncident,
  generationState,
  incidentGenerationProgress,
  incidentGenerationTraceId,
  incidentSchema,
  incidentSidebarSessions,
  isIncidentGenerating,
  loadIncidentSchema,
  loadIncidentSession,
  loadIncidentSessionSummaries,
  renameIncident,
  startIncidentSession,
  stopIncidentGeneration,
  updateIncidentAnswers,
} = useIncidentReportSessions();

const isSidebarLocked = computed(() => {
  return isLoading.value || isIncidentGenerating.value;
});

const sidebarSessions = computed(() => {
  return activeWorkspaceId.value === 'chat'
    ? sessionSummaries.value
    : incidentSidebarSessions.value;
});

const sidebarActiveSessionId = computed(() => {
  return activeWorkspaceId.value === 'chat'
    ? activeSessionId.value
    : activeIncidentSessionId.value;
});

const isMessageStreaming = (message: ChatMessageNode) => {
  return (
    isLoading.value &&
    message.role === 'assistant' &&
    message.id === activeGeneration.value?.assistant_id
  );
};

const activeStreamingAssistantMessage = computed(() => {
  const activeAssistantId = activeGeneration.value?.assistant_id;
  if (!activeAssistantId) {
    return null;
  }
  return findMessageById(activeAssistantId);
});

const liveToolStatuses = computed<ChatToolStatus[]>(() => {
  return activeStreamingAssistantMessage.value?.tool_statuses ?? [];
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

const openMessageTrace = async (messageId: string) => {
  const targetMessage = findMessageById(messageId);
  const traceId = targetMessage?.trace_id?.trim() ?? '';
  if (!traceId) {
    showCopyToast('这条回复还没有可查看的 trace_id。', {
      title: '暂无链路信息',
    });
    return;
  }
  await openTraceModalByTraceId(traceId);
};

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
  copyMessage,
  downloadAssistantMessage,
  downloadMessageFile,
} = useMessageActions({
  inputText,
  selectedFiles,
  selectedSkillIds,
  editingMessageId,
  editingDraftText,
  editingDraftFiles,
  editingDraftSkillIds,
  isLoading,
  activeSessionId,
  conversationId,
  rootChildIds,
  messageNodes,
  selectedRootChildId,
  selectedChildIdByParent,
  currentLeafMessageId,
  findMessageById,
  createMessageNode,
  buildRequestSnapshotForUserMessage,
  executeAssistantGeneration,
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

const onSelectWorkspace = async (workspaceId: string) => {
  if (workspaceId === 'chat') {
    activeWorkspaceId.value = 'chat';
    onClearChat();
    return;
  }

  activeWorkspaceId.value = 'incident-report';
  clearActiveIncidentSession();
};

const onSelectModel = (model: string) => {
  selectedModel.value = model;
  if (!availableModels.value.includes(selectedRerankerModel.value)) {
    selectedRerankerModel.value = model;
  }
  if (activeSessionId.value && rootChildIds.value.length > 0) {
    void persistCurrentSession();
  }
};

const onSelectRerankerModel = (model: string) => {
  selectedRerankerModel.value = model;
  if (activeSessionId.value && rootChildIds.value.length > 0) {
    void persistCurrentSession();
  }
};

const updateSelectedSkillIds = (skillIds: string[]) => {
  selectedSkillIds.value = [...skillIds];
};

const updateEditingSkillIds = (skillIds: string[]) => {
  editingDraftSkillIds.value = [...skillIds];
};

const onLoadSession = async (sessionId: string) => {
  if (activeWorkspaceId.value === 'chat') {
    await loadChatSession(sessionId);
    return;
  }
  await loadIncidentSession(sessionId);
};

const onRenameSession = async (payload: {
  sessionId: string;
  title: string;
}) => {
  if (activeWorkspaceId.value === 'chat') {
    await renameChatSession(payload.sessionId, payload.title);
    return;
  }
  await renameIncident(payload.sessionId, payload.title);
};

const onDeleteSession = async (sessionId: string) => {
  if (activeWorkspaceId.value === 'chat') {
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
    await generateIncident(selectedModel.value, selectedRerankerModel.value);
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

const { loadAvailableModels, loadAvailableSkills } = useCatalogLoader({
  availableModels,
  selectedModel,
  selectedRerankerModel,
  processingModes,
});

onMounted(() => {
  scrollToBottom();
  void loadSessionSummaries();
  void loadIncidentSchema();
  void loadIncidentSessionSummaries();
  void loadAvailableSkills();
  void loadAvailableModels();
  prewarmVisibleConversationCache(
    activeSessionId.value ?? conversationId.value,
  );
});
</script>

<style scoped src="../styles/components/chat-layout.css"></style>
