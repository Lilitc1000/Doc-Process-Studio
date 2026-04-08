import { computed, ref, watch, type Ref } from 'vue';
import type {
  ChatInteractionAnswer,
  ChatInteractionCard,
} from '../../types/chat';

interface UseMessageInteractionOptions {
  interaction: Ref<ChatInteractionCard>;
  canSubmitInteraction: Ref<boolean>;
  onSubmit: (answer: ChatInteractionAnswer) => void;
}

export const useMessageInteraction = (
  options: UseMessageInteractionOptions,
) => {
  const interactionSingleValue = ref('');
  const interactionMultiValue = ref<string[]>([]);
  const interactionTextValue = ref('');
  const interactionCustomValue = ref('');
  const interactionSubmitting = ref(false);

  const resetInteractionDraft = () => {
    interactionSingleValue.value = '';
    interactionMultiValue.value = [];
    interactionTextValue.value = '';
    interactionCustomValue.value = '';
    interactionSubmitting.value = false;
  };

  const canSubmitCurrentInteraction = computed(() => {
    const interaction = options.interaction.value;
    const customValue = interactionCustomValue.value.trim();

    if (interaction.kind === 'text') {
      if (!interaction.required) {
        return true;
      }
      return interactionTextValue.value.trim().length > 0;
    }

    if (interaction.kind === 'single_select') {
      if (!interaction.required) {
        return true;
      }
      return (
        interactionSingleValue.value.trim().length > 0 || customValue.length > 0
      );
    }

    if (!interaction.required) {
      return true;
    }
    return interactionMultiValue.value.length > 0 || customValue.length > 0;
  });

  const onSelectSingleOption = (value: string) => {
    interactionSingleValue.value = value;
  };

  const onToggleMultiOption = (value: string) => {
    const existed = interactionMultiValue.value.includes(value);
    interactionMultiValue.value = existed
      ? interactionMultiValue.value.filter((item) => item !== value)
      : [...interactionMultiValue.value, value];
  };

  const submitInteractionAnswer = () => {
    const interaction = options.interaction.value;
    if (
      !options.canSubmitInteraction.value ||
      interactionSubmitting.value ||
      !canSubmitCurrentInteraction.value
    ) {
      return;
    }

    const answer: ChatInteractionAnswer = {
      sessionId: interaction.sessionId,
      stepId: interaction.stepId,
    };

    if (interaction.kind === 'text') {
      answer.value = interactionTextValue.value.trim();
    } else if (interaction.kind === 'single_select') {
      if (interactionSingleValue.value.trim()) {
        answer.value = interactionSingleValue.value.trim();
      }
    } else {
      answer.value = [...interactionMultiValue.value];
    }

    if (
      interaction.allowCustom &&
      interactionCustomValue.value.trim().length > 0
    ) {
      answer.customValue = interactionCustomValue.value.trim();
    }

    interactionSubmitting.value = true;
    options.onSubmit(answer);
  };

  watch(
    () => options.interaction.value.stepId,
    () => {
      resetInteractionDraft();
    },
    { immediate: true },
  );

  watch(
    () => options.canSubmitInteraction.value,
    (enabled) => {
      if (enabled) {
        interactionSubmitting.value = false;
      }
    },
  );

  return {
    interactionCustomValue,
    interactionMultiValue,
    interactionSingleValue,
    interactionSubmitting,
    interactionTextValue,
    canSubmitCurrentInteraction,
    onSelectSingleOption,
    onToggleMultiOption,
    submitInteractionAnswer,
  };
};
