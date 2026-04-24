<template>
  <div class="incident-report-page">
    <div class="incident-report-page-body">
      <SessionSidebar
        :sessions="incidentReportStore.incidentReportSidebarSessions"
        :active-session-id="incidentReportStore.activeIncidentReportSessionId"
        :is-locked="incidentReportStore.isIncidentReportGenerating"
        :group-by-created-at="true"
        @load-session="onLoadSession"
        @rename-session="onRenameSession"
        @delete-session="onDeleteSession"
      />
      <div class="incident-report-main">
        <IncidentReportWorkspace
          :schema="incidentReportStore.incidentReportSchema"
          :session="incidentReportStore.activeIncidentReportSession"
          :is-generating="incidentReportStore.isIncidentReportGenerating"
          :generation-state="incidentReportStore.generationState"
          :generation-task="incidentReportStore.generationTask"
          :preview-html="incidentReportStore.incidentReportPreviewHtml"
          :preview-pdf-base64="
            incidentReportStore.incidentReportPreviewPdfBase64
          "
          :preview-docx-base64="
            incidentReportStore.incidentReportPreviewDocxBase64
          "
          :preview-loading="incidentReportStore.incidentReportPreviewLoading"
          :preview-error="incidentReportStore.incidentReportPreviewError"
          @start="onStartIncidentReport"
          @update-answers="onIncidentReportAnswersUpdate"
          @quick-generate-body="onIncidentReportQuickGenerateBody"
          @generate-section="onIncidentReportGenerateSection"
          @download-preview-docx="onIncidentReportDownloadPreviewDocx"
          @open-trace="onIncidentReportOpenTrace"
          @stop-generation="onIncidentReportStopGeneration"
          @request-preview="onIncidentReportRequestPreview"
          @cancel-preview="onIncidentReportCancelPreview"
        />
      </div>
    </div>
    <FloatingToast
      :visible="isCopyToastVisible"
      :title="copyToastTitle"
      :message="copyToastMessage"
    />
    <TraceReplayModal
      :visible="isTraceModalVisible"
      :trace-id="activeTraceId"
      :loading="isTraceModalLoading"
      :error-message="traceModalErrorMessage"
      :payload="activeTracePayload"
      @close="closeTraceModal"
      @retry="onTraceModalRetry"
      @copy-trace-id="copyTraceId"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useAppStore } from '../../stores/app';
import { useIncidentReportStore } from '../../stores/incident-report';
import { useCatalogLoader } from '../../composables/business/useCatalogLoader';
import { useCopyToast } from '../../composables/business/useCopyToast';
import { useIncidentReportSessions } from './composables/useIncidentReportSessions';
import { useTraceModal } from '../../composables/business/useTraceModal';
import type { IncidentReportFormAnswer } from '../../types/incident-report/incident-report';
import { getErrorMessage } from '../../utils/common/error';
import FloatingToast from '../../components/business/FloatingToast.vue';
import SessionSidebar from '../../components/business/SessionSidebar.vue';
import TraceReplayModal from '../../components/business/TraceReplayModal.vue';
import IncidentReportWorkspace from './components/IncidentReportWorkspace.vue';

const appStore = useAppStore();
const incidentReportStore = useIncidentReportStore();
const router = useRouter();

const { copyToastMessage, copyToastTitle, isCopyToastVisible, showCopyToast } =
  useCopyToast();

const {
  cancelIncidentReportPreview,
  clearActiveIncidentReportSession,
  deleteIncidentReport,
  downloadIncidentReportPreviewDocx,
  flushSaveIncidentReportSnapshot,
  generateBodySection,
  loadIncidentReportPreview,
  quickGenerateBody,
  loadIncidentReportSchema,
  loadIncidentReportSession,
  loadIncidentReportSessionSummaries,
  renameIncidentReport,
  startIncidentReportSession,
  stopIncidentReportGeneration,
  updateIncidentReportAnswers,
} = useIncidentReportSessions();

const {
  isTraceModalVisible,
  activeTraceId,
  isTraceModalLoading,
  traceModalErrorMessage,
  activeTracePayload,
  openTraceModalByTraceId,
  closeTraceModal,
  retryTraceModalLoad,
  copyTraceId,
} = useTraceModal({ showCopyToast });

const onLoadSession = async (sessionId: string) => {
  await loadIncidentReportSession(sessionId);
};

const onRenameSession = async (payload: {
  sessionId: string;
  title: string;
}) => {
  await renameIncidentReport(payload.sessionId, payload.title);
};

const onDeleteSession = async (sessionId: string) => {
  await deleteIncidentReport(sessionId);
};

const onStartIncidentReport = async () => {
  await startIncidentReportSession();
};

const onHeaderTitleClick = async () => {
  try {
    await flushSaveIncidentReportSnapshot();
  } catch {
    showCopyToast('保存事故报告失败。', { title: '保存失败' });
  }
  clearActiveIncidentReportSession();
};

const onIncidentReportAnswersUpdate = (
  answers: Record<string, IncidentReportFormAnswer>,
) => {
  updateIncidentReportAnswers(answers);
};

const onIncidentReportQuickGenerateBody = async () => {
  try {
    await quickGenerateBody(
      appStore.selectedModel,
      appStore.selectedRerankerModel,
    );
  } catch (error) {
    const message = getErrorMessage(error, '正文生成失败，请稍后重试。');
    showCopyToast(message, { title: '正文生成失败' });
  }
};

const onIncidentReportGenerateSection = async (payload: {
  sectionId: string;
  timelineIndex?: number;
}) => {
  try {
    await generateBodySection(appStore.selectedModel, payload.sectionId, {
      rerankerModel: appStore.selectedRerankerModel,
      timelineIndex: payload.timelineIndex,
    });
  } catch (error) {
    const message = getErrorMessage(error, '分段生成失败，请稍后重试。');
    showCopyToast(message, { title: '分段生成失败' });
  }
};

const onIncidentReportStopGeneration = () => {
  stopIncidentReportGeneration();
};

const onIncidentReportCancelPreview = () => {
  cancelIncidentReportPreview();
};

const onIncidentReportRequestPreview = async () => {
  try {
    await loadIncidentReportPreview({
      model: appStore.selectedModel,
      rerankerModel: appStore.selectedRerankerModel,
    });
  } catch (error) {
    const message = getErrorMessage(error, '附件预览加载失败，请稍后重试。');
    showCopyToast(message, { title: '预览失败' });
  }
};

const onIncidentReportDownloadPreviewDocx = async () => {
  try {
    await downloadIncidentReportPreviewDocx();
  } catch (error) {
    const message = getErrorMessage(error, '下载失败，请稍后重试。');
    showCopyToast(message, { title: '下载失败' });
  }
};

const onIncidentReportOpenTrace = (traceId: string) => {
  void openTraceModalByTraceId(traceId);
};

const onTraceModalRetry = () => {
  void retryTraceModalLoad();
};

const onGoHome = async () => {
  try {
    await flushSaveIncidentReportSnapshot();
  } catch {
    showCopyToast('保存事故报告失败。', { title: '保存失败' });
  }
  router.push({ name: 'home' });
};

const isTitleClickable = computed(
  () => !incidentReportStore.isIncidentReportGenerating,
);

defineExpose({
  onHeaderTitleClick,
  onGoHome,
  isTitleClickable,
});

const { loadAvailableModels } = useCatalogLoader();

onMounted(() => {
  void loadIncidentReportSchema();
  void loadIncidentReportSessionSummaries();
  void loadAvailableModels();
});
</script>

<style scoped src="./styles/incident-report-page.css"></style>
