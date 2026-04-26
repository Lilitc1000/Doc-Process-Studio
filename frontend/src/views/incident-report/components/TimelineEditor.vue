<template>
  <div class="timeline-editor">
    <div class="timeline-items">
      <div v-for="(item, index) in items" :key="index" class="timeline-item">
        <div class="timeline-item-header">
          <span class="timeline-item-index">#{{ index + 1 }}</span>
          <button
            type="button"
            class="timeline-item-remove"
            @click="removeItem(index)"
          >
            ✕
          </button>
        </div>
        <div class="timeline-item-fields">
          <div class="timeline-field">
            <label class="timeline-field-label">时间</label>
            <base-date-time-picker
              :model-value="item.time"
              mode="datetime"
              @update:model-value="updateItem(index, 'time', $event)"
            />
          </div>
          <div class="timeline-field">
            <label class="timeline-field-label">事件</label>
            <base-input
              :model-value="item.event"
              placeholder="描述发生的事件"
              @update:model-value="updateItem(index, 'event', $event)"
            />
          </div>
        </div>
      </div>
    </div>
    <base-button variant="ghost" size="sm" @click="addItem">
      + 添加时间线条目
    </base-button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import BaseButton from '../../../components/base/BaseButton.vue';
import BaseInput from '../../../components/base/BaseInput.vue';
import BaseDateTimePicker from '../../../components/base/BaseDateTimePicker.vue';

interface TimelineItem {
  time: string;
  event: string;
}

const props = withDefaults(
  defineProps<{
    modelValue?: unknown;
  }>(),
  {
    modelValue: () => [],
  },
);

const emit = defineEmits<{
  (e: 'update:modelValue', value: unknown): void;
}>();

const items = computed<TimelineItem[]>(() => {
  if (Array.isArray(props.modelValue)) {
    return props.modelValue.map((item: unknown) => {
      if (typeof item === 'object' && item !== null) {
        const obj = item as Record<string, unknown>;
        return { time: String(obj.time ?? ''), event: String(obj.event ?? '') };
      }
      return { time: '', event: String(item) };
    });
  }
  return [];
});

const addItem = () => {
  const newItems = [...items.value, { time: '', event: '' }];
  emit('update:modelValue', newItems);
};

const removeItem = (index: number) => {
  const newItems = items.value.filter((_, i) => i !== index);
  emit('update:modelValue', newItems);
};

const updateItem = (index: number, field: 'time' | 'event', value: string) => {
  const newItems = items.value.map((item, i) =>
    i === index ? { ...item, [field]: value } : item,
  );
  emit('update:modelValue', newItems);
};
</script>

<style scoped>
.timeline-editor {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.timeline-items {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.timeline-item {
  padding: 10px;
  background: var(--color-bg-secondary);
  border-radius: 6px;
  border-left: 3px solid var(--color-primary);
}

.timeline-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.timeline-item-index {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-primary);
}

.timeline-item-remove {
  border: none;
  background: transparent;
  cursor: pointer;
  color: var(--color-text-tertiary);
  font-size: 14px;
  padding: 2px 4px;
  border-radius: 4px;
}

.timeline-item-remove:hover {
  background: var(--color-danger-bg, #fef2f2);
  color: var(--color-danger);
}

.timeline-item-fields {
  display: flex;
  gap: 8px;
  align-items: flex-end;
}

.timeline-field {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.timeline-field-label {
  font-size: 12px;
  color: var(--color-text-secondary);
}
</style>
