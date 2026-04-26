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
        <h1>编辑报告 - {{ report.ref_no }}</h1>
      </div>

      <div class="edit-form">
        <div class="form-group">
          <label class="form-label">报告标题 *</label>
          <base-input v-model="formData.title" placeholder="请输入报告标题" />
        </div>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">严重级别</label>
            <base-dropdown
              v-model="formData.severity"
              :options="severityOptions"
              placeholder="选择级别"
            />
          </div>
          <div class="form-group">
            <label class="form-label">所属系统</label>
            <base-input
              v-model="formData.system"
              placeholder="如：数据库系统"
            />
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">站点编号</label>
            <base-input v-model="formData.site_id" placeholder="如：SITE-01" />
          </div>
          <div class="form-group">
            <label class="form-label">故障日期</label>
            <base-input
              v-model="formData.fault_date"
              placeholder="YYYY-MM-DD"
            />
          </div>
        </div>
        <div class="form-group">
          <label class="form-label">事故描述</label>
          <base-textarea
            v-model="formData.description"
            placeholder="请详细描述事故情况..."
          />
        </div>
      </div>

      <div class="edit-actions">
        <base-button
          variant="secondary"
          @click="router.push(`/incident-report/${report.id}`)"
        >
          取消
        </base-button>
        <base-button
          variant="primary"
          :disabled="!formData.title.trim() || saving"
          @click="handleSave"
        >
          {{ saving ? '保存中...' : '保存' }}
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
} from '../../../api/incident-report';
import type { IncidentReportDetailItem } from '../../../types/incident-report/incident-report';
import BaseButton from '../../../components/base/BaseButton.vue';
import BaseInput from '../../../components/base/BaseInput.vue';
import BaseDropdown from '../../../components/base/BaseDropdown.vue';
import BaseTextarea from '../../../components/base/BaseTextarea.vue';

const route = useRoute();
const router = useRouter();

const report = ref<IncidentReportDetailItem | null>(null);
const loading = ref(true);
const saving = ref(false);

const formData = ref({
  title: '',
  severity: '',
  system: '',
  site_id: '',
  fault_date: '',
  description: '',
});

const severityOptions = [
  { value: '', label: '请选择' },
  { value: 'P0', label: 'P0 - 紧急' },
  { value: 'P1', label: 'P1 - 严重' },
  { value: 'P2', label: 'P2 - 一般' },
  { value: 'P3', label: 'P3 - 轻微' },
];

const handleSave = async () => {
  if (!report.value || !formData.value.title.trim()) return;
  saving.value = true;
  try {
    await updateIncidentReport(report.value.id, {
      title: formData.value.title,
      severity: formData.value.severity || undefined,
      system: formData.value.system || undefined,
      site_id: formData.value.site_id || undefined,
      fault_date: formData.value.fault_date || undefined,
      form_data: {
        ...(report.value.form_data || {}),
        description: formData.value.description,
      },
    });
    router.push(`/incident-report/${report.value.id}`);
  } finally {
    saving.value = false;
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
      site_id: data.site_id ?? '',
      fault_date: data.fault_date ?? '',
      description: (data.form_data?.description as string) ?? '',
    };
  } finally {
    loading.value = false;
  }
});
</script>

<style scoped>
.incident-report-edit-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 24px;
  max-width: 800px;
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
}

.edit-form {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-secondary);
}

.form-row {
  display: flex;
  gap: 16px;
}

.form-row .form-group {
  flex: 1;
}

.edit-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding-top: 20px;
  border-top: 1px solid var(--color-border);
  margin-top: 20px;
}
</style>
