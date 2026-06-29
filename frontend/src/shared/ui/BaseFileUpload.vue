<template>
  <span
    class="base-file-upload"
    :class="{ disabled }"
    role="button"
    :tabindex="disabled ? -1 : 0"
    v-bind="$attrs"
    @click="triggerSelect"
    @keydown.enter.prevent="triggerSelect"
    @keydown.space.prevent="triggerSelect"
  >
    <slot />
    <input
      ref="fileInputRef"
      class="base-file-upload-input"
      type="file"
      :accept="accept"
      :multiple="multiple"
      :disabled="disabled"
      @click.stop
      @change="onChange"
    />
  </span>
</template>

<script setup lang="ts">
import { ref } from 'vue';

defineOptions({
  inheritAttrs: false,
});

const props = withDefaults(
  defineProps<{
    accept?: string;
    multiple?: boolean;
    disabled?: boolean;
    autoReset?: boolean;
  }>(),
  {
    accept: '',
    multiple: false,
    disabled: false,
    autoReset: true,
  },
);

const emit = defineEmits<{
  (e: 'select', files: File[]): void;
}>();

const fileInputRef = ref<HTMLInputElement | null>(null);

const triggerSelect = () => {
  if (props.disabled) {
    return;
  }
  fileInputRef.value?.click();
};

const onChange = (event: Event) => {
  const input = event.target as HTMLInputElement;
  const files = input.files ? Array.from(input.files) : [];
  if (files.length > 0) {
    emit('select', files);
  }
  if (props.autoReset) {
    input.value = '';
  }
};

const clear = () => {
  if (fileInputRef.value) {
    fileInputRef.value.value = '';
  }
};

defineExpose({
  open: triggerSelect,
  clear,
});
</script>

<style scoped>
.base-file-upload {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.base-file-upload:focus-visible {
  outline: none;
}

.base-file-upload.disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.base-file-upload-input {
  display: none;
}
</style>
