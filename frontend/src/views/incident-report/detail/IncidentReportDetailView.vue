<template>
  <section class="incident-report-detail-view">
    <div v-if="loading" class="detail-loading">加载中...</div>
    <div v-else-if="!report" class="detail-empty">报告不存在</div>
    <template v-else>
      <div class="detail-header">
        <div class="detail-header-left">
          <base-button
            variant="ghost"
            size="sm"
            @click="router.push('/incident-report')"
          >
            <svg
              viewBox="0 0 20 20"
              width="16"
              height="16"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M12.5 15L7.5 10L12.5 5" />
            </svg>
            返回列表
          </base-button>
          <span class="detail-ref">{{ report.refNo }}</span>
          <span class="detail-title">{{ report.title }}</span>
        </div>
        <div class="detail-header-right">
          <base-button
            variant="ghost"
            size="sm"
            :disabled="downloadingDocx"
            @click="handleDownloadDocx"
          >
            <svg
              viewBox="0 0 20 20"
              width="14"
              height="14"
              fill="none"
              stroke="currentColor"
              stroke-width="1.5"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M10 3V13M10 13L6.5 9.5M10 13L13.5 9.5M3 16H17" />
            </svg>
            {{ downloadingDocx ? '生成中...' : '下载 Word' }}
          </base-button>
          <base-button
            v-if="canEdit"
            variant="secondary"
            size="sm"
            @click="router.push(`/incident-report/${report.id}/edit`)"
          >
            <svg
              viewBox="0 0 20 20"
              width="14"
              height="14"
              fill="none"
              stroke="currentColor"
              stroke-width="1.5"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M13.5 3.5L16.5 6.5L7 16H4V13L13.5 3.5z" />
            </svg>
            编辑
          </base-button>
          <base-button
            v-if="canSubmit"
            variant="primary"
            size="sm"
            @click="showSubmitConfirm = true"
          >
            <svg
              viewBox="0 0 20 20"
              width="14"
              height="14"
              fill="none"
              stroke="currentColor"
              stroke-width="1.5"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M5 10L9 14L16 5" />
            </svg>
            提交审核
          </base-button>
          <base-button
            v-if="canAudit"
            variant="primary"
            size="sm"
            @click="showAuditDialog = true"
          >
            <svg
              viewBox="0 0 20 20"
              width="14"
              height="14"
              fill="none"
              stroke="currentColor"
              stroke-width="1.5"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M10 4C5 4 2 10 2 10s3 6 8 6 8-6 8-6-3-6-8-6z" />
              <circle cx="10" cy="10" r="2.5" />
            </svg>
            审核
          </base-button>
          <base-button
            v-if="canAssign"
            variant="secondary"
            size="sm"
            @click="showAssignDialog = true"
          >
            <svg
              viewBox="0 0 20 20"
              width="14"
              height="14"
              fill="none"
              stroke="currentColor"
              stroke-width="1.5"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M16 10V16H4V10M10 4V12M7 7L10 4L13 7" />
            </svg>
            分配处理人
          </base-button>
          <base-button
            v-if="canClose"
            variant="danger"
            size="sm"
            @click="handleClose"
          >
            <svg
              viewBox="0 0 20 20"
              width="14"
              height="14"
              fill="none"
              stroke="currentColor"
              stroke-width="1.5"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <rect x="3" y="3" width="14" height="14" rx="2" />
              <path d="M3 7H17M7 3V7" />
            </svg>
            关闭
          </base-button>
          <base-button
            v-if="canReopen"
            variant="secondary"
            size="sm"
            @click="handleReopen"
          >
            <svg
              viewBox="0 0 20 20"
              width="14"
              height="14"
              fill="none"
              stroke="currentColor"
              stroke-width="1.5"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path
                d="M2.5 10A7.5 7.5 0 0 1 15 5.5M17.5 10A7.5 7.5 0 0 1 5 14.5"
              />
              <path d="M15 2V5.5H11.5M5 18V14.5H8.5" />
            </svg>
            重新打开
          </base-button>
        </div>
      </div>

      <div class="detail-body">
        <div class="detail-sidebar">
          <div class="detail-info-card">
            <h3>基本信息</h3>
            <div class="info-row">
              <span class="info-label">状态</span>
              <report-status-badge :status="report.status" />
            </div>
            <div class="info-row">
              <span class="info-label">级别</span>
              <span class="info-value">{{ report.severity ?? '-' }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">报告人</span>
              <span class="info-value">{{
                report.reporterName ?? report.reporterId
              }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">处理人</span>
              <span class="info-value">{{
                report.assigneeName ?? report.assigneeId ?? '-'
              }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">审核人</span>
              <span class="info-value">{{
                report.verifierName ?? report.verifierId ?? '-'
              }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">系统</span>
              <span class="info-value">{{ report.system ?? '-' }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">站点</span>
              <span class="info-value">{{ report.siteId ?? '-' }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">故障日期</span>
              <span class="info-value">{{
                formatDateTime(report.faultDate)
              }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">创建时间</span>
              <span class="info-value">{{
                formatDateTime(report.createdAt)
              }}</span>
            </div>
          </div>

          <report-audit-timeline :audit-logs="auditLogs" />
        </div>

        <div class="detail-content">
          <report-detail-content :report="report" />
          <report-comments
            :report-id="report.id"
            :comments="comments"
            @add-comment="handleAddComment"
          />
        </div>
      </div>
    </template>

    <base-confirm-dialog
      v-model="showSubmitConfirm"
      title="确认提交审核"
      message="确定要提交此报告进行审核吗？"
      confirm-text="提交"
      cancel-text="取消"
      confirm-variant="primary"
      @confirm="handleSubmitConfirm"
    />
    <base-confirm-dialog
      v-model="showAuditApproveConfirm"
      title="确认通过"
      message="确定要通过此报告吗？"
      confirm-text="通过"
      cancel-text="取消"
      confirm-variant="primary"
      @confirm="handleAuditApprove"
    />
    <base-confirm-dialog
      v-model="showAuditRejectConfirm"
      title="确认驳回"
      message="确定要驳回此报告吗？"
      confirm-text="驳回"
      cancel-text="取消"
      confirm-variant="danger"
      @confirm="handleAuditReject"
    />
    <base-confirm-dialog
      v-model="showAssignConfirm"
      title="确认分配"
      :message="`确定将此报告分配给 ${selectedAssigneeName} 吗？`"
      confirm-text="确定"
      cancel-text="取消"
      confirm-variant="primary"
      @confirm="handleAssignConfirm"
    />
    <base-confirm-dialog
      v-model="showCloseConfirm"
      title="确认关闭"
      message="确定要关闭此报告吗？"
      confirm-text="关闭"
      cancel-text="取消"
      confirm-variant="danger"
      @confirm="handleCloseConfirm"
    />
    <base-confirm-dialog
      v-model="showReopenConfirm"
      title="确认重新打开"
      message="确定要重新打开此报告吗？"
      confirm-text="重新打开"
      cancel-text="取消"
      confirm-variant="primary"
      @confirm="handleReopenConfirm"
    />

    <teleport to="body">
      <transition name="confirm-fade">
        <div
          v-if="showAuditDialog"
          class="audit-overlay"
          @click.self="showAuditDialog = false"
        >
          <div class="audit-dialog">
            <div class="audit-dialog-header">
              <h4>审核报告 - {{ report?.refNo }}</h4>
              <base-button
                variant="ghost"
                size="sm"
                @click="showAuditDialog = false"
              >
                <svg
                  viewBox="0 0 20 20"
                  width="16"
                  height="16"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                >
                  <path d="M5 5L15 15M15 5L5 15" />
                </svg>
              </base-button>
            </div>
            <div class="audit-dialog-body">
              <div class="form-group">
                <label class="form-label">审核意见 *</label>
                <base-textarea
                  v-model="auditComment"
                  placeholder="请输入审核意见..."
                />
              </div>
            </div>
            <div class="audit-dialog-footer">
              <base-button
                variant="danger"
                :disabled="!auditComment.trim()"
                @click="showAuditRejectConfirm = true"
              >
                <svg
                  viewBox="0 0 20 20"
                  width="14"
                  height="14"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                >
                  <path d="M5 5L15 15M15 5L5 15" />
                </svg>
                驳回
              </base-button>
              <base-button
                variant="primary"
                :disabled="!auditComment.trim()"
                @click="showAuditApproveConfirm = true"
              >
                <svg
                  viewBox="0 0 20 20"
                  width="14"
                  height="14"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <path d="M4 10.5L8 14.5L16 5.5" />
                </svg>
                通过
              </base-button>
            </div>
          </div>
        </div>
      </transition>
    </teleport>

    <teleport to="body">
      <transition name="confirm-fade">
        <div
          v-if="showAssignDialog"
          class="audit-overlay"
          @click.self="showAssignDialog = false"
        >
          <div class="audit-dialog">
            <div class="audit-dialog-header">
              <h4>分配处理人 - {{ report?.refNo }}</h4>
              <base-button
                variant="ghost"
                size="sm"
                @click="showAssignDialog = false"
              >
                <svg
                  viewBox="0 0 20 20"
                  width="16"
                  height="16"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                >
                  <path d="M5 5L15 15M15 5L5 15" />
                </svg>
              </base-button>
            </div>
            <div class="audit-dialog-body">
              <div class="form-group">
                <label class="form-label">选择处理人 *</label>
                <base-dropdown
                  v-model="selectedAssigneeId"
                  :options="handlerOptions"
                  placeholder="请选择处理人"
                />
              </div>
            </div>
            <div class="audit-dialog-footer">
              <base-button
                variant="secondary"
                size="sm"
                @click="showAssignDialog = false"
              >
                取消
              </base-button>
              <base-button
                variant="primary"
                :disabled="!selectedAssigneeId"
                @click="showAssignConfirm = true"
              >
                确认分配
              </base-button>
            </div>
          </div>
        </div>
      </transition>
    </teleport>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useIncidentReportStore } from '../../../stores/incident-report';
import { useAuthStore } from '../../../stores/auth';
import { useReportDetail } from './composables/useReportDetail';
import {
  fetchIncidentReportComments,
  createIncidentReportComment,
  closeIncidentReport,
  reopenIncidentReport,
  previewIncidentReport,
  approveIncidentReport,
  rejectIncidentReport,
  assignIncidentReport,
  fetchUsersWithRoles,
  submitIncidentReport,
} from '../../../api/incident-report';
import type { IncidentCommentEntry } from '../../../types/incident-report/incident-report';
import BaseButton from '../../../components/base/BaseButton.vue';
import BaseTextarea from '../../../components/base/BaseTextarea.vue';
import BaseConfirmDialog from '../../../components/base/BaseConfirmDialog.vue';
import BaseDropdown from '../../../components/base/BaseDropdown.vue';
import ReportStatusBadge from '../components/ReportStatusBadge.vue';
import ReportAuditTimeline from './components/ReportAuditTimeline.vue';
import ReportDetailContent from './components/ReportDetailContent.vue';
import ReportComments from './components/ReportComments.vue';
import { formatDateTime } from '../../../utils/common/date';

const route = useRoute();
const router = useRouter();
const store = useIncidentReportStore();
const authStore = useAuthStore();

const {
  report,
  auditLogs,
  loading,
  load: loadDetail,
  refreshLogs,
} = useReportDetail();
const comments = ref<IncidentCommentEntry[]>([]);
const downloadingDocx = ref(false);
const showSubmitConfirm = ref(false);
const showAuditDialog = ref(false);
const auditComment = ref('');
const showAuditApproveConfirm = ref(false);
const showAuditRejectConfirm = ref(false);
const showAssignDialog = ref(false);
const showAssignConfirm = ref(false);
const showCloseConfirm = ref(false);
const showReopenConfirm = ref(false);
const selectedAssigneeId = ref('');
const handlerUsers = ref<{ userId: string; username: string }[]>([]);

const handlerOptions = computed(() =>
  handlerUsers.value.map((u) => ({ value: u.userId, label: u.username })),
);

const selectedAssigneeName = computed(() => {
  const user = handlerUsers.value.find(
    (u) => u.userId === selectedAssigneeId.value,
  );
  return user?.username ?? '';
});

const canEdit = computed(() => {
  if (!report.value) return false;
  const s = report.value.status;
  if (s !== 'draft' && s !== 'rejected') return false;
  if (
    report.value.reporterId === authStore.userId &&
    store.hasPermission('report:edit_own')
  )
    return true;
  return (
    store.hasPermission('report:edit_assigned') ||
    store.hasPermission('report:edit_all')
  );
});

const canSubmit = computed(() => {
  if (!report.value) return false;
  const s = report.value.status;
  if (s !== 'draft' && s !== 'rejected') return false;
  return store.hasPermission('report:submit');
});

const canAudit = computed(() => {
  if (!report.value) return false;
  return report.value.status === 'pending' && store.canAudit;
});

const canAssign = computed(() => {
  if (!report.value) return false;
  return (
    (report.value.status === 'approved' ||
      report.value.status === 'in_progress') &&
    store.hasPermission('report:assign')
  );
});

const canClose = computed(() => {
  if (!report.value) return false;
  return (
    report.value.status === 'in_progress' &&
    store.hasPermission('report:close_assigned')
  );
});

const canReopen = computed(() => {
  if (!report.value) return false;
  return report.value.status === 'closed' && store.canReopenReport;
});

const handleClose = () => {
  showCloseConfirm.value = true;
};

const handleCloseConfirm = async () => {
  if (!report.value) return;
  report.value = await closeIncidentReport(report.value.id);
  refreshLogs(report.value.id);
};

const handleReopen = () => {
  showReopenConfirm.value = true;
};

const handleReopenConfirm = async () => {
  if (!report.value) return;
  report.value = await reopenIncidentReport(report.value.id);
  refreshLogs(report.value.id);
};

const handleSubmitConfirm = async () => {
  if (!report.value) return;
  try {
    report.value = await submitIncidentReport(report.value.id);
    refreshLogs(report.value.id);
  } catch {
    // API error handled by interceptor
  }
};

const handleAuditApprove = async () => {
  if (!report.value || !auditComment.value.trim()) return;
  try {
    report.value = await approveIncidentReport(
      report.value.id,
      auditComment.value,
    );
    refreshLogs(report.value.id);
    showAuditDialog.value = false;
    auditComment.value = '';
  } catch {
    // API error handled by interceptor
  }
};

const handleAuditReject = async () => {
  if (!report.value || !auditComment.value.trim()) return;
  try {
    report.value = await rejectIncidentReport(
      report.value.id,
      auditComment.value,
    );
    refreshLogs(report.value.id);
    showAuditDialog.value = false;
    auditComment.value = '';
  } catch {
    // API error handled by interceptor
  }
};

const handleAssignConfirm = async () => {
  if (!report.value || !selectedAssigneeId.value) return;
  try {
    report.value = await assignIncidentReport(
      report.value.id,
      selectedAssigneeId.value,
    );
    refreshLogs(report.value.id);
    showAssignDialog.value = false;
    selectedAssigneeId.value = '';
  } catch {
    // API error handled by interceptor
  }
};

const loadHandlerUsers = async () => {
  if (handlerUsers.value.length > 0) return;
  try {
    const data = await fetchUsersWithRoles();
    handlerUsers.value = (data.items ?? [])
      .filter((u) => u.roles.includes('handler'))
      .map((u) => ({ userId: u.userId, username: u.username }));
  } catch {
    // API error handled by interceptor
  }
};

const handleAddComment = async (content: string) => {
  if (!report.value) return;
  const comment = await createIncidentReportComment(report.value.id, {
    content,
  });
  comments.value.push(comment);
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
  await store.loadUserIncidentRoles();
  try {
    const [commentData] = await Promise.all([
      fetchIncidentReportComments(reportId),
      loadDetail(reportId),
    ]);
    comments.value = commentData;
  } catch {
    // loadDetail sets report to null on failure, UI shows "报告不存在"
  }
});

watch(showAssignDialog, (val) => {
  if (val) loadHandlerUsers();
});
</script>

<style scoped src="./styles/incident-report-detail.css"></style>
