<template>
  <div v-if="selectedIds.length > 0" class="report-list-bulk-actions">
    <span class="bulk-count">已选择 {{ selectedIds.length }} 项</span>
    <base-button variant="ghost" size="sm" @click="$emit('clear-selection')">
      取消选择
    </base-button>
    <base-button
      v-if="canDelete"
      variant="danger"
      size="sm"
      @click="$emit('bulk-delete', selectedIds)"
    >
      批量删除
    </base-button>
  </div>
</template>

<script setup lang="ts">
import BaseButton from '../../../../components/base/BaseButton.vue';

defineProps<{
  selectedIds: string[];
  canDelete: boolean;
}>();

defineEmits<{
  (e: 'clear-selection'): void;
  (e: 'bulk-delete', ids: string[]): void;
}>();
</script>

<style scoped>
.report-list-bulk-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--color-primary-bg, #eff6ff);
  border-radius: 6px;
  margin-bottom: 8px;
}

.bulk-count {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-primary);
}
</style>
