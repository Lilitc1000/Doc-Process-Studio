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
            <span class="timeline-time">{{
              formatDateTime(log.createdAt)
            }}</span>
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
import { formatDateTime } from '../../../../utils/common/date';

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
</script>

<style scoped>
.report-audit-timeline {
  margin-top: var(--space-lg);
}

.report-audit-timeline h3 {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  margin-bottom: var(--space-md);
  color: var(--color-text-primary);
}

.timeline {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.timeline-item {
  display: flex;
  gap: var(--space-md);
  padding: var(--space-sm) 0;
  position: relative;
}

.timeline-dot {
  width: 0.5rem;
  height: 0.5rem;
  border-radius: var(--radius-full);
  margin-top: var(--space-xs);
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
  gap: var(--space-sm);
  align-items: center;
  font-size: var(--text-sm);
}

.timeline-action {
  font-weight: var(--font-medium);
  color: var(--color-text-primary);
}

.timeline-actor {
  color: var(--color-text-secondary);
}

.timeline-time {
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}

.timeline-comment {
  margin-top: var(--space-xs);
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  padding: var(--space-xs) var(--space-sm);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
}

.timeline-status-change {
  margin-top: var(--space-2xs);
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}
</style>
