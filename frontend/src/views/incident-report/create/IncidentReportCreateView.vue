<template>
  <div class="incident-report-create-view">
    <div class="create-header">
      <base-button variant="ghost" size="sm" @click="router.push('/incident-report')">
        ← 返回列表
      </base-button>
      <h1>新建事故报告</h1>
    </div>

    <div class="wizard-steps">
      <div
        v-for="(step, index) in steps"
        :key="step.key"
        :class="['wizard-step', { active: currentStep === index, completed: currentStep > index }]"
        @click="currentStep > index && (currentStep = index)"
      >
        <span class="step-number">{{ index + 1 }}</span>
        <span class="step-label">{{ step.label }}</span>
      </div>
    </div>

    <div class="wizard-content">
      <div v-if="currentStep === 0" class="step-form">
        <div class="form-group">
          <label class="form-label">报告标题 *</label>
          <base-input v-model="formData.title" placeholder="请输入报告标题" />
        </div>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">严重级别</label>
            <base-dropdown v-model="formData.severity" :options="severityOptions" placeholder="选择级别" />
          </div>
          <div class="form-group">
            <label class="form-label">所属系统</label>
            <base-input v-model="formData.system" placeholder="如：数据库系统" />
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">站点编号</label>
            <base-input v-model="formData.site_id" placeholder="如：SITE-01" />
          </div>
          <div class="form-group">
            <label class="form-label">故障日期</label>
            <base-input v-model="formData.fault_date" placeholder="YYYY-MM-DD" />
          </div>
        </div>
      </div>

      <div v-if="currentStep === 1" class="step-form">
        <div class="form-group">
          <label class="form-label">事故描述</label>
          <base-textarea v-model="formData.description" placeholder="请详细描述事故情况..." />
        </div>
      </div>

      <div v-if="currentStep === 2" class="step-form">
        <div class="form-group">
          <label class="form-label">时间线</label>
          <base-textarea v-model="formData.timeline" placeholder="记录事故发生的时间线..." />
        </div>
      </div>

      <div v-if="currentStep === 3" class="step-form">
        <div class="form-group">
          <label class="form-label">附录</label>
          <base-textarea v-model="formData.appendix" placeholder="附加信息..." />
        </div>
      </div>

      <div v-if="currentStep === 4" class="step-preview">
        <h3>预览并提交</h3>
        <div class="preview-summary">
          <div class="preview-row"><span>标题：</span><span>{{ formData.title }}</span></div>
          <div class="preview-row"><span>级别：</span><span>{{ formData.severity || '-' }}</span></div>
          <div class="preview-row"><span>系统：</span><span>{{ formData.system || '-' }}</span></div>
          <div class="preview-row"><span>站点：</span><span>{{ formData.site_id || '-' }}</span></div>
          <div class="preview-row"><span>故障日期：</span><span>{{ formData.fault_date || '-' }}</span></div>
        </div>
      </div>
    </div>

    <div class="wizard-actions">
      <base-button variant="secondary" @click="handleSaveDraft" :disabled="saving">
        保存草稿
      </base-button>
      <div class="wizard-nav">
        <base-button v-if="currentStep > 0" variant="ghost" @click="currentStep--">
          上一步
        </base-button>
        <base-button
          v-if="currentStep < steps.length - 1"
          variant="primary"
          class="wizard-btn-next"
          @click="currentStep++"
        >
          下一步
        </base-button>
        <base-button
          v-if="currentStep === steps.length - 1"
          variant="primary"
          class="wizard-btn-submit"
          :disabled="!formData.title.trim() || submitting"
          @click="handleSubmit"
        >
          提交报告
        </base-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { createIncidentReport, submitIncidentReport } from '../../../api/incident-report';
import BaseButton from '../../../components/base/BaseButton.vue';
import BaseInput from '../../../components/base/BaseInput.vue';
import BaseDropdown from '../../../components/base/BaseDropdown.vue';
import BaseTextarea from '../../../components/base/BaseTextarea.vue';

const router = useRouter();

const steps = [
  { key: 'basic', label: '基本信息' },
  { key: 'description', label: '事故描述' },
  { key: 'timeline', label: '时间线' },
  { key: 'appendix', label: '附录' },
  { key: 'preview', label: '预览提交' },
];

const currentStep = ref(0);
const saving = ref(false);
const submitting = ref(false);

const formData = ref({
  title: '',
  severity: '',
  system: '',
  site_id: '',
  fault_date: '',
  description: '',
  timeline: '',
  appendix: '',
});

const severityOptions = [
  { value: '', label: '请选择' },
  { value: 'P0', label: 'P0 - 紧急' },
  { value: 'P1', label: 'P1 - 严重' },
  { value: 'P2', label: 'P2 - 一般' },
  { value: 'P3', label: 'P3 - 轻微' },
];

const buildFormPayload = () => ({
  title: formData.value.title,
  severity: formData.value.severity || undefined,
  system: formData.value.system || undefined,
  site_id: formData.value.site_id || undefined,
  fault_date: formData.value.fault_date || undefined,
  form_data: {
    description: formData.value.description,
    timeline: formData.value.timeline,
    appendix: formData.value.appendix,
  },
});

const handleSaveDraft = async () => {
  if (!formData.value.title.trim()) return;
  saving.value = true;
  try {
    const report = await createIncidentReport(buildFormPayload());
    router.push(`/incident-report/${report.id}`);
  } finally {
    saving.value = false;
  }
};

const handleSubmit = async () => {
  if (!formData.value.title.trim()) return;
  submitting.value = true;
  try {
    const report = await createIncidentReport(buildFormPayload());
    await submitIncidentReport(report.id);
    router.push(`/incident-report/${report.id}`);
  } finally {
    submitting.value = false;
  }
};

onMounted(() => {});
</script>

<style scoped src="./styles/incident-report-create.css"></style>
