<template>
  <div
    class="chat-message"
    :class="[
      `role-${message.role}`,
      {
        'is-editing': isEditing,
        'toolbar-visible': showToolbarByDefault,
      },
    ]"
  >
    <div class="message-track">
      <MessageHeader :role="message.role" :timestamp="message.timestamp" />

      <div
        ref="messageContentRef"
        class="message-content"
        :class="{ thinking: isThinking }"
      >
        <div v-if="isEditing" class="message-edit-panel">
          <MessageFiles
            v-if="editingFiles.length > 0"
            :files="editingFiles"
            editable
            @remove="$emit('remove-edit-file', $event)"
          />
          <textarea
            ref="editTextareaRef"
            class="message-edit-textarea"
            rows="1"
            :value="editingText"
            placeholder="编辑消息内容..."
            @input="onEditTextInput"
          ></textarea>
        </div>

        <template v-else>
          <MessageLiveToolStatus
            v-if="showInlineLiveToolStatus && liveToolStatus"
            :status="liveToolStatus"
          />

          <div
            v-if="
              isThinking &&
              !normalizedDisplayContent.trim().length &&
              !(message.files && message.files.length > 0)
            "
            class="thinking-state"
          >
            <span class="thinking-spinner"></span>
            <span>思考中...</span>
          </div>

          <MessageToolTimeline
            v-if="showHistoricalToolStatuses"
            :tool-statuses="toolStatuses"
            :is-streaming="Boolean(isStreaming)"
          />

          <template v-if="message.role === 'assistant'">
            <MessageInteractionCard
              v-if="activeInteraction"
              :interaction="activeInteraction"
              :can-submit-interaction="canSubmitInteraction"
              @submit="$emit('submit-interaction', $event)"
            />

            <!-- eslint-disable vue/no-v-html -->
            <div
              v-if="normalizedDisplayContent.trim().length > 0"
              class="message-text"
              v-html="renderedContent"
            ></div>
            <!-- eslint-enable vue/no-v-html -->

            <MessageFiles
              v-if="message.files && message.files.length > 0"
              :files="message.files"
              @download="onMessageFileDownload"
            />
          </template>

          <template v-else>
            <MessageFiles
              v-if="message.files && message.files.length > 0"
              :files="message.files"
              @download="onMessageFileDownload"
            />

            <!-- eslint-disable vue/no-v-html -->
            <div
              v-if="normalizedDisplayContent.trim().length > 0"
              class="message-text"
              v-html="renderedContent"
            ></div>
            <!-- eslint-enable vue/no-v-html -->
          </template>
        </template>
      </div>

      <MessageToolbar
        v-if="message.role !== 'system'"
        :role="message.role"
        :is-editing="isEditing"
        :show-version-switcher="showVersionSwitcher"
        :version-index="versionIndex"
        :version-count="versionCount"
        :can-go-prev="canGoPrev"
        :can-go-next="canGoNext"
        :is-version-locked="isVersionLocked"
        :can-edit="canEdit"
        :can-regenerate="canRegenerate"
        :can-copy="canCopy"
        :can-download="canDownload"
        :can-confirm-edit="canConfirmEdit"
        @prev-version="$emit('prev-version')"
        @next-version="$emit('next-version')"
        @start-edit="$emit('start-edit')"
        @upload-edit-files="$emit('upload-edit-files', $event)"
        @cancel-edit="$emit('cancel-edit')"
        @confirm-edit="$emit('confirm-edit')"
        @regenerate="$emit('regenerate')"
        @copy="$emit('copy')"
        @download="$emit('download')"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, toRef } from 'vue';
import { useMessageEdit } from '../composables/message/useMessageEdit';
import { useMessageRender } from '../composables/message/useMessageRender';
import type {
  ChatAttachment,
  ChatEditAttachment,
  ChatInteractionAnswer,
  ChatInteractionCard,
  ChatMessageDisplay,
  ChatToolStatus,
} from '../types/chat';
import MessageFiles from './message/MessageFiles.vue';
import MessageHeader from './message/MessageHeader.vue';
import MessageInteractionCard from './message/MessageInteractionCard.vue';
import MessageLiveToolStatus from './message/MessageLiveToolStatus.vue';
import MessageToolTimeline from './message/MessageToolTimeline.vue';
import MessageToolbar from './message/MessageToolbar.vue';

const props = defineProps<{
  message: ChatMessageDisplay;
  cacheScopeId: string;
  isThinking?: boolean;
  isStreaming?: boolean;
  liveToolStatus?: ChatToolStatus | null;
  showVersionSwitcher?: boolean;
  versionIndex?: number;
  versionCount?: number;
  canGoPrev?: boolean;
  canGoNext?: boolean;
  canEdit?: boolean;
  canRegenerate?: boolean;
  canCopy?: boolean;
  canDownload?: boolean;
  isVersionLocked?: boolean;
  isEditing?: boolean;
  editingText?: string;
  editingFiles?: ChatEditAttachment[];
  canConfirmEdit?: boolean;
  showToolbarByDefault?: boolean;
  canSubmitInteraction?: boolean;
}>();

const emit = defineEmits<{
  (e: 'prev-version'): void;
  (e: 'next-version'): void;
  (e: 'start-edit'): void;
  (e: 'update-edit-text', value: string): void;
  (e: 'upload-edit-files', files: File[]): void;
  (e: 'remove-edit-file', index: number): void;
  (e: 'cancel-edit'): void;
  (e: 'confirm-edit'): void;
  (e: 'regenerate'): void;
  (e: 'copy'): void;
  (e: 'download'): void;
  (e: 'download-file', file: ChatAttachment): void;
  (e: 'submit-interaction', answer: ChatInteractionAnswer): void;
}>();

const isEditing = computed(() => props.isEditing ?? false);
const editingText = computed(() => props.editingText ?? '');
const editingFiles = computed(() => props.editingFiles ?? []);
const showToolbarByDefault = computed(
  () => props.showToolbarByDefault ?? false,
);
const showVersionSwitcher = computed(() => props.showVersionSwitcher ?? false);
const versionIndex = computed(() => props.versionIndex ?? 1);
const versionCount = computed(() => props.versionCount ?? 1);
const canGoPrev = computed(() => props.canGoPrev ?? false);
const canGoNext = computed(() => props.canGoNext ?? false);
const canEdit = computed(() => props.canEdit ?? false);
const canRegenerate = computed(() => props.canRegenerate ?? false);
const canCopy = computed(() => props.canCopy ?? false);
const canDownload = computed(() => props.canDownload ?? false);
const isVersionLocked = computed(() => props.isVersionLocked ?? false);
const canConfirmEdit = computed(() => props.canConfirmEdit ?? false);
const canSubmitInteraction = computed(
  () => props.canSubmitInteraction ?? false,
);
const toolStatuses = computed<ChatToolStatus[]>(() => {
  return props.message.toolStatuses ?? [];
});
const showInlineLiveToolStatus = computed(() => {
  return props.message.role === 'assistant' && Boolean(props.liveToolStatus);
});
const showHistoricalToolStatuses = computed(() => {
  return props.message.role === 'assistant' && toolStatuses.value.length > 0;
});
const activeInteraction = computed<ChatInteractionCard | null>(() => {
  if (props.message.role !== 'assistant') {
    return null;
  }
  return props.message.interaction ?? null;
});
const liveToolStatus = computed(() => props.liveToolStatus ?? null);

const { editTextareaRef, onEditTextInput } = useMessageEdit({
  isEditing,
  editingText,
  onTextChange: (value) => {
    emit('update-edit-text', value);
  },
});

const { messageContentRef, normalizedDisplayContent, renderedContent } =
  useMessageRender({
    message: toRef(props, 'message'),
    cacheScopeId: toRef(props, 'cacheScopeId'),
    isEditing,
    showToolbarByDefault,
  });

const onMessageFileDownload = (file: ChatAttachment) => {
  emit('download-file', file);
};
</script>

<style src="../styles/components/chat-message.css"></style>
