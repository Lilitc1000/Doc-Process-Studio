<template>
  <div class="report-list-filters">
    <base-input
      :model-value="search"
      placeholder="搜索报告标题..."
      class="filter-search"
      @update:model-value="$emit('update:search', $event)"
      @keydown.enter="$emit('filter-change')"
    />
    <base-dropdown
      :model-value="status"
      :options="statusOptions"
      placeholder="状态"
      class="filter-dropdown"
      panel-min-width="160px"
      @update:model-value="$emit('update:status', $event)"
    />
    <base-dropdown
      :model-value="severity"
      :options="severityOptions"
      placeholder="严重级别"
      class="filter-dropdown"
      panel-min-width="160px"
      @update:model-value="$emit('update:severity', $event)"
    />
    <base-button variant="secondary" @click="$emit('filter-change')">
      筛选
    </base-button>
  </div>
</template>

<script setup lang="ts">
import BaseInput from '../../../../components/base/BaseInput.vue';
import BaseDropdown from '../../../../components/base/BaseDropdown.vue';
import BaseButton from '../../../../components/base/BaseButton.vue';

defineProps<{
  status: string;
  severity: string;
  search: string;
}>();

defineEmits<{
  (e: 'update:status', value: string): void;
  (e: 'update:severity', value: string): void;
  (e: 'update:search', value: string): void;
  (e: 'filter-change'): void;
}>();

const statusOptions = [
  { value: '', label: '全部状态' },
  { value: 'draft', label: '草稿' },
  { value: 'pending', label: '待审核' },
  { value: 'approved', label: '已批准' },
  { value: 'rejected', label: '已驳回' },
  { value: 'in_progress', label: '处理中' },
  { value: 'closed', label: '已关闭' },
];

const severityOptions = [
  { value: '', label: '全部级别' },
  { value: 'P0', label: 'P0 - 紧急' },
  { value: 'P1', label: 'P1 - 严重' },
  { value: 'P2', label: 'P2 - 一般' },
  { value: 'P3', label: 'P3 - 轻微' },
];
</script>

<style scoped>
.report-list-filters {
  display: flex;
  gap: 8px;
  align-items: center;
  padding: 12px 0;
  flex-wrap: wrap;
}

.filter-search {
  flex: 1;
  min-width: 200px;
}

.filter-dropdown {
  min-width: 120px;
}
</style>
