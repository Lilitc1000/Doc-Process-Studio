<template>
  <div class="schema-form-renderer">
    <div v-for="step in schema.steps" :key="step.step_id" class="form-step">
      <h3 class="step-title">{{ step.title }}</h3>
      <p v-if="step.description" class="step-description">{{ step.description }}</p>

      <div class="step-fields">
        <template v-for="field in step.fields" :key="field.field_id">
          <div v-if="field.field_type === 'text'" class="form-field">
            <label :class="['field-label', { required: field.required }]">{{ field.label }}</label>
            <base-input
              :model-value="getFieldValue(field.field_id)"
              :placeholder="field.placeholder ?? undefined"
              @update:model-value="setFieldValue(field.field_id, $event)"
            />
          </div>

          <div v-else-if="field.field_type === 'textarea'" class="form-field">
            <label :class="['field-label', { required: field.required }]">{{ field.label }}</label>
            <base-textarea
              :model-value="getFieldValue(field.field_id)"
              :placeholder="field.placeholder ?? undefined"
              @update:model-value="setFieldValue(field.field_id, $event)"
            />
          </div>

          <div v-else-if="field.field_type === 'select'" class="form-field">
            <label :class="['field-label', { required: field.required }]">{{ field.label }}</label>
            <base-dropdown
              :model-value="getFieldValue(field.field_id)"
              :options="fieldOptions(field)"
              :placeholder="field.placeholder ?? undefined"
              @update:model-value="setFieldValue(field.field_id, $event)"
            />
          </div>

          <div v-else-if="field.field_type === 'datetime'" class="form-field">
            <label :class="['field-label', { required: field.required }]">{{ field.label }}</label>
            <base-date-time-picker
              :model-value="getFieldValue(field.field_id)"
              mode="datetime"
              @update:model-value="setFieldValue(field.field_id, $event)"
            />
          </div>

          <div v-else-if="field.field_type === 'date'" class="form-field">
            <label :class="['field-label', { required: field.required }]">{{ field.label }}</label>
            <base-date-time-picker
              :model-value="getFieldValue(field.field_id)"
              mode="date"
              @update:model-value="setFieldValue(field.field_id, $event)"
            />
          </div>

          <div v-else-if="field.field_type === 'rich_text'" class="form-field">
            <label :class="['field-label', { required: field.required }]">{{ field.label }}</label>
            <rich-text-editor
              :model-value="getFieldValue(field.field_id)"
              @update:model-value="setFieldValue(field.field_id, $event)"
            />
          </div>

          <div v-else-if="field.field_type === 'timeline'" class="form-field">
            <label :class="['field-label', { required: field.required }]">{{ field.label }}</label>
            <timeline-editor
              :model-value="getFieldValue(field.field_id)"
              @update:model-value="setFieldValue(field.field_id, $event)"
            />
          </div>

          <div v-else-if="field.field_type === 'attachment'" class="form-field">
            <label :class="['field-label', { required: field.required }]">{{ field.label }}</label>
            <base-file-upload
              accept="image/*,.pdf,.doc,.docx"
              multiple
              @select="handleFileSelect(field.field_id, $event)"
            />
          </div>

          <div v-else class="form-field">
            <label :class="['field-label', { required: field.required }]">{{ field.label }}</label>
            <base-input
              :model-value="getFieldValue(field.field_id)"
              :placeholder="field.placeholder ?? undefined"
              @update:model-value="setFieldValue(field.field_id, $event)"
            />
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import BaseInput from '../../../components/base/BaseInput.vue';
import BaseTextarea from '../../../components/base/BaseTextarea.vue';
import BaseDropdown from '../../../components/base/BaseDropdown.vue';
import BaseDateTimePicker from '../../../components/base/BaseDateTimePicker.vue';
import BaseFileUpload from '../../../components/base/BaseFileUpload.vue';
import RichTextEditor from './RichTextEditor.vue';
import TimelineEditor from './TimelineEditor.vue';

interface FormFieldSchema {
  field_id: string;
  label: string;
  field_type: string;
  required: boolean;
  placeholder?: string | null;
  options?: { value: string; label: string }[] | null;
}

interface FormStepSchema {
  step_id: string;
  title: string;
  description?: string | null;
  fields: FormFieldSchema[];
}

interface FormSchema {
  version: number;
  steps: FormStepSchema[];
}

const props = defineProps<{
  schema: FormSchema;
  modelValue: Record<string, unknown>;
}>();

const emit = defineEmits<{
  (e: 'update:modelValue', value: Record<string, unknown>): void;
}>();

const getFieldValue = (fieldId: string): string => {
  const val = props.modelValue?.[fieldId];
  if (val == null) return '';
  return String(val);
};

const setFieldValue = (fieldId: string, value: unknown) => {
  emit('update:modelValue', { ...props.modelValue, [fieldId]: value });
};

const fieldOptions = (field: FormFieldSchema) => {
  if (!field.options) return [];
  return field.options.map((o) => ({ value: o.value, label: o.label }));
};

const handleFileSelect = (fieldId: string, files: File[]) => {
  const fileNames = files.map((f) => f.name);
  setFieldValue(fieldId, fileNames);
};
</script>

<style scoped>
.schema-form-renderer {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.form-step {
  padding: 16px;
  background: var(--color-bg-secondary);
  border-radius: 8px;
}

.step-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 4px;
  color: var(--color-text-primary);
}

.step-description {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin-bottom: 16px;
}

.step-fields {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.field-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-secondary);
}

.field-label.required::after {
  content: ' *';
  color: var(--color-danger);
}
</style>
