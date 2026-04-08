<template>
  <div class="message-interaction-card" aria-live="polite">
    <div class="message-interaction-header">
      <span class="message-interaction-step">
        第 {{ interaction.currentStep }}/{{ interaction.totalSteps }} 步
      </span>
      <h4 class="message-interaction-title">
        {{ interaction.title }}
      </h4>
    </div>
    <p class="message-interaction-prompt">
      {{ interaction.prompt }}
    </p>

    <div
      v-if="interaction.kind === 'single_select'"
      class="message-interaction-options"
    >
      <button
        v-for="option in interaction.options"
        :key="option.value"
        class="message-interaction-option"
        :class="{ 'is-selected': interactionSingleValue === option.value }"
        type="button"
        :disabled="!canSubmitInteraction || interactionSubmitting"
        @click="onSelectSingleOption(option.value)"
      >
        <span class="message-interaction-option-label">
          {{ option.label }}
        </span>
        <span
          v-if="option.description"
          class="message-interaction-option-description"
        >
          {{ option.description }}
        </span>
      </button>
    </div>

    <div
      v-else-if="interaction.kind === 'multi_select'"
      class="message-interaction-options"
    >
      <button
        v-for="option in interaction.options"
        :key="option.value"
        class="message-interaction-option"
        :class="{ 'is-selected': interactionMultiValue.includes(option.value) }"
        type="button"
        :disabled="!canSubmitInteraction || interactionSubmitting"
        @click="onToggleMultiOption(option.value)"
      >
        <span class="message-interaction-option-label">
          {{ option.label }}
        </span>
        <span
          v-if="option.description"
          class="message-interaction-option-description"
        >
          {{ option.description }}
        </span>
      </button>
    </div>

    <textarea
      v-else
      v-model.trim="interactionTextValue"
      class="message-interaction-textarea"
      rows="2"
      :placeholder="interaction.placeholder || '请输入内容...'"
      :disabled="!canSubmitInteraction || interactionSubmitting"
    ></textarea>

    <input
      v-if="interaction.allowCustom"
      v-model.trim="interactionCustomValue"
      class="message-interaction-custom-input"
      type="text"
      :placeholder="interaction.placeholder || '输入自定义内容...'"
      :disabled="!canSubmitInteraction || interactionSubmitting"
    />

    <div class="message-interaction-actions">
      <button
        class="message-interaction-submit"
        type="button"
        :disabled="
          !canSubmitInteraction ||
          interactionSubmitting ||
          !canSubmitCurrentInteraction
        "
        @click="submitInteractionAnswer"
      >
        {{ interactionSubmitting ? '提交中...' : '确认并继续' }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { toRef } from 'vue';
import { useMessageInteraction } from '../../composables/message/useMessageInteraction';
import type {
  ChatInteractionAnswer,
  ChatInteractionCard,
} from '../../types/chat';

const props = defineProps<{
  interaction: ChatInteractionCard;
  canSubmitInteraction: boolean;
}>();

const emit = defineEmits<{
  (e: 'submit', answer: ChatInteractionAnswer): void;
}>();

const {
  interactionCustomValue,
  interactionMultiValue,
  interactionSingleValue,
  interactionSubmitting,
  interactionTextValue,
  canSubmitCurrentInteraction,
  onSelectSingleOption,
  onToggleMultiOption,
  submitInteractionAnswer,
} = useMessageInteraction({
  interaction: toRef(props, 'interaction'),
  canSubmitInteraction: toRef(props, 'canSubmitInteraction'),
  onSubmit: (answer) => {
    emit('submit', answer);
  },
});
</script>
