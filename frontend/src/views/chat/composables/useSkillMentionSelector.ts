import { computed, nextTick, ref, watch, type Ref } from 'vue';
import type { SkillOption } from '../../../types/common/skill';

interface UseSkillMentionSelectorOptions {
  text: Readonly<Ref<string>>;
  selectedSkillIds: Readonly<Ref<string[]>>;
  availableSkills: Readonly<Ref<SkillOption[]>>;
  textareaRef: Readonly<Ref<HTMLTextAreaElement | null>>;
  updateText: (value: string) => void;
  updateSelectedSkillIds: (skillIds: string[]) => void;
}

const SKILL_TRIGGER_PATTERN = /(?:^|\s)\$([A-Za-z0-9._-]*)$/;

export const useSkillMentionSelector = (
  options: UseSkillMentionSelectorOptions,
) => {
  const caretPosition = ref(0);
  const activeSuggestionIndex = ref(0);

  const selectedSkillOptions = computed(() => {
    return options.selectedSkillIds.value
      .map((skillId) => {
        return (
          options.availableSkills.value.find((skill) => skill.id === skillId) ??
          null
        );
      })
      .filter((skill): skill is SkillOption => skill !== null);
  });

  const resolveTriggerState = () => {
    const textarea = options.textareaRef.value;
    if (!textarea) {
      return null;
    }

    const cursorPosition = textarea.selectionStart ?? caretPosition.value;
    const prefixText = options.text.value.slice(0, cursorPosition);
    const triggerMatch = SKILL_TRIGGER_PATTERN.exec(prefixText);
    if (!triggerMatch) {
      return null;
    }

    const fullMatch = triggerMatch[0];
    const matchStart =
      triggerMatch.index ?? prefixText.length - fullMatch.length;
    const dollarOffset = fullMatch.lastIndexOf('$');
    if (dollarOffset < 0) {
      return null;
    }

    return {
      query: triggerMatch[1] ?? '',
      start: matchStart + dollarOffset,
      end: cursorPosition,
    };
  };

  const filteredSkillSuggestions = computed(() => {
    const triggerState = resolveTriggerState();
    if (!triggerState) {
      return [];
    }

    const selectedSet = new Set(options.selectedSkillIds.value);
    const normalizedQuery = triggerState.query.trim().toLowerCase();
    return options.availableSkills.value.filter((skill) => {
      if (selectedSet.has(skill.id)) {
        return false;
      }
      if (!normalizedQuery) {
        return true;
      }
      return (
        skill.id.toLowerCase().includes(normalizedQuery) ||
        skill.displayName.toLowerCase().includes(normalizedQuery)
      );
    });
  });

  const showSkillSuggestions = computed(() => {
    return filteredSkillSuggestions.value.length > 0;
  });

  const normalizeSkillIds = (skillIds: string[]) => {
    return Array.from(
      new Set(
        skillIds
          .map((skillId) => skillId.trim())
          .filter((skillId) => skillId.length > 0),
      ),
    );
  };

  const emitSkillIds = (skillIds: string[]) => {
    options.updateSelectedSkillIds(normalizeSkillIds(skillIds));
  };

  const onCaretChange = () => {
    if (!options.textareaRef.value) {
      return;
    }
    caretPosition.value =
      options.textareaRef.value.selectionStart ?? caretPosition.value;
  };

  const onTextInput = (textarea: HTMLTextAreaElement | null) => {
    if (!textarea) {
      return;
    }
    caretPosition.value = textarea.selectionStart ?? textarea.value.length;
  };

  const removeSelectedSkill = (skillId: string) => {
    emitSkillIds(
      options.selectedSkillIds.value.filter((currentSkillId) => {
        return currentSkillId !== skillId;
      }),
    );
  };

  const selectSkillSuggestion = (skillId: string) => {
    if (options.selectedSkillIds.value.includes(skillId)) {
      return;
    }

    const triggerState = resolveTriggerState();
    if (!triggerState) {
      emitSkillIds([...options.selectedSkillIds.value, skillId]);
      return;
    }

    const nextText =
      options.text.value.slice(0, triggerState.start) +
      options.text.value.slice(triggerState.end);
    options.updateText(nextText);
    emitSkillIds([...options.selectedSkillIds.value, skillId]);
    activeSuggestionIndex.value = 0;

    void nextTick(() => {
      if (!options.textareaRef.value) {
        return;
      }
      const nextCursor = Math.min(triggerState.start, nextText.length);
      options.textareaRef.value.focus();
      options.textareaRef.value.setSelectionRange(nextCursor, nextCursor);
      caretPosition.value = nextCursor;
    });
  };

  const tryRemoveLastSkillByBackspace = () => {
    if (options.selectedSkillIds.value.length === 0) {
      return false;
    }

    const textarea = options.textareaRef.value;
    if (!textarea) {
      return false;
    }

    const selectionStart = textarea.selectionStart ?? 0;
    const selectionEnd = textarea.selectionEnd ?? 0;
    if (selectionStart !== selectionEnd) {
      return false;
    }

    if (options.text.value.trim().length > 0) {
      return false;
    }

    const nextSkillIds = [...options.selectedSkillIds.value];
    nextSkillIds.pop();
    emitSkillIds(nextSkillIds);
    return true;
  };

  const handleSuggestionKeydown = (event: KeyboardEvent) => {
    if (!showSkillSuggestions.value) {
      return false;
    }

    if (event.key === 'ArrowDown') {
      event.preventDefault();
      activeSuggestionIndex.value =
        (activeSuggestionIndex.value + 1) %
        filteredSkillSuggestions.value.length;
      return true;
    }

    if (event.key === 'ArrowUp') {
      event.preventDefault();
      activeSuggestionIndex.value =
        (activeSuggestionIndex.value -
          1 +
          filteredSkillSuggestions.value.length) %
        filteredSkillSuggestions.value.length;
      return true;
    }

    if (event.key === 'Enter' || event.key === 'Tab') {
      event.preventDefault();
      const activeSkill =
        filteredSkillSuggestions.value[activeSuggestionIndex.value] ??
        filteredSkillSuggestions.value[0];
      if (activeSkill) {
        selectSkillSuggestion(activeSkill.id);
      }
      return true;
    }

    if (event.key === 'Escape') {
      event.preventDefault();
      activeSuggestionIndex.value = 0;
      return true;
    }

    return false;
  };

  watch(filteredSkillSuggestions, (nextSuggestions) => {
    if (nextSuggestions.length === 0) {
      activeSuggestionIndex.value = 0;
      return;
    }
    if (activeSuggestionIndex.value > nextSuggestions.length - 1) {
      activeSuggestionIndex.value = nextSuggestions.length - 1;
    }
  });

  return {
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
  };
};
