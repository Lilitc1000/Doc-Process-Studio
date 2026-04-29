<template>
  <div v-if="auditLogs.length > 0" class="report-audit-timeline">
    <h3>审核记录</h3>
    <div class="timeline">
      <div v-for="log in auditLogs" :key="log.id" class="timeline-item">
        <div class="timeline-dot" :class="`dot-${log.action}`" />
        <div class="timeline-content">
          <div class="timeline-header">
            <span class="timeline-action">{{ actionLabel(log.action) }}</span>
            <span class="timeline-actor">{{
              log.actorName ?? log.actorId
            }}</span>
            <span class="timeline-time">{{ formatDate(log.createdAt) }}</span>
          </div>
          <div v-if="log.comment" class="timeline-comment">
            {{ log.comment }}
          </div>
          <div
            v-if="log.fromStatus && log.toStatus"
            class="timeline-status-change"
          >
            {{ statusLabel(log.fromStatus) }} →
            {{ statusLabel(log.toStatus) }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type {
  IncidentAuditLogEntry,
  IncidentReportStatus,
} from '../../../../types/incident-report/incident-report';
import { INCIDENT_STATUS_LABELS } from '../../../../types/incident-report/incident-report';

defineProps<{
  auditLogs: IncidentAuditLogEntry[];
}>();

const actionLabel = (action: string) => {
  const labels: Record<string, string> = {
    create: '创建',
    submit: '提交审核',
    approve: '通过审核',
    reject: '驳回',
    assign: '分配处理人',
    close: '关闭',
    reopen: '重新打开',
    migrated: '迁移',
  };
  return labels[action] ?? action;
};

const statusLabel = (status: string) =>
  INCIDENT_STATUS_LABELS[status as IncidentReportStatus] ?? status;

const formatDate = (dateStr: string) => {
  try {
    return new Date(dateStr).toLocaleString('zh-CN');
  } catch {
    return dateStr;
  }
};
</script>

<style scoped>
.report-audit-timeline {
  margin-top: 16px;
}

.report-audit-timeline h3 {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 12px;
  color: var(--color-text-primary);
}

.timeline {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.timeline-item {
  display: flex;
  gap: 10px;
  padding: 8px 0;
  position: relative;
}

.timeline-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-top: 6px;
  flex-shrink: 0;
  background: var(--color-text-tertiary);
}

.dot-create {
  background: var(--color-primary);
}
.dot-submit {
  background: var(--color-warning);
}
.dot-approve {
  background: var(--color-success);
}
.dot-reject {
  background: var(--color-danger);
}
.dot-close {
  background: var(--color-text-tertiary);
}
.dot-reopen {
  background: var(--color-primary);
}

.timeline-content {
  flex: 1;
  min-width: 0;
}

.timeline-header {
  display: flex;
  gap: 8px;
  align-items: center;
  font-size: 13px;
}

.timeline-action {
  font-weight: 500;
  color: var(--color-text-primary);
}

.timeline-actor {
  color: var(--color-text-secondary);
}

.timeline-time {
  color: var(--color-text-tertiary);
  font-size: 12px;
}

.timeline-comment {
  margin-top: 4px;
  font-size: 13px;
  color: var(--color-text-secondary);
  padding: 4px 8px;
  background: var(--color-bg-secondary);
  border-radius: 4px;
}

.timeline-status-change {
  margin-top: 2px;
  font-size: 12px;
  color: var(--color-text-tertiary);
}
</style>
