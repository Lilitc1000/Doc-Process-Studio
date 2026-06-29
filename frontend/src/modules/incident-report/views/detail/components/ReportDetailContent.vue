<template>
  <div class="report-detail-content">
    <div v-if="hasAnyData" class="detail-sections">
      <div class="detail-section">
        <div class="section-title">
          <h3>SECTION A - 故障记录 / Fault Details</h3>
        </div>
        <div class="section-body">
          <div class="field-grid two-column">
            <div class="field-row">
              <span class="field-label">报告标题 / Report Title</span>
              <span class="field-value">{{ report.title || '-' }}</span>
            </div>
            <div class="field-row">
              <span class="field-label">参考编号 / Reference No.</span>
              <span class="field-value">{{
                getFormValue('manual_reference_no')
              }}</span>
            </div>
            <div class="field-row">
              <span class="field-label"
                >故障上报日期 / Date of Fault Reporting</span
              >
              <span class="field-value">{{
                report.faultDate || getFormValue('manual_fault_date') || '-'
              }}</span>
            </div>
            <div class="field-row">
              <span class="field-label"
                >故障上报时间 / Time of Fault Reporting</span
              >
              <span class="field-value">{{
                getFormValue('manual_fault_time')
              }}</span>
            </div>
            <div class="field-row">
              <span class="field-label">报告人 / Reporting Person</span>
              <span class="field-value">{{
                getFormValue('manual_reporting_person')
              }}</span>
            </div>
            <div class="field-row">
              <span class="field-label">审核人 / Verified By</span>
              <span class="field-value">{{
                getFormValue('manual_verified_by')
              }}</span>
            </div>
            <div class="field-row">
              <span class="field-label">站点编号 / Site ID</span>
              <span class="field-value">{{
                report.siteId || getFormValue('manual_site_id') || '-'
              }}</span>
            </div>
            <div class="field-row">
              <span class="field-label">系统 / 子系统 / System</span>
              <span class="field-value">{{
                report.system || getFormValue('manual_system') || '-'
              }}</span>
            </div>
            <div class="field-row">
              <span class="field-label">故障位置 / Location of Fault</span>
              <span class="field-value">{{
                getFormValue('manual_location')
              }}</span>
            </div>
            <div class="field-row full-width">
              <span class="field-label"
                >故障现象详情 / Details of Fault Symptom</span
              >
              <span class="field-value">{{
                getFormValue('manual_fault_symptom')
              }}</span>
            </div>
            <div class="field-row">
              <span class="field-label">到场时间 / Arrival Datetime</span>
              <span class="field-value">{{
                getFormValue('manual_arrival_datetime')
              }}</span>
            </div>
            <div class="field-row">
              <span class="field-label">恢复时间 / Clearance Datetime</span>
              <span class="field-value">{{
                getFormValue('manual_clearance_datetime')
              }}</span>
            </div>
            <div class="field-row">
              <span class="field-label">维护人员 / Service Person</span>
              <span class="field-value">{{
                getFormValue('manual_service_person')
              }}</span>
            </div>
            <div class="field-row">
              <span class="field-label">故障原因 / Fault Cause</span>
              <span class="field-value">{{
                getFormValue('manual_fault_cause')
              }}</span>
            </div>
            <div class="field-row">
              <span class="field-label">使用物料 / Materials Used</span>
              <span class="field-value">{{
                getFormValue('manual_materials_used')
              }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="detail-section">
        <div class="section-title">
          <h3>SECTION B - 维修与验证 / Repair Works & Verification</h3>
        </div>
        <div class="section-body">
          <div class="field-grid">
            <div class="field-row full-width">
              <span class="field-label">维修详情 / Repair Details</span>
              <span class="field-value">{{
                getFormValue('manual_repair_details')
              }}</span>
            </div>
            <div class="field-row">
              <span class="field-label">承包商人员 / Contractor Staff</span>
              <span class="field-value">{{
                getFormValue('manual_contractor_staff')
              }}</span>
            </div>
            <div class="field-row">
              <span class="field-label">承包商签名 / Contractor Signature</span>
              <span class="field-value">{{
                getFormValue('manual_contractor_signature')
              }}</span>
            </div>
            <div class="field-row">
              <span class="field-label">承包商日期 / Contractor Date</span>
              <span class="field-value">{{
                getFormValue('manual_contractor_date')
              }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="detail-section">
        <div class="section-title">
          <h3>SECTION C - 结案与签署 / Closeout & Sign-off</h3>
        </div>
        <div class="section-body">
          <div class="field-grid two-column">
            <div class="field-row">
              <span class="field-label">严重级别 / Severity</span>
              <span class="field-value">{{
                report.severity || getFormValue('manual_severity') || '-'
              }}</span>
            </div>
            <div class="field-row">
              <span class="field-label">状态 / Status</span>
              <span class="field-value">{{
                getFormValue('manual_status')
              }}</span>
            </div>
            <div class="field-row">
              <span class="field-label">跟进单号 / Follow-up Ref No.</span>
              <span class="field-value">{{
                getFormValue('manual_status_ref_no')
              }}</span>
            </div>
            <div class="field-row">
              <span class="field-label">业主代表 / Employer Rep</span>
              <span class="field-value">{{
                getFormValue('manual_employer_rep')
              }}</span>
            </div>
            <div class="field-row">
              <span class="field-label">业主代表签名 / Employer Signature</span>
              <span class="field-value">{{
                getFormValue('manual_employer_signature')
              }}</span>
            </div>
            <div class="field-row">
              <span class="field-label">结案日期 / Closeout Date</span>
              <span class="field-value">{{
                getFormValue('manual_closeout_date')
              }}</span>
            </div>
            <div class="field-row full-width">
              <span class="field-label">备注 / Comments</span>
              <span class="field-value">{{
                getFormValue('manual_comments')
              }}</span>
            </div>
          </div>
        </div>
      </div>

      <div v-if="hasBodyData" class="detail-section">
        <div class="section-title">
          <h3>AI 正文 / AI Body</h3>
        </div>
        <div class="section-body">
          <div class="sub-section-card">
            <div class="sub-section-header">
              <h4>事故简述 / Incident Summary</h4>
            </div>
            <div class="sub-section-body">
              <p class="text-block">{{ getFormValue('body_description') }}</p>
            </div>
          </div>

          <div
            v-if="timelineItems.length > 0 || hasTimelineTimeRange"
            class="sub-section-card"
          >
            <div class="sub-section-header">
              <h4>时间线 / Timeline</h4>
            </div>
            <div class="sub-section-body">
              <div v-if="hasTimelineTimeRange" class="timeline-range">
                <div class="timeline-range-item">
                  <span class="field-label">开始时间 / Start Time</span>
                  <span class="field-value">{{
                    getFormValue('body_affected_start_time')
                  }}</span>
                </div>
                <div class="timeline-range-item">
                  <span class="field-label">结束时间 / End Time</span>
                  <span class="field-value">{{
                    getFormValue('body_affected_end_time')
                  }}</span>
                </div>
              </div>
              <table v-if="timelineItems.length > 0" class="timeline-table">
                <thead>
                  <tr>
                    <th>时间</th>
                    <th>事件</th>
                    <th>处理</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(item, idx) in timelineItems" :key="idx">
                    <td>{{ item.time || '-' }}</td>
                    <td>{{ item.event || '-' }}</td>
                    <td>{{ item.resolution || '-' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <div v-if="hasImpactData" class="sub-section-card">
            <div class="sub-section-header">
              <h4>影响范围 / 严重级别 / Impact & Severity</h4>
            </div>
            <div class="sub-section-body">
              <div class="field-grid two-column">
                <div class="field-row">
                  <span class="field-label">影响范围 / Impact Scope</span>
                  <span class="field-value">{{
                    getFormValue('body_impact_scope')
                  }}</span>
                </div>
                <div class="field-row">
                  <span class="field-label">严重级别 / Impact Severity</span>
                  <span class="field-value">{{
                    getFormValue('body_impact_severity')
                  }}</span>
                </div>
                <div class="field-row full-width">
                  <span class="field-label">业务影响 / Business Impact</span>
                  <span class="field-value">{{
                    getFormValue('body_business_impact')
                  }}</span>
                </div>
              </div>
            </div>
          </div>

          <div v-if="hasRootCauseData" class="sub-section-card">
            <div class="sub-section-header">
              <h4>根因分析 / Root Cause</h4>
            </div>
            <div class="sub-section-body">
              <div class="field-grid">
                <div class="field-row">
                  <span class="field-label">触发原因 / Trigger</span>
                  <span class="field-value">{{
                    getFormValue('body_trigger')
                  }}</span>
                </div>
                <div class="field-row full-width">
                  <span class="field-label">根因 / Root Cause</span>
                  <span class="field-value">{{
                    getFormValue('body_root_cause')
                  }}</span>
                </div>
              </div>
            </div>
          </div>

          <div v-if="hasFollowUpData" class="sub-section-card">
            <div class="sub-section-header">
              <h4>后续动作 / Follow-Up Actions</h4>
            </div>
            <div class="sub-section-body">
              <p class="text-block">{{ getFormValue('body_follow_up') }}</p>
            </div>
          </div>
        </div>
      </div>

      <div v-if="hasAppendixData" class="detail-section">
        <div class="section-title">
          <h3>附录 / Appendix</h3>
        </div>
        <div class="section-body">
          <div class="appendix-content">
            <div
              v-if="isHtmlAppendix"
              v-safe-html="appendixContent"
              class="appendix-html"
            />
            <p v-else class="text-block">{{ appendixContent }}</p>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="content-empty">暂无报告内容</div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import humps from 'humps';
import type { IncidentReportDetailItem } from '../../../types/incident-report';

const props = defineProps<{
  report: IncidentReportDetailItem;
}>();

const formData = computed(() => {
  const fd = humps.decamelizeKeys(
    (props.report.formData || {}) as Record<string, unknown>,
  ) as Record<string, unknown>;
  const result: Record<string, unknown> = {};
  for (const [key, raw] of Object.entries(fd)) {
    if (raw !== null && raw !== undefined) {
      if (
        typeof raw === 'object' &&
        'value' in (raw as Record<string, unknown>)
      ) {
        result[key] = (raw as Record<string, unknown>).value ?? '';
      } else {
        result[key] = raw;
      }
    }
  }
  return result;
});

const getFormValue = (key: string): string => {
  const value = formData.value[key];
  if (value === null || value === undefined) return '-';
  if (Array.isArray(value)) return JSON.stringify(value, null, 2);
  if (typeof value === 'object') return JSON.stringify(value, null, 2);
  return String(value);
};

const timelineItems = computed(() => {
  const raw = formData.value.body_timeline;
  if (!raw) return [];
  try {
    const parsed = typeof raw === 'string' ? JSON.parse(raw) : raw;
    if (Array.isArray(parsed)) return parsed;
    return [];
  } catch {
    return [];
  }
});

const hasTimelineTimeRange = computed(() => {
  const start = formData.value.body_affected_start_time;
  const end = formData.value.body_affected_end_time;
  return (
    (start !== undefined && start !== null && start !== '' && start !== '-') ||
    (end !== undefined && end !== null && end !== '' && end !== '-')
  );
});

const hasImpactData = computed(() => {
  const keys = [
    'body_impact_scope',
    'body_impact_severity',
    'body_business_impact',
  ];
  return keys.some((key) => {
    const val = formData.value[key];
    return val !== undefined && val !== null && val !== '' && val !== '-';
  });
});

const hasRootCauseData = computed(() => {
  const keys = ['body_trigger', 'body_root_cause'];
  return keys.some((key) => {
    const val = formData.value[key];
    return val !== undefined && val !== null && val !== '' && val !== '-';
  });
});

const hasFollowUpData = computed(() => {
  const val = formData.value.body_follow_up;
  return val !== undefined && val !== null && val !== '' && val !== '-';
});

const appendixContent = computed(() => getFormValue('appendix_notes'));

const isHtmlAppendix = computed(() => {
  const content = appendixContent.value;
  return content.startsWith('<') && content.includes('</');
});

const hasBodyData = computed(() => {
  const bodyKeys = [
    'body_description',
    'body_affected_start_time',
    'body_affected_end_time',
    'body_impact_scope',
    'body_impact_severity',
    'body_business_impact',
    'body_trigger',
    'body_root_cause',
    'body_follow_up',
    'body_timeline',
  ];
  return bodyKeys.some((key) => {
    const val = formData.value[key];
    return val !== undefined && val !== null && val !== '' && val !== '-';
  });
});

const hasAppendixData = computed(() => {
  const val = formData.value.appendix_notes;
  return val !== undefined && val !== null && val !== '' && val !== '-';
});

const hasAnyData = computed(() => {
  return (
    Object.keys(formData.value).length > 0 ||
    props.report.title ||
    props.report.severity ||
    props.report.system ||
    props.report.siteId
  );
});
</script>

<style scoped>
.report-detail-content {
  flex: 1;
  min-width: 0;
}

.detail-sections {
  display: flex;
  flex-direction: column;
  gap: var(--space-xl);
}

.detail-section {
  background: rgba(255, 255, 255, 0.96);
  border-radius: var(--radius-md);
  overflow: hidden;
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-xs);
}

.section-title {
  padding: var(--space-md) var(--space-lg);
  background: var(--color-bg-tertiary);
  border-bottom: 1px solid var(--color-border);
}

.section-title h3 {
  margin: 0;
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
}

.section-body {
  padding: var(--space-lg);
}

.field-grid {
  display: grid;
  gap: var(--space-md);
}

.field-grid.two-column {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.field-row {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
}

.field-row.full-width {
  grid-column: 1 / -1;
}

.field-label {
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
  font-weight: var(--font-medium);
}

.field-value {
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  white-space: pre-wrap;
  word-break: break-word;
  line-height: var(--leading-normal);
}

.sub-section-card {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  margin-bottom: var(--space-md);
  background: var(--color-bg-primary);
}

.sub-section-card:last-child {
  margin-bottom: 0;
}

.sub-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-sm) var(--space-md);
  border-bottom: 1px solid var(--color-border);
  background: var(--color-bg-secondary);
}

.sub-section-header h4 {
  margin: 0;
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
}

.sub-section-body {
  padding: var(--space-md);
}

.text-block {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  white-space: pre-wrap;
  word-break: break-word;
  line-height: var(--leading-relaxed);
}

.timeline-range {
  display: flex;
  gap: var(--space-xl);
  margin-bottom: var(--space-md);
  padding-bottom: var(--space-md);
  border-bottom: 1px dashed var(--color-border);
}

.timeline-range-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
}

.timeline-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-xs);
}

.timeline-table th {
  background: var(--color-bg-tertiary);
  padding: var(--space-xs) var(--space-sm);
  text-align: left;
  font-weight: var(--font-semibold);
  border: 1px solid var(--color-border);
  white-space: nowrap;
}

.timeline-table td {
  padding: var(--space-xs) var(--space-sm);
  border: 1px solid var(--color-border);
  white-space: pre-wrap;
  word-break: break-word;
}

.appendix-content {
  line-height: var(--leading-relaxed);
}

.appendix-html {
  line-height: var(--leading-relaxed);
}

.appendix-html :deep(img) {
  max-width: 100%;
  height: auto;
  border-radius: var(--radius-sm);
  margin: var(--space-xs) 0;
}

.appendix-html :deep(table) {
  width: 100%;
  border-collapse: collapse;
}

.appendix-html :deep(th),
.appendix-html :deep(td) {
  border: 1px solid var(--color-border);
  padding: var(--space-xs) var(--space-sm);
  text-align: left;
  font-size: var(--text-sm);
}

.appendix-html :deep(th) {
  background: var(--color-bg-tertiary);
  font-weight: var(--font-semibold);
}

.appendix-html :deep(ul),
.appendix-html :deep(ol) {
  padding-left: var(--space-xl);
  margin: var(--space-xs) 0;
}

.appendix-html :deep(p) {
  margin: var(--space-xs) 0;
}

.content-empty {
  text-align: center;
  padding: var(--space-xl);
  color: var(--color-text-tertiary);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
}

@media (max-width: 768px) {
  .field-grid.two-column {
    grid-template-columns: 1fr;
  }

  .timeline-range {
    flex-direction: column;
    gap: var(--space-md);
  }
}
</style>
