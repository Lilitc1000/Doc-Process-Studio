<template>
  <div class="incident-report-edit-view">
    <div v-if="loading" class="edit-loading">加载中...</div>
    <div v-else-if="!report" class="edit-empty">报告不存在</div>
    <template v-else>
      <div class="edit-header">
        <base-button
          variant="ghost"
          size="sm"
          @click="router.push(`/incident-report/${report.id}`)"
        >
          ← 返回详情
        </base-button>
        <h1>编辑报告 / Edit Report - {{ report.refNo }}</h1>
        <div class="edit-header-actions">
          <base-button
            variant="ghost"
            size="sm"
            :disabled="downloadingDocx"
            @click="handleDownloadDocx"
          >
            {{ downloadingDocx ? '生成中...' : '下载 Word' }}
          </base-button>
        </div>
      </div>

      <div class="edit-form zone-card">
        <div class="section-heading">
          <h3>SECTION A - 故障记录 / Fault Details</h3>
        </div>
        <div class="zone-grid two-column">
          <label class="field-item">
            <span>报告标题 / Report Title *</span>
            <base-input v-model="formData.title" placeholder="请输入报告标题" />
          </label>
          <label class="field-item">
            <span>参考编号 / Reference No.</span>
            <base-input
              v-model="formAnswers.manual_reference_no"
              placeholder="例如：DAS2 Fault Log Form-015"
            />
          </label>
          <label class="field-item">
            <span>故障上报日期 / Date of Fault Reporting *</span>
            <base-date-time-picker
              mode="date"
              placeholder="选择日期"
              :model-value="formData.faultDate"
              @update:model-value="formData.faultDate = $event"
            />
          </label>
          <label class="field-item">
            <span>故障上报时间 / Time of Fault Reporting</span>
            <base-date-time-picker
              mode="time"
              placeholder="选择时间"
              :model-value="formAnswers.manual_fault_time"
              @update:model-value="formAnswers.manual_fault_time = $event"
            />
          </label>
          <label class="field-item">
            <span>报告人 / Reporting Person *</span>
            <base-input
              v-model="formAnswers.manual_reporting_person"
              placeholder="报告人姓名"
            />
          </label>
          <label class="field-item">
            <span>审核人 / Verified By</span>
            <base-input
              v-model="formAnswers.manual_verified_by"
              placeholder="审核人姓名"
            />
          </label>
          <label class="field-item">
            <span>站点编号 / Site ID *</span>
            <base-input v-model="formData.siteId" placeholder="如：SITE-01" />
          </label>
          <label class="field-item">
            <span>系统 / 子系统 / System / Subsystems *</span>
            <base-input
              v-model="formData.system"
              placeholder="如：数据库系统"
            />
          </label>
          <label class="field-item">
            <span>故障位置 / Location of Fault *</span>
            <base-input
              v-model="formAnswers.manual_location"
              placeholder="故障发生位置"
            />
          </label>
          <label class="field-item full-width">
            <span>故障现象详情 / Details of Fault Symptom *</span>
            <base-textarea
              v-model="formAnswers.manual_fault_symptom"
              rows="3"
              placeholder="请详细描述故障现象..."
            />
          </label>
          <label class="field-item">
            <span>到场时间 / Arrival Datetime</span>
            <base-date-time-picker
              mode="datetime"
              :model-value="formAnswers.manual_arrival_datetime"
              @update:model-value="formAnswers.manual_arrival_datetime = $event"
            />
          </label>
          <label class="field-item">
            <span>恢复时间 / Clearance Datetime</span>
            <base-date-time-picker
              mode="datetime"
              :model-value="formAnswers.manual_clearance_datetime"
              @update:model-value="
                formAnswers.manual_clearance_datetime = $event
              "
            />
          </label>
          <label class="field-item">
            <span>维护人员 / Service Person</span>
            <base-input
              v-model="formAnswers.manual_service_person"
              placeholder="维护人员姓名"
            />
          </label>
          <label class="field-item">
            <span>故障原因 / Fault Cause</span>
            <base-input
              v-model="formAnswers.manual_fault_cause"
              placeholder="故障原因"
            />
          </label>
          <label class="field-item">
            <span>使用物料 / Materials Used</span>
            <base-input
              v-model="formAnswers.manual_materials_used"
              placeholder="使用的物料"
            />
          </label>
        </div>

        <div class="section-heading" style="margin-top: 1.2rem">
          <h3>SECTION B - 维修与验证 / Repair Works & Verification</h3>
        </div>
        <div class="zone-grid two-column">
          <label class="field-item full-width">
            <span>维修详情 / Repair Details</span>
            <base-textarea
              v-model="formAnswers.manual_repair_details"
              rows="3"
              placeholder="请描述维修过程..."
            />
          </label>
          <label class="field-item">
            <span>承包商人员 / Contractor Staff</span>
            <base-input
              v-model="formAnswers.manual_contractor_staff"
              placeholder="承包商人员"
            />
          </label>
          <label class="field-item">
            <span>承包商签名 / Contractor Signature</span>
            <base-input
              v-model="formAnswers.manual_contractor_signature"
              placeholder="签名"
            />
          </label>
          <label class="field-item">
            <span>承包商日期 / Contractor Date</span>
            <base-date-time-picker
              mode="date"
              placeholder="选择日期"
              :model-value="formAnswers.manual_contractor_date"
              @update:model-value="formAnswers.manual_contractor_date = $event"
            />
          </label>
        </div>

        <div class="section-heading" style="margin-top: 1.2rem">
          <h3>SECTION C - 结案与签署 / Closeout & Sign-off</h3>
        </div>
        <div class="zone-grid two-column">
          <label class="field-item">
            <span>严重级别 / Severity</span>
            <base-dropdown
              :model-value="formData.severity"
              :options="severityOptions"
              placeholder="请选择严重级别"
              @update:model-value="formData.severity = $event"
            />
          </label>
          <label class="field-item">
            <span>状态 / Status</span>
            <base-dropdown
              :model-value="formAnswers.manual_status"
              :options="statusOptions"
              placeholder="请选择状态"
              @update:model-value="formAnswers.manual_status = $event"
            />
          </label>
          <label
            v-if="formAnswers.manual_status === 'follow_up_action_required'"
            class="field-item"
          >
            <span>跟进单号 / Follow-up Ref No.</span>
            <base-input
              v-model="formAnswers.manual_status_ref_no"
              placeholder="例如：DAS2-FAULT-016"
            />
          </label>
          <label class="field-item">
            <span>业主代表 / Employer Rep</span>
            <base-input
              v-model="formAnswers.manual_employer_rep"
              placeholder="业主代表"
            />
          </label>
          <label class="field-item">
            <span>业主代表签名 / Employer Signature</span>
            <base-input
              v-model="formAnswers.manual_employer_signature"
              placeholder="签名"
            />
          </label>
          <label class="field-item">
            <span>结案日期 / Closeout Date</span>
            <base-date-time-picker
              mode="date"
              placeholder="选择日期"
              :model-value="formAnswers.manual_closeout_date"
              @update:model-value="formAnswers.manual_closeout_date = $event"
            />
          </label>
          <label class="field-item full-width">
            <span>备注 / Comments</span>
            <base-textarea
              v-model="formAnswers.manual_comments"
              rows="2"
              placeholder="备注信息..."
            />
          </label>
        </div>

        <div class="section-heading" style="margin-top: 1.2rem">
          <h3>AI 正文 / AI Body</h3>
        </div>
        <div class="zone-grid">
          <label class="field-item full-width">
            <span>事故简述 / Incident Summary</span>
            <base-textarea
              v-model="formAnswers.body_description"
              rows="4"
              placeholder="请描述事故概况..."
            />
          </label>
          <label class="field-item full-width">
            <span>影响范围 / Impact Scope</span>
            <base-input
              v-model="formAnswers.body_impact_scope"
              placeholder="影响范围"
            />
          </label>
          <label class="field-item full-width">
            <span>根因分析 / Root Cause</span>
            <base-textarea
              v-model="formAnswers.body_root_cause"
              rows="3"
              placeholder="根因分析..."
            />
          </label>
          <label class="field-item full-width">
            <span>后续动作 / Follow-Up Actions</span>
            <base-textarea
              v-model="formAnswers.body_follow_up"
              rows="3"
              placeholder="后续动作计划..."
            />
          </label>
        </div>

        <div class="section-heading" style="margin-top: 1.2rem">
          <h3>附录 / Appendix</h3>
        </div>
        <div class="zone-grid">
          <label class="field-item full-width">
            <span>附录内容 / Appendix Notes</span>
            <base-textarea
              v-model="formAnswers.appendix_notes"
              rows="4"
              placeholder="请输入附录内容..."
            />
          </label>
        </div>
      </div>

      <div class="edit-actions">
        <base-button
          variant="secondary"
          @click="router.push(`/incident-report/${report.id}`)"
        >
          取消 / Cancel
        </base-button>
        <base-button
          variant="primary"
          :disabled="!formData.title.trim() || saving"
          @click="handleSave"
        >
          {{ saving ? '保存中...' : '保存 / Save' }}
        </base-button>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import {
  fetchIncidentReportDetail,
  updateIncidentReport,
  previewIncidentReport,
} from '../../../api/incident-report';
import type { IncidentReportDetailItem } from '../../../types/incident-report/incident-report';
import BaseButton from '../../../components/base/BaseButton.vue';
import BaseInput from '../../../components/base/BaseInput.vue';
import BaseDropdown from '../../../components/base/BaseDropdown.vue';
import BaseTextarea from '../../../components/base/BaseTextarea.vue';
import BaseDateTimePicker from '../../../components/base/BaseDateTimePicker.vue';

const route = useRoute();
const router = useRouter();

const report = ref<IncidentReportDetailItem | null>(null);
const loading = ref(true);
const saving = ref(false);
const downloadingDocx = ref(false);

const formData = ref({
  title: '',
  severity: '',
  system: '',
  siteId: '',
  faultDate: '',
});

const defaultFormAnswers: Record<string, string> = {
  manual_reference_no: '',
  manual_fault_time: '',
  manual_reporting_person: '',
  manual_verified_by: '',
  manual_location: '',
  manual_fault_symptom: '',
  manual_arrival_datetime: '',
  manual_clearance_datetime: '',
  manual_service_person: '',
  manual_fault_cause: '',
  manual_materials_used: '',
  manual_repair_details: '',
  manual_contractor_staff: '',
  manual_contractor_signature: '',
  manual_contractor_date: '',
  manual_status: '',
  manual_status_ref_no: '',
  manual_employer_rep: '',
  manual_employer_signature: '',
  manual_closeout_date: '',
  manual_comments: '',
  quick_narrative: '',
  body_description: '',
  body_impact_scope: '',
  body_impact_severity: '',
  body_business_impact: '',
  body_trigger: '',
  body_root_cause: '',
  body_follow_up: '',
  appendix_notes: '',
};

const formAnswers = ref<Record<string, string>>({ ...defaultFormAnswers });

const severityOptions = [
  { value: '', label: '请选择 / Select' },
  { value: 'minor', label: '一般 / Minor' },
  { value: 'major', label: '严重 / Major' },
  { value: 'critical', label: '致命 / Critical' },
];

const statusOptions = [
  { value: '', label: '请选择 / Select' },
  { value: 'follow_up_action_required', label: '跟进中 / Follow-up' },
  { value: 'closed', label: '已关闭 / Closed' },
];

const handleSave = async () => {
  if (!report.value || !formData.value.title.trim()) return;
  saving.value = true;
  try {
    await updateIncidentReport(report.value.id, {
      title: formData.value.title,
      severity: formData.value.severity || undefined,
      system: formData.value.system || undefined,
      siteId: formData.value.siteId || undefined,
      faultDate: formData.value.faultDate || undefined,
      formData: formAnswers.value,
    });
    router.push(`/incident-report/${report.value.id}`);
  } finally {
    saving.value = false;
  }
};

const handleDownloadDocx = async () => {
  if (!report.value || downloadingDocx.value) return;
  downloadingDocx.value = true;
  try {
    const preview = await previewIncidentReport(report.value.id, {});
    if (!preview.docxBase64 || !preview.docxFileName) return;
    const binaryString = atob(preview.docxBase64);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    const blob = new Blob([bytes], {
      type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = preview.docxFileName;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  } finally {
    downloadingDocx.value = false;
  }
};

onMounted(async () => {
  const reportId = route.params.id as string;
  try {
    const data = await fetchIncidentReportDetail(reportId);
    report.value = data;
    formData.value = {
      title: data.title,
      severity: data.severity ?? '',
      system: data.system ?? '',
      siteId: data.siteId ?? '',
      faultDate: data.faultDate ?? '',
    };
    const fd = (data.formData || {}) as Record<string, unknown>;
    const answers = { ...defaultFormAnswers };
    for (const key of Object.keys(defaultFormAnswers)) {
      if (fd[key] !== undefined && fd[key] !== null) {
        answers[key] = String(fd[key]);
      }
    }
    formAnswers.value = answers;
  } finally {
    loading.value = false;
  }
});
</script>

<style scoped>
.incident-report-edit-view {
  --ir-border: #e2e8f0;
  --ir-text: #0f172a;
  --ir-muted: #475569;

  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 24px;
  max-width: 960px;
  margin: 0 auto;
}

.edit-loading,
.edit-empty {
  text-align: center;
  padding: 40px;
  color: var(--color-text-secondary);
}

.edit-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.edit-header h1 {
  font-size: 20px;
  font-weight: 600;
  margin: 0;
  color: var(--ir-text);
  flex: 1;
}

.edit-header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
}

.edit-form {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
}

.zone-card {
  border: 1px solid var(--ir-border);
  border-radius: 16px;
  padding: 1rem;
  background: #fff;
}

.section-heading {
  margin-bottom: 0.75rem;
}

.section-heading h3 {
  margin: 0;
  font-size: 0.96rem;
  color: #1e3a8a;
  letter-spacing: 0.01em;
}

.zone-grid {
  display: grid;
  gap: 0.84rem;
}

.zone-grid.two-column {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.field-item {
  display: grid;
  gap: 0.44rem;
}

.field-item > span {
  font-size: 0.78rem;
  color: #475569;
}

.field-item.full-width {
  grid-column: 1 / -1;
}

.edit-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding-top: 20px;
  border-top: 1px solid var(--ir-border);
  margin-top: 20px;
}

@media (max-width: 768px) {
  .zone-grid.two-column {
    grid-template-columns: 1fr;
  }
}
</style>
