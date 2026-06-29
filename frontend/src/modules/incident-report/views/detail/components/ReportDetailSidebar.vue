<template>
  <div class="report-detail-sidebar">
    <div class="detail-info-card">
      <h3>基本信息</h3>
      <div v-for="field in infoFields" :key="field.key" class="info-row">
        <span class="info-label">{{ field.label }}</span>
        <span v-if="field.key === 'status'" class="info-value">
          <report-status-badge :status="report.status" />
        </span>
        <span v-else class="info-value">{{ field.value ?? '-' }}</span>
      </div>
    </div>

    <report-audit-timeline :audit-logs="auditLogs" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type {
  IncidentReportDetailItem,
  IncidentAuditLogEntry,
} from '../../../types/incident-report';
import { INCIDENT_STATUS_LABELS } from '../../../types/incident-report';
import ReportStatusBadge from '../../components/ReportStatusBadge.vue';
import ReportAuditTimeline from './ReportAuditTimeline.vue';
import { formatDateTime } from '@shared/utils/date';

const props = defineProps<{
  report: IncidentReportDetailItem;
  auditLogs: IncidentAuditLogEntry[];
}>();

const infoFields = computed(() => [
  {
    key: 'status',
    label: '状态',
    value: INCIDENT_STATUS_LABELS[props.report.status] ?? props.report.status,
  },
  { key: 'severity', label: '级别', value: props.report.severity },
  {
    key: 'reporter',
    label: '报告人',
    value: props.report.reporterName ?? props.report.reporterId,
  },
  {
    key: 'assignee',
    label: '处理人',
    value: props.report.assigneeName ?? props.report.assigneeId,
  },
  {
    key: 'verifier',
    label: '审核人',
    value: props.report.verifierName ?? props.report.verifierId,
  },
  { key: 'system', label: '系统', value: props.report.system },
  { key: 'site', label: '站点', value: props.report.siteId },
  {
    key: 'fault_date',
    label: '故障日期',
    value: formatDateTime(props.report.faultDate),
  },
  {
    key: 'created_at',
    label: '创建时间',
    value: formatDateTime(props.report.createdAt),
  },
]);
</script>

<style scoped>
.report-detail-sidebar {
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
}

.detail-info-card {
  padding: var(--space-lg);
  background: rgba(255, 255, 255, 0.96);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-xs);
}

.detail-info-card h3 {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  margin-bottom: var(--space-md);
  color: var(--color-text-primary);
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-xs) 0;
  font-size: var(--text-xs);
}

.info-label {
  color: var(--color-text-secondary);
}

.info-value {
  color: var(--color-text-primary);
  font-weight: var(--font-medium);
}
</style>
