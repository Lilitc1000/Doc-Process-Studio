import { nextTick, ref, watch, type Ref } from 'vue';

interface UseMessageEditOptions {
  isEditing: Ref<boolean>;
  editingText: Ref<string>;
  onTextChange: (value: string) => void;
}

export const useMessageEdit = (options: UseMessageEditOptions) => {
  const editTextareaRef = ref<HTMLTextAreaElement | null>(null);

  const resizeEditTextarea = () => {
    if (!editTextareaRef.value) {
      return;
    }
    editTextareaRef.value.style.height = 'auto';
    editTextareaRef.value.style.height = `${editTextareaRef.value.scrollHeight}px`;
  };

  const onEditTextInput = (event: Event) => {
    const textarea = event.target as HTMLTextAreaElement;
    textarea.style.height = 'auto';
    textarea.style.height = `${textarea.scrollHeight}px`;
    options.onTextChange(textarea.value);
  };

  watch(
    [options.isEditing, options.editingText],
    async () => {
      if (!options.isEditing.value) {
        return;
      }
      await nextTick();
      resizeEditTextarea();
    },
    { immediate: true },
  );

  return {
    editTextareaRef,
    onEditTextInput,
  };
};
