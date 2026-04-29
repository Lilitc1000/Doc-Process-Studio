<template>
  <div class="incident-report-create-view">
    <div class="create-header">
      <base-button
        variant="ghost"
        size="sm"
        @click="router.push('/incident-report')"
      >
        ← 返回列表
      </base-button>
      <h1>新建事故报告 / New Incident Report</h1>
    </div>

    <div class="wizard-steps">
      <div
        v-for="(step, index) in WIZARD_STEPS"
        :key="step.key"
        :class="[
          'wizard-step',
          { active: currentStep === index, completed: currentStep > index },
        ]"
        @click="currentStep > index && (currentStep = index as WizardStep)"
      >
        <span class="step-number">{{ index + 1 }}</span>
        <span class="step-label">{{ step.label }}</span>
      </div>
    </div>

    <div class="wizard-content">
      <div v-if="currentStep === 0" class="step-form zone-card">
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
          <label class="field-item" :class="{ invalid: !formData.faultDate }">
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
          <label class="field-item" :class="{ invalid: !formData.siteId }">
            <span>站点编号 / Site ID *</span>
            <base-input v-model="formData.siteId" placeholder="如：SITE-01" />
          </label>
          <label class="field-item" :class="{ invalid: !formData.system }">
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
      </div>

      <div v-if="currentStep === 1" class="step-form zone-card">
        <div class="section-heading">
          <h3>快填模式 / Quick Fill</h3>
          <p>
            可跳过此步骤直接进入正文编辑，也可填写简述后一键 AI 生成完整正文。
          </p>
        </div>
        <div class="zone-grid">
          <label class="field-item full-width">
            <span>事故简述 / Quick Narrative</span>
            <base-textarea
              v-model="formAnswers.quick_narrative"
              rows="4"
              placeholder="例如：3月12号下午3点客户下单报错，定位数据库 CPU 打满，3点半降级并加索引，4点恢复，后续加强 code review。"
            />
          </label>
          <label class="field-item full-width">
            <span>时间线 / Quick Timeline</span>
            <div class="timeline-list">
              <div
                v-for="(item, index) in quickTimelineItems"
                :key="index"
                class="timeline-row"
              >
                <base-input
                  :value="item.time"
                  placeholder="时间"
                  @input="onQuickTimelineInput(index, 'time', $event)"
                />
                <base-input
                  :value="item.event"
                  placeholder="发生了什么"
                  @input="onQuickTimelineInput(index, 'event', $event)"
                />
                <base-input
                  :value="item.resolution"
                  placeholder="如何处理"
                  @input="onQuickTimelineInput(index, 'resolution', $event)"
                />
                <base-button
                  type="button"
                  variant="danger"
                  size="sm"
                  @click="quickTimelineItems.splice(index, 1)"
                >
                  删除
                </base-button>
              </div>
            </div>
            <base-button
              type="button"
              variant="secondary"
              size="sm"
              @click="
                quickTimelineItems.push({ time: '', event: '', resolution: '' })
              "
            >
              新增时间线 / Add Timeline
            </base-button>
          </label>
          <label class="field-item">
            <span>影响范围 / Impact Scope</span>
            <base-input
              v-model="formAnswers.quick_impact_scope"
              placeholder="影响范围"
            />
          </label>
          <label class="field-item">
            <span>严重级别 / Impact Severity</span>
            <base-input
              v-model="formAnswers.quick_impact_severity"
              placeholder="严重级别"
            />
          </label>
          <label class="field-item full-width">
            <span>根因推测 / Root Cause Guess</span>
            <base-textarea
              v-model="formAnswers.quick_root_cause_guess"
              rows="2"
              placeholder="根因推测..."
            />
          </label>
          <label class="field-item full-width">
            <span>后续动作 / Follow-up Action</span>
            <base-textarea
              v-model="formAnswers.quick_follow_up_action"
              rows="2"
              placeholder="后续动作..."
            />
          </label>
        </div>
      </div>

      <div v-if="currentStep === 2" class="step-form zone-card">
        <div class="section-heading">
          <h3>AI 正文 / AI Body</h3>
          <p>可由快填自动填充，也可逐段使用 AI 生成或手动编辑。</p>
        </div>

        <div class="section-card">
          <div class="section-header">
            <h4>事故简述 / Incident Summary *</h4>
            <base-button
              type="button"
              variant="ghost"
              size="sm"
              :disabled="generating"
              @click="handleSectionGenerate('description')"
            >
              AI 生成
            </base-button>
          </div>
          <base-textarea
            v-model="formAnswers.body_description"
            rows="4"
            placeholder="请描述事故概况..."
          />
        </div>

        <div class="section-card">
          <div class="section-header">
            <h4>时间线 / Timeline *</h4>
            <base-button
              type="button"
              variant="ghost"
              size="sm"
              :disabled="generating"
              @click="handleSectionGenerate('timeline')"
            >
              AI 生成
            </base-button>
          </div>
          <div class="timeline-list">
            <div
              v-for="(item, index) in bodyTimelineItems"
              :key="index"
              class="timeline-row"
            >
              <base-date-time-picker
                mode="time"
                placeholder="时间"
                :model-value="item.time"
                @update:model-value="
                  onBodyTimelineChange(index, 'time', $event)
                "
              />
              <base-input
                :value="item.event"
                placeholder="发生了什么"
                @input="onBodyTimelineInput(index, 'event', $event)"
              />
              <base-input
                :value="item.resolution"
                placeholder="如何处理"
                @input="onBodyTimelineInput(index, 'resolution', $event)"
              />
              <base-button
                type="button"
                variant="danger"
                size="sm"
                @click="bodyTimelineItems.splice(index, 1)"
              >
                删除
              </base-button>
            </div>
          </div>
          <base-button
            type="button"
            variant="secondary"
            size="sm"
            @click="
              bodyTimelineItems.push({ time: '', event: '', resolution: '' })
            "
          >
            新增时间线 / Add Timeline
          </base-button>
        </div>

        <div class="section-card">
          <div class="section-header">
            <h4>影响范围 / 严重级别 / Impact & Severity *</h4>
            <base-button
              type="button"
              variant="ghost"
              size="sm"
              :disabled="generating"
              @click="handleSectionGenerate('impact')"
            >
              AI 生成
            </base-button>
          </div>
          <div class="zone-grid two-column">
            <label class="field-item">
              <span>影响范围 / Impact Scope *</span>
              <base-input
                v-model="formAnswers.body_impact_scope"
                placeholder="影响范围"
              />
            </label>
            <label class="field-item">
              <span>严重级别 / Impact Severity *</span>
              <base-input
                v-model="formAnswers.body_impact_severity"
                placeholder="严重级别"
              />
            </label>
            <label class="field-item full-width">
              <span>业务影响 / Business Impact</span>
              <base-textarea
                v-model="formAnswers.body_business_impact"
                rows="2"
                placeholder="业务影响描述..."
              />
            </label>
          </div>
        </div>

        <div class="section-card">
          <div class="section-header">
            <h4>根因分析 / Root Cause *</h4>
            <base-button
              type="button"
              variant="ghost"
              size="sm"
              :disabled="generating"
              @click="handleSectionGenerate('root_cause')"
            >
              AI 生成
            </base-button>
          </div>
          <div class="zone-grid">
            <label class="field-item">
              <span>触发原因 / Trigger</span>
              <base-input
                v-model="formAnswers.body_trigger"
                placeholder="触发原因"
              />
            </label>
            <label class="field-item full-width">
              <span>根因 / Root Cause *</span>
              <base-textarea
                v-model="formAnswers.body_root_cause"
                rows="3"
                placeholder="根因分析..."
              />
            </label>
          </div>
        </div>

        <div class="section-card">
          <div class="section-header">
            <h4>后续动作 / Follow-Up Actions *</h4>
            <base-button
              type="button"
              variant="ghost"
              size="sm"
              :disabled="generating"
              @click="handleSectionGenerate('follow_up')"
            >
              AI 生成
            </base-button>
          </div>
          <base-textarea
            v-model="formAnswers.body_follow_up"
            rows="4"
            placeholder="后续动作计划..."
          />
        </div>

        <div v-if="generationError" class="error-hint">
          {{ generationError }}
        </div>
      </div>

      <div v-if="currentStep === 3" class="step-form zone-card">
        <div class="section-heading">
          <h3>附录 / Appendix</h3>
          <p>支持文本输入，附加信息将在生成文档时同步写入附录页。</p>
        </div>
        <div class="zone-grid">
          <label class="field-item full-width">
            <span>附录内容 / Appendix Notes</span>
            <base-textarea
              v-model="formAnswers.appendix_notes"
              rows="6"
              placeholder="请输入附录内容..."
            />
          </label>
        </div>
      </div>

      <div v-if="currentStep === 4" class="step-form zone-card">
        <div class="section-heading">
          <h3>预览附件 / Preview Attachment</h3>
          <p>点击生成预览后，可使用 PDF 浏览器查看文档。</p>
        </div>
        <div class="preview-actions">
          <base-button
            type="button"
            variant="primary"
            :disabled="previewing"
            @click="handleGeneratePreview"
          >
            {{ previewing ? '生成中...' : '生成预览 / Generate Preview' }}
          </base-button>
          <base-button
            v-if="previewData?.pdfBase64"
            type="button"
            variant="secondary"
            @click="openPdfPreview"
          >
            在 PDF 浏览器中查看 / View PDF
          </base-button>
          <base-button
            v-if="previewData?.docxBase64"
            type="button"
            variant="secondary"
            @click="downloadDocx"
          >
            下载 DOCX / Download
          </base-button>
        </div>
        <div v-if="previewData?.html" class="preview-html-container">
          <div v-safe-html="previewData.html" class="preview-html"></div>
        </div>
        <div v-if="previewData?.warnings?.length" class="preview-warnings">
          <p v-for="w in previewData.warnings" :key="w" class="warning-hint">
            {{ w }}
          </p>
        </div>
      </div>
    </div>

    <div class="wizard-actions">
      <base-button
        variant="secondary"
        :disabled="saving"
        @click="handleSaveDraft"
      >
        保存草稿 / Save Draft
      </base-button>
      <div class="wizard-nav">
        <base-button
          v-if="currentStep > 0"
          variant="ghost"
          @click="currentStep--"
        >
          上一步 / Previous
        </base-button>
        <base-button
          v-if="currentStep < WIZARD_STEPS.length - 1"
          variant="primary"
          class="wizard-btn-next"
          @click="handleNextStep"
        >
          下一步 / Next
        </base-button>
        <base-button
          v-if="currentStep === WIZARD_STEPS.length - 1"
          variant="primary"
          class="wizard-btn-submit"
          :disabled="!formData.title.trim() || submitting"
          @click="handleSubmit"
        >
          提交报告 / Submit
        </base-button>
      </div>
    </div>

    <ai-generating-modal
      :visible="generating || previewing"
      :label="generatingLabel"
      @stop="handleStopGeneration"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue';
import { useRouter } from 'vue-router';
import { useAppStore } from '../../../stores/app';
import { useReportWizard, WIZARD_STEPS } from './composables/useReportWizard';
import type { WizardStep } from './composables/useReportWizard';
import AiGeneratingModal from '../../../components/business/AiGeneratingModal.vue';
import BaseButton from '../../../components/base/BaseButton.vue';
import BaseInput from '../../../components/base/BaseInput.vue';
import BaseTextarea from '../../../components/base/BaseTextarea.vue';
import BaseDropdown from '../../../components/base/BaseDropdown.vue';
import BaseDateTimePicker from '../../../components/base/BaseDateTimePicker.vue';

const router = useRouter();

const {
  currentStep,
  saving,
  submitting,
  generating,
  previewing,
  reportId,
  previewData,
  generationError,
  saveAsDraft,
  createAndSubmit,
  quickGenerate,
  generateSection,
  generatePreview,
  applyGenerationResult,
} = useReportWizard();

let abortController: AbortController | null = null;

const appStore = useAppStore();

const generatingLabel = computed(() => {
  if (previewing.value) return '正在生成预览';
  return 'AI 正在生成';
});

const handleStopGeneration = () => {
  if (abortController) {
    abortController.abort();
    abortController = null;
  }
};

interface TimelineItem {
  time: string;
  event: string;
  resolution: string;
}

const formData = ref({
  title: '',
  severity: '',
  system: '',
  siteId: '',
  faultDate: '',
});

const formAnswers = ref<Record<string, string>>({
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
  quick_impact_scope: '',
  quick_impact_severity: '',
  quick_root_cause_guess: '',
  quick_follow_up_action: '',
  body_description: '',
  body_impact_scope: '',
  body_impact_severity: '',
  body_business_impact: '',
  body_trigger: '',
  body_root_cause: '',
  body_follow_up: '',
  appendix_notes: '',
});

const quickTimelineItems = ref<TimelineItem[]>([]);
const bodyTimelineItems = ref<TimelineItem[]>([
  { time: '', event: '', resolution: '' },
]);

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

watch(
  quickTimelineItems,
  (items) => {
    formAnswers.value.quick_timeline = JSON.stringify(items);
  },
  { deep: true },
);

watch(
  bodyTimelineItems,
  (items) => {
    formAnswers.value.body_timeline = JSON.stringify(items);
  },
  { deep: true },
);

const onQuickTimelineInput = (
  index: number,
  key: keyof TimelineItem,
  event: Event,
) => {
  const value = (event.target as HTMLInputElement).value;
  if (quickTimelineItems.value[index]) {
    quickTimelineItems.value[index][key] = value;
  }
};

const onBodyTimelineChange = (
  index: number,
  key: keyof TimelineItem,
  value: string,
) => {
  if (bodyTimelineItems.value[index]) {
    bodyTimelineItems.value[index][key] = value;
  }
};

const onBodyTimelineInput = (
  index: number,
  key: keyof TimelineItem,
  event: Event,
) => {
  const value = (event.target as HTMLInputElement).value;
  onBodyTimelineChange(index, key, value);
};

const buildFormPayload = () => {
  const formDataPayload: Record<string, unknown> = { ...formAnswers.value };
  formDataPayload.body_timeline = bodyTimelineItems.value;
  formDataPayload.quick_timeline = quickTimelineItems.value;
  return {
    title: formData.value.title,
    severity: formData.value.severity || undefined,
    system: formData.value.system || undefined,
    siteId: formData.value.siteId || undefined,
    faultDate: formData.value.faultDate || undefined,
    formData: formDataPayload,
  };
};

const handleNextStep = async () => {
  if (currentStep.value === 0) {
    if (!formData.value.title.trim()) return;
  }

  if (currentStep.value === 1 && formAnswers.value.quick_narrative.trim()) {
    try {
      abortController = new AbortController();
      const result = await quickGenerate(buildFormPayload(), {
        model: appStore.selectedModel,
        rerankerModel: appStore.selectedRerankerModel,
        signal: abortController.signal,
      });
      applyGenerationResult(result, formAnswers.value);
      if (result.formAnswers.bodyTimeline) {
        const timeline = result.formAnswers.bodyTimeline.value;
        if (Array.isArray(timeline)) {
          bodyTimelineItems.value = timeline.map(
            (item: Record<string, string>) => ({
              time: item.time || '',
              event: item.event || '',
              resolution: item.resolution || '',
            }),
          );
        }
      }
      currentStep.value = 2 as WizardStep;
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') return;
    } finally {
      abortController = null;
    }
    return;
  }

  if (currentStep.value < WIZARD_STEPS.length - 1) {
    currentStep.value = (currentStep.value + 1) as WizardStep;
  }
};

const handleSaveDraft = async () => {
  if (!formData.value.title.trim()) return;
  saving.value = true;
  try {
    const report = await saveAsDraft(buildFormPayload());
    if (!reportId.value) {
      router.push(`/incident-report/${report.id}`);
    }
  } finally {
    saving.value = false;
  }
};

const handleSubmit = async () => {
  if (!formData.value.title.trim()) return;
  submitting.value = true;
  try {
    const report = await createAndSubmit(buildFormPayload());
    router.push(`/incident-report/${report.id}`);
  } finally {
    submitting.value = false;
  }
};

const handleSectionGenerate = async (sectionId: string) => {
  if (generating.value) return;
  try {
    abortController = new AbortController();
    generating.value = true;
    await saveAsDraft(buildFormPayload());
    const result = await generateSection(sectionId, {
      signal: abortController.signal,
    });
    applyGenerationResult(result, formAnswers.value);
    if (sectionId === 'timeline' && result.formAnswers.bodyTimeline) {
      const timeline = result.formAnswers.bodyTimeline.value;
      if (Array.isArray(timeline)) {
        bodyTimelineItems.value = timeline.map(
          (item: Record<string, string>) => ({
            time: item.time || '',
            event: item.event || '',
            resolution: item.resolution || '',
          }),
        );
      }
    }
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') return;
    throw err;
  } finally {
    abortController = null;
  }
};

const handleGeneratePreview = async () => {
  try {
    abortController = new AbortController();
    await saveAsDraft(buildFormPayload());
    await generatePreview({ signal: abortController.signal });
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') return;
    throw err;
  } finally {
    abortController = null;
  }
};

const openPdfPreview = () => {
  if (!previewData.value?.pdfBase64) return;
  const binaryString = atob(previewData.value.pdfBase64);
  const bytes = new Uint8Array(binaryString.length);
  for (let i = 0; i < binaryString.length; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }
  const blob = new Blob([bytes], { type: 'application/pdf' });
  const url = URL.createObjectURL(blob);
  window.open(url, '_blank');
};

const downloadDocx = () => {
  if (!previewData.value?.docxBase64 || !previewData.value?.docxFileName)
    return;
  const binaryString = atob(previewData.value.docxBase64);
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
  link.download = previewData.value.docxFileName;
  link.click();
  URL.revokeObjectURL(url);
};
</script>

<style scoped src="./styles/incident-report-create.css"></style>
