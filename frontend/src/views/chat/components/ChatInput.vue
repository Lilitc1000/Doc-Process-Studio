<template>
  <div class="chat-input">
    <div v-if="files.length > 0" class="files-preview">
      <div ref="filesContainerRef" class="files-list">
        <div v-for="(file, index) in files" :key="index" class="file-item">
          <span
            class="file-icon"
            :style="getFileIconStyle(file.name, file.type)"
            :title="getFileIconLabel(file.name, file.type)"
            aria-hidden="true"
          >
            <svg viewBox="0 0 20 20" class="file-icon-svg">
              <path
                d="M6 2.75H10.6L14.75 6.9V15a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 15V5A2.25 2.25 0 016 2.75z"
                fill="var(--file-icon-bg)"
                stroke="var(--file-icon-border)"
                stroke-linejoin="round"
                stroke-width="1.2"
              />
              <path
                d="M10.5 2.75V6.25H14"
                fill="none"
                stroke="var(--file-icon-border)"
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="1.2"
              />
            </svg>
            <span class="file-icon-badge">
              {{ getFileIconBadge(file.name, file.type) }}
            </span>
          </span>
          <div class="file-details">
            <span class="file-name">{{ file.name }}</span>
            <span class="file-size">{{ formatFileSize(file) }}</span>
          </div>
          <BaseButton
            type="button"
            class="remove-file-btn"
            variant="ghost"
            size="sm"
            title="移除文件"
            @click.stop="$emit('remove-file', index)"
          >
            ✕
          </BaseButton>
        </div>
      </div>
      <BaseButton
        type="button"
        class="remove-all-btn"
        variant="danger"
        size="sm"
        title="移除所有文件"
        @click="$emit('clear-all-files')"
      >
        ✕ 移除所有文件
      </BaseButton>
    </div>
    <div class="input-area">
      <div class="editor-area">
        <div v-if="selectedSkillOptions.length > 0" class="skill-chip-list">
          <BaseButton
            v-for="skill in selectedSkillOptions"
            :key="skill.id"
            type="button"
            class="skill-chip"
            variant="ghost"
            size="sm"
            :title="`移除文档处理方式：${skill.displayName}`"
            @click="removeSelectedSkill(skill.id)"
          >
            <span class="skill-chip-name">{{ skill.displayName }}</span>
            <span class="skill-chip-remove" aria-hidden="true">×</span>
          </BaseButton>
        </div>

        <div class="textarea-wrapper">
          <BaseTextarea
            :ref="setTextareaRef"
            :value="localText"
            class="chat-input-textarea"
            placeholder="输入消息... (支持 Markdown)"
            @input="onInput"
            @keydown="onKeydown"
            @click="onCaretChange"
            @keyup="onCaretChange"
            @focus="onCaretChange"
          ></BaseTextarea>

          <Transition name="skill-suggestion-fade">
            <div
              v-if="showSkillSuggestions"
              class="skill-suggestion-panel"
              role="listbox"
            >
              <BaseButton
                v-for="(skill, index) in filteredSkillSuggestions"
                :key="skill.id"
                type="button"
                class="skill-suggestion-item"
                variant="ghost"
                size="sm"
                :class="{ active: index === activeSuggestionIndex }"
                :title="skill.shortDescription || skill.displayName"
                @mousedown.prevent="selectSkillSuggestion(skill.id)"
                @mouseenter="activeSuggestionIndex = index"
              >
                <span class="skill-suggestion-main">
                  <span class="skill-suggestion-name">{{
                    skill.displayName
                  }}</span>
                </span>
                <span
                  v-if="skill.shortDescription"
                  class="skill-suggestion-desc"
                >
                  {{ skill.shortDescription }}
                </span>
              </BaseButton>
            </div>
          </Transition>
        </div>
      </div>

      <div class="input-actions">
        <BaseFileUpload
          class="file-input-label"
          title="上传文件"
          :accept="accept"
          multiple
          @select="onFileSelect"
        >
          <svg viewBox="0 0 16 16" class="action-icon-svg" aria-hidden="true">
            <path
              d="M10.75 5.25L6.63 9.37A2.12 2.12 0 103.63 6.37l4.59-4.59a3.25 3.25 0 114.59 4.59L7.16 12a4.25 4.25 0 11-6.01-6.01l4.95-4.95"
              fill="none"
              stroke="currentColor"
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="1.4"
            />
          </svg>
        </BaseFileUpload>

        <BaseButton
          type="button"
          class="send-btn"
          variant="primary"
          size="lg"
          :class="{
            disabled: !canSend && !props.isLoading,
            stopping: props.isLoading,
          }"
          :disabled="!canSend && !props.isLoading"
          :title="props.isLoading ? '停止生成' : '发送消息 (Enter)'"
          @click="props.isLoading ? onStop() : onSend()"
        >
          <svg
            v-if="props.isLoading"
            viewBox="0 0 16 16"
            class="send-icon-svg"
            aria-hidden="true"
          >
            <rect
              x="4.25"
              y="4.25"
              width="7.5"
              height="7.5"
              rx="1.4"
              fill="currentColor"
            />
          </svg>
          <svg
            v-else
            viewBox="0 0 16 16"
            class="send-icon-svg"
            aria-hidden="true"
          >
            <path
              d="M13.25 2.75L7.25 13.25L6.25 8.75L1.75 7.75L13.25 2.75z"
              fill="none"
              stroke="currentColor"
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="1.4"
            />
          </svg>
          <span class="send-text">{{ props.isLoading ? '停止' : '发送' }}</span>
        </BaseButton>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  computed,
  onMounted,
  ref,
  watch,
  type ComponentPublicInstance,
} from 'vue';
import { useSkillMentionSelector } from '../composables/useSkillMentionSelector';
import type { SkillOption } from '../../../types/common/skill';
import { formatFileSize, getFileTypeVisual } from '../../../utils/common/file';
import BaseButton from '../../../components/base/BaseButton.vue';
import BaseFileUpload from '../../../components/base/BaseFileUpload.vue';
import BaseTextarea from '../../../components/base/BaseTextarea.vue';

const props = defineProps<{
  text: string;
  files: File[];
  availableSkills?: SkillOption[];
  selectedSkillIds?: string[];
  accept?: string;
  isLoading?: boolean;
}>();

const emit = defineEmits<{
  (e: 'update:text', value: string): void;
  (e: 'update:selected-skill-ids', skillIds: string[]): void;
  (e: 'upload-files', files: File[]): void;
  (e: 'clear-all-files'): void;
  (e: 'remove-file', index: number): void;
  (e: 'send'): void;
  (e: 'stop'): void;
}>();

const localText = ref('');
const localSelectedSkillIds = ref<string[]>([]);
const textareaRef = ref<HTMLTextAreaElement | null>(null);
type BaseTextareaExpose = {
  getTextareaEl?: () => HTMLTextAreaElement | null;
};

const setTextareaRef = (instance: Element | ComponentPublicInstance | null) => {
  if (instance instanceof HTMLTextAreaElement) {
    textareaRef.value = instance;
    return;
  }

  const exposed = instance as BaseTextareaExpose | null;
  textareaRef.value = exposed?.getTextareaEl?.() ?? null;
};

const getFileIconStyle = (fileName: string, mimeType?: string) => {
  const visual = getFileTypeVisual(fileName, mimeType);
  return {
    '--file-icon-fg': visual.color,
    '--file-icon-bg': visual.background,
    '--file-icon-border': visual.border,
  };
};

const getFileIconBadge = (fileName: string, mimeType?: string) => {
  return getFileTypeVisual(fileName, mimeType).badge;
};

const getFileIconLabel = (fileName: string, mimeType?: string) => {
  return getFileTypeVisual(fileName, mimeType).label;
};

const resizeTextarea = () => {
  if (!textareaRef.value) {
    return;
  }

  textareaRef.value.style.height = 'auto';
  textareaRef.value.style.height = `${textareaRef.value.scrollHeight}px`;
};
const availableSkills = computed(() => props.availableSkills ?? []);
const {
  activeSuggestionIndex,
  filteredSkillSuggestions,
  selectedSkillOptions,
  showSkillSuggestions,
  handleSuggestionKeydown,
  onCaretChange,
  onTextInput,
  removeSelectedSkill,
  selectSkillSuggestion,
  tryRemoveLastSkillByBackspace,
} = useSkillMentionSelector({
  text: localText,
  selectedSkillIds: localSelectedSkillIds,
  availableSkills,
  textareaRef,
  updateText: (value) => {
    localText.value = value;
    emit('update:text', value);
    resizeTextarea();
  },
  updateSelectedSkillIds: (skillIds) => {
    localSelectedSkillIds.value = [...skillIds];
    emit('update:selected-skill-ids', [...skillIds]);
  },
});

const canSend = computed(() => {
  return (localText.value.trim() || props.files.length > 0) && !props.isLoading;
});

watch(
  () => props.text,
  (newVal) => {
    localText.value = newVal;
  },
  { immediate: true },
);

watch(
  () => props.selectedSkillIds,
  (newSkillIds) => {
    localSelectedSkillIds.value = [...(newSkillIds ?? [])];
  },
  { immediate: true },
);

const onInput = (event: Event) => {
  const target = event.target as HTMLTextAreaElement;
  localText.value = target.value;
  onTextInput(target);
  resizeTextarea();
  emit('update:text', localText.value);
};

const onSend = () => {
  if (canSend.value) {
    emit('send');
  }
};

const onStop = () => {
  emit('stop');
};

const onKeydown = (e: KeyboardEvent) => {
  if (handleSuggestionKeydown(e)) {
    return;
  }

  if (e.key === 'Backspace' && tryRemoveLastSkillByBackspace()) {
    e.preventDefault();
    return;
  }

  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    onSend();
  }
};

const onFileSelect = (files: File[]) => {
  if (files.length > 0) {
    emit('upload-files', files);
  }
};

watch(localText, () => {
  resizeTextarea();
});

onMounted(() => {
  resizeTextarea();
});
</script>

<style scoped src="../styles/chat-input.css"></style>
