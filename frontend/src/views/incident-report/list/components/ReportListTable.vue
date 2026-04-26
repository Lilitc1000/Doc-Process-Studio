<template>
  <div class="report-list-table">
    <div v-if="loading" class="report-list-loading">加载中...</div>
    <div v-else-if="items.length === 0" class="report-list-empty">暂无报告</div>
    <table v-else class="report-table">
      <thead>
        <tr>
          <th>编号</th>
          <th>标题</th>
          <th>状态</th>
          <th>级别</th>
          <th>日期</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in items" :key="item.id" class="report-list-row">
          <td class="cell-ref">{{ item.ref_no }}</td>
          <td class="cell-title">{{ item.title }}</td>
          <td class="cell-status">
            <report-status-badge :status="item.status" />
          </td>
          <td class="cell-severity">{{ item.severity ?? '-' }}</td>
          <td class="cell-date">{{ formatDate(item.created_at) }}</td>
          <td class="cell-actions">
            <base-button
              variant="ghost"
              size="sm"
              class="action-view"
              @click="$emit('view', item.id)"
            >
              查看
            </base-button>
            <base-button
              v-if="item.status === 'draft' || item.status === 'rejected'"
              variant="ghost"
              size="sm"
              class="action-edit"
              @click="$emit('edit', item.id)"
            >
              编辑
            </base-button>
            <base-button
              v-if="canDelete"
              variant="ghost"
              size="sm"
              class="action-delete"
              @click="$emit('delete', item.id)"
            >
              删除
            </base-button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
import type { IncidentReportSummaryItem } from '../../../../types/incident-report/incident-report';
import BaseButton from '../../../../components/base/BaseButton.vue';
import ReportStatusBadge from '../../components/ReportStatusBadge.vue';

defineProps<{
  items: IncidentReportSummaryItem[];
  loading: boolean;
  canDelete: boolean;
}>();

defineEmits<{
  (e: 'view', id: string): void;
  (e: 'edit', id: string): void;
  (e: 'delete', id: string): void;
}>();

const formatDate = (dateStr: string) => {
  try {
    return new Date(dateStr).toLocaleDateString('zh-CN');
  } catch {
    return dateStr;
  }
};
</script>

<style scoped>
.report-list-table {
  width: 100%;
}

.report-list-loading,
.report-list-empty {
  text-align: center;
  padding: 40px;
  color: var(--color-text-secondary);
}

.report-table {
  width: 100%;
  border-collapse: collapse;
}

.report-table th {
  text-align: left;
  padding: 8px 12px;
  font-size: 12px;
  color: var(--color-text-secondary);
  border-bottom: 1px solid var(--color-border);
  font-weight: 500;
}

.report-table td {
  padding: 10px 12px;
  font-size: 14px;
  border-bottom: 1px solid var(--color-border);
}

.report-list-row {
  transition: background-color 0.15s;
}

.report-list-row:hover {
  background: var(--color-bg-hover);
}

.cell-ref {
  color: var(--color-text-secondary);
  font-family: monospace;
  font-size: 13px;
}

.cell-title {
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cell-actions {
  display: flex;
  gap: 4px;
}
</style>
