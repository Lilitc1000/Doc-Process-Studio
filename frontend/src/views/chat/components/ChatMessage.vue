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
      <message-header :role="message.role" :timestamp="message.timestamp" />

      <div
        ref="messageContentRef"
        class="message-content"
        :class="{ thinking: isThinking }"
      >
        <div v-if="isEditing" class="message-edit-panel">
          <div
            v-if="editingSkillOptions.length > 0"
            class="message-edit-skill-list"
          >
            <base-button
              v-for="skill in editingSkillOptions"
              :key="skill.id"
              type="button"
              class="message-edit-skill-chip"
              variant="ghost"
              size="sm"
              :title="`移除文档处理方式：${skill.displayName}`"
              @click="removeEditingSkill(skill.id)"
            >
              <span class="message-edit-skill-chip-name">
                {{ skill.displayName }}
              </span>
              <span class="message-edit-skill-chip-remove" aria-hidden="true">
                ×
              </span>
            </base-button>
          </div>

          <message-files
            v-if="editingFiles.length > 0"
            :files="editingFiles"
            editable
            @remove="$emit('remove-edit-file', $event)"
          />

          <div class="message-edit-textarea-wrapper">
            <base-textarea
              :ref="setEditTextareaRef"
              class="message-edit-textarea"
              rows="1"
              :value="editingText"
              placeholder="编辑消息内容..."
              @input="onEditTextInputWithCaret"
              @keydown="onEditTextareaKeydown"
              @click="updateEditCaret"
              @keyup="updateEditCaret"
              @focus="updateEditCaret"
            ></base-textarea>

            <transition name="skill-suggestion-fade">
              <div
                v-if="showEditSkillSuggestions"
                class="message-edit-skill-suggestion-panel"
                role="listbox"
              >
                <base-button
                  v-for="(skill, index) in filteredEditSkillSuggestions"
                  :key="skill.id"
                  type="button"
                  class="message-edit-skill-suggestion-item"
                  variant="ghost"
                  size="sm"
                  :class="{ active: index === activeEditSkillIndex }"
                  :title="skill.shortDescription || skill.displayName"
                  @mousedown.prevent="selectEditSkillSuggestion(skill.id)"
                  @mouseenter="activeEditSkillIndex = index"
                >
                  <span class="message-edit-skill-suggestion-main">
                    <span class="message-edit-skill-suggestion-name">
                      {{ skill.displayName }}
                    </span>
                  </span>
                  <span
                    v-if="skill.shortDescription"
                    class="message-edit-skill-suggestion-desc"
                  >
                    {{ skill.shortDescription }}
                  </span>
                </base-button>
              </div>
            </transition>
          </div>
        </div>

        <template v-else>
          <message-live-tool-status
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

          <message-tool-timeline
            v-if="showHistoricalToolStatuses"
            :tool-statuses="toolStatuses"
            :is-streaming="Boolean(isStreaming)"
          />

          <template v-if="message.role === 'assistant'">
            <div
              v-if="normalizedDisplayContent.trim().length > 0"
              v-safe-html="renderedContent"
              class="message-text"
            ></div>

            <message-files
              v-if="message.files && message.files.length > 0"
              :files="message.files"
              @download="onMessageFileDownload"
            />
          </template>

          <template v-else>
            <div v-if="displaySkillTags.length > 0" class="message-skill-list">
              <span
                v-for="skill in displaySkillTags"
                :key="skill.id"
                class="message-skill-chip"
                :title="`文档处理方式：${skill.displayName}`"
              >
                {{ skill.displayName }}
              </span>
            </div>

            <message-files
              v-if="message.files && message.files.length > 0"
              :files="message.files"
              @download="onMessageFileDownload"
            />

            <div
              v-if="normalizedDisplayContent.trim().length > 0"
              v-safe-html="renderedContent"
              class="message-text"
            ></div>
          </template>
        </template>
      </div>

      <message-toolbar
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
        :can-open-trace="canOpenTrace"
        :can-confirm-edit="canConfirmEdit"
        @prev-version="$emit('prev-version')"
        @next-version="$emit('next-version')"
        @start-edit="$emit('start-edit')"
        @upload-edit-files="$emit('upload-edit-files', $event)"
        @cancel-edit="$emit('cancel-edit')"
        @confirm-edit="$emit('confirm-edit')"
        @regenerate="$emit('regenerate')"
        @copy="$emit('copy')"
        @open-trace="$emit('open-trace')"
        @download="$emit('download')"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, toRef, type ComponentPublicInstance } from 'vue';
import { useMessageEdit } from '../composables/useMessageEdit';
import { useMessageRender } from '../composables/useMessageRender';
import { useSkillMentionSelector } from '../composables/useSkillMentionSelector';
import type {
  ChatAttachment,
  ChatEditAttachment,
  ChatMessageDisplay,
  ChatToolStatus,
} from '../../../types/chat/chat';
import type { SkillOption } from '../../../types/common/skill';
import BaseButton from '../../../components/base/BaseButton.vue';
import BaseTextarea from '../../../components/base/BaseTextarea.vue';
import MessageFiles from './message/MessageFiles.vue';
import MessageHeader from './message/MessageHeader.vue';
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
  canOpenTrace?: boolean;
  isVersionLocked?: boolean;
  isEditing?: boolean;
  editingText?: string;
  editingFiles?: ChatEditAttachment[];
  editingSkillIds?: string[];
  availableSkills?: SkillOption[];
  kbProjects?: Array<{ id: string; name: string }>;
  canConfirmEdit?: boolean;
  showToolbarByDefault?: boolean;
}>();

const emit = defineEmits<{
  (e: 'prev-version'): void;
  (e: 'next-version'): void;
  (e: 'start-edit'): void;
  (e: 'update-edit-text', value: string): void;
  (e: 'update-edit-skill-ids', skillIds: string[]): void;
  (e: 'upload-edit-files', files: File[]): void;
  (e: 'remove-edit-file', index: number): void;
  (e: 'cancel-edit'): void;
  (e: 'confirm-edit'): void;
  (e: 'regenerate'): void;
  (e: 'copy'): void;
  (e: 'open-trace'): void;
  (e: 'download'): void;
  (e: 'download-file', file: ChatAttachment): void;
}>();

const isEditing = computed(() => props.isEditing ?? false);
const editingText = computed(() => props.editingText ?? '');
const editingFiles = computed(() => props.editingFiles ?? []);
const editingSkillIds = computed(() => props.editingSkillIds ?? []);
const availableSkills = computed(() => props.availableSkills ?? []);
const kbProjects = computed(() => props.kbProjects ?? []);
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
const canOpenTrace = computed(() => props.canOpenTrace ?? false);
const isVersionLocked = computed(() => props.isVersionLocked ?? false);
const canConfirmEdit = computed(() => props.canConfirmEdit ?? false);
const toolStatuses = computed<ChatToolStatus[]>(() => {
  return props.message.toolStatuses ?? [];
});
const showInlineLiveToolStatus = computed(() => {
  return props.message.role === 'assistant' && Boolean(props.liveToolStatus);
});
const showHistoricalToolStatuses = computed(() => {
  return props.message.role === 'assistant' && toolStatuses.value.length > 0;
});
const displaySkillTags = computed(() => {
  if (props.message.role !== 'user') {
    return [];
  }

  const requestSkillIds = props.message.requestSkillIds ?? [];
  if (requestSkillIds.length === 0) {
    return [];
  }

  return requestSkillIds.map((skillId) => {
    const matchedSkill = availableSkills.value.find((skill) => {
      return skill.id === skillId;
    });

    return {
      id: skillId,
      displayName: matchedSkill?.displayName ?? skillId,
    };
  });
});
const liveToolStatus = computed(() => props.liveToolStatus ?? null);

const { editTextareaRef, onEditTextInput } = useMessageEdit({
  isEditing,
  editingText,
  onTextChange: (value) => {
    emit('update-edit-text', value);
  },
});
type BaseTextareaExpose = {
  getTextareaEl?: () => HTMLTextAreaElement | null;
};

const setEditTextareaRef = (
  instance: Element | ComponentPublicInstance | null,
) => {
  if (instance instanceof HTMLTextAreaElement) {
    editTextareaRef.value = instance;
    return;
  }

  const exposed = instance as BaseTextareaExpose | null;
  editTextareaRef.value = exposed?.getTextareaEl?.() ?? null;
};

const {
  activeSuggestionIndex: activeEditSkillIndex,
  filteredSkillSuggestions: filteredEditSkillSuggestions,
  selectedSkillOptions: editingSkillOptions,
  showSkillSuggestions: showEditSkillSuggestions,
  handleSuggestionKeydown,
  onCaretChange: updateEditCaret,
  onTextInput,
  removeSelectedSkill: removeEditingSkill,
  selectSkillSuggestion: selectEditSkillSuggestion,
  tryRemoveLastSkillByBackspace,
} = useSkillMentionSelector({
  text: editingText,
  selectedSkillIds: editingSkillIds,
  availableSkills,
  kbProjects,
  textareaRef: editTextareaRef,
  updateText: (value) => {
    emit('update-edit-text', value);
  },
  updateSelectedSkillIds: (skillIds) => {
    emit('update-edit-skill-ids', [...skillIds]);
  },
});

const onEditTextInputWithCaret = (event: Event) => {
  onEditTextInput(event);
  onTextInput(event.target as HTMLTextAreaElement);
};

const onEditTextareaKeydown = (event: KeyboardEvent) => {
  if (handleSuggestionKeydown(event)) {
    return;
  }
  if (event.key === 'Backspace' && tryRemoveLastSkillByBackspace()) {
    event.preventDefault();
  }
};

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

<style src="../styles/chat-message.css"></style>
