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
} from '../../../../types/incident-report/incident-report';
import { INCIDENT_STATUS_LABELS } from '../../../../types/incident-report/incident-report';
import ReportStatusBadge from '../../components/ReportStatusBadge.vue';
import ReportAuditTimeline from './ReportAuditTimeline.vue';

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
    value: formatDate(props.report.faultDate),
  },
  {
    key: 'created_at',
    label: '创建时间',
    value: formatDate(props.report.createdAt),
  },
]);

const formatDate = (dateStr: string | null) => {
  if (!dateStr) return '-';
  try {
    return new Date(dateStr).toLocaleString('zh-CN');
  } catch {
    return dateStr;
  }
};
</script>

<style scoped>
.report-detail-sidebar {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.detail-info-card {
  padding: 16px;
  background: var(--color-bg-secondary);
  border-radius: 8px;
}

.detail-info-card h3 {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 12px;
  color: var(--color-text-primary);
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 0;
  font-size: 13px;
}

.info-label {
  color: var(--color-text-secondary);
}

.info-value {
  color: var(--color-text-primary);
  font-weight: 500;
}
</style>
