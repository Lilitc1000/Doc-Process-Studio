<template>
  <div class="audit-action-panel">
    <h3>审核操作</h3>
    <div class="audit-form">
      <div class="form-group">
        <label class="form-label">审核意见 *</label>
        <base-textarea v-model="comment" placeholder="请输入审核意见..." />
      </div>
      <div class="audit-buttons">
        <base-button
          variant="danger"
          :disabled="!comment.trim() || processing"
          @click="$emit('reject', comment)"
        >
          驳回
        </base-button>
        <base-button
          variant="primary"
          :disabled="!comment.trim() || processing"
          @click="$emit('approve', comment)"
        >
          通过
        </base-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import BaseButton from '../../../../components/base/BaseButton.vue';
import BaseTextarea from '../../../../components/base/BaseTextarea.vue';

defineProps<{
  processing: boolean;
}>();

defineEmits<{
  (e: 'approve', comment: string): void;
  (e: 'reject', comment: string): void;
}>();

const comment = ref('');
</script>

<style scoped>
.audit-action-panel {
  padding: 20px;
  background: var(--color-bg-secondary);
  border-radius: 8px;
}

.audit-action-panel h3 {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 12px;
}

.audit-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-secondary);
}

.audit-buttons {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}
</style>
