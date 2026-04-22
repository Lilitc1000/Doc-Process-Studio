<template>
  <div class="incident-page">
    <AppHeader
      page-id="incident-report"
      :title-clickable="!incidentStore.isIncidentGenerating"
      @go-home="onGoHome"
      @title-click="onHeaderTitleClick"
    />
    <div class="incident-page-body">
      <ChatSidebar
        :sessions="incidentStore.incidentSidebarSessions"
        :active-session-id="incidentStore.activeIncidentSessionId"
        :is-locked="incidentStore.isIncidentGenerating"
        :group-by-created-at="true"
        @load-session="onLoadSession"
        @rename-session="onRenameSession"
        @delete-session="onDeleteSession"
      />
      <div class="incident-main">
        <IncidentReportWorkspace
          :schema="incidentStore.incidentSchema"
          :session="incidentStore.activeIncidentSession"
          :is-generating="incidentStore.isIncidentGenerating"
          :generation-state="incidentStore.generationState"
          :generation-task="incidentStore.generationTask"
          :preview-html="incidentStore.incidentPreviewHtml"
          :preview-pdf-base64="incidentStore.incidentPreviewPdfBase64"
          :preview-docx-base64="incidentStore.incidentPreviewDocxBase64"
          :preview-loading="incidentStore.incidentPreviewLoading"
          :preview-error="incidentStore.incidentPreviewError"
          @start="onStartIncident"
          @update-answers="onIncidentAnswersUpdate"
          @quick-generate-body="onIncidentQuickGenerateBody"
          @generate-section="onIncidentGenerateSection"
          @download-preview-docx="onIncidentDownloadPreviewDocx"
          @open-trace="onIncidentOpenTrace"
          @stop-generation="onIncidentStopGeneration"
          @request-preview="onIncidentRequestPreview"
          @cancel-preview="onIncidentCancelPreview"
        />
      </div>
    </div>
    <TraceReplayModal
      :visible="isTraceModalVisible"
      :trace-id="activeTraceId"
      :loading="isTraceModalLoading"
      :error-message="traceModalErrorMessage"
      :payload="activeTracePayload"
      @close="closeTraceModal"
      @retry="retryTraceModalLoad"
      @copy-trace-id="copyTraceId"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue';
import { useAppStore } from '../stores/app';
import { useIncidentStore } from '../stores/incident';
import { useCatalogLoader } from '../composables/useCatalogLoader';
import { useCopyToast } from '../composables/useCopyToast';
import { useIncidentReportSessions } from '../composables/useIncidentReportSessions';
import { useTraceModal } from '../composables/useTraceModal';
import type { IncidentFormAnswer } from '../types/incident-report';
import AppHeader from '../components/AppHeader.vue';
import ChatSidebar from '../components/ChatSidebar.vue';
import IncidentReportWorkspace from '../components/IncidentReportWorkspace.vue';
import TraceReplayModal from '../components/TraceReplayModal.vue';

const appStore = useAppStore();
const incidentStore = useIncidentStore();

const { showCopyToast } = useCopyToast();

const {
  activeTraceId,
  activeTracePayload,
  closeTraceModal,
  copyTraceId,
  isTraceModalLoading,
  isTraceModalVisible,
  openTraceModalByTraceId,
  retryTraceModalLoad,
  traceModalErrorMessage,
} = useTraceModal({
  showCopyToast,
});

const {
  cancelIncidentPreview,
  clearActiveIncidentSession,
  deleteIncident,
  downloadIncidentPreviewDocx,
  flushSaveIncidentSnapshot,
  generateBodySection,
  loadIncidentPreview,
  quickGenerateBody,
  loadIncidentSchema,
  loadIncidentSession,
  loadIncidentSessionSummaries,
  renameIncident,
  startIncidentSession,
  stopIncidentGeneration,
  updateIncidentAnswers,
} = useIncidentReportSessions();

const onLoadSession = async (sessionId: string) => {
  await loadIncidentSession(sessionId);
};

const onRenameSession = async (payload: {
  sessionId: string;
  title: string;
}) => {
  await renameIncident(payload.sessionId, payload.title);
};

const onDeleteSession = async (sessionId: string) => {
  await deleteIncident(sessionId);
};

const onStartIncident = async () => {
  await startIncidentSession();
};

const onHeaderTitleClick = async () => {
  try {
    await flushSaveIncidentSnapshot();
  } catch {
    showCopyToast('保存事故报告失败。', { title: '保存失败' });
  }
  clearActiveIncidentSession();
};

const onIncidentAnswersUpdate = (
  answers: Record<string, IncidentFormAnswer>,
) => {
  updateIncidentAnswers(answers);
};

const onIncidentQuickGenerateBody = async () => {
  try {
    await quickGenerateBody(
      appStore.selectedModel,
      appStore.selectedRerankerModel,
    );
  } catch (error) {
    const message =
      error instanceof Error ? error.message : '正文生成失败，请稍后重试。';
    showCopyToast(message, { title: '正文生成失败' });
  }
};

const onIncidentGenerateSection = async (payload: {
  sectionId: string;
  timelineIndex?: number;
}) => {
  try {
    await generateBodySection(appStore.selectedModel, payload.sectionId, {
      reranker_model: appStore.selectedRerankerModel,
      timeline_index: payload.timelineIndex,
    });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : '分段生成失败，请稍后重试。';
    showCopyToast(message, { title: '分段生成失败' });
  }
};

const onIncidentStopGeneration = () => {
  stopIncidentGeneration();
};

const onIncidentCancelPreview = () => {
  cancelIncidentPreview();
};

const onIncidentRequestPreview = async () => {
  try {
    await loadIncidentPreview({
      model: appStore.selectedModel,
      reranker_model: appStore.selectedRerankerModel,
    });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : '附件预览加载失败，请稍后重试。';
    showCopyToast(message, { title: '预览失败' });
  }
};

const onIncidentDownloadPreviewDocx = async () => {
  try {
    await downloadIncidentPreviewDocx();
  } catch (error) {
    const message =
      error instanceof Error ? error.message : '下载失败，请稍后重试。';
    showCopyToast(message, { title: '下载失败' });
  }
};

const onIncidentOpenTrace = (traceId: string) => {
  void openTraceModalByTraceId(traceId);
};

const onGoHome = async () => {
  try {
    await flushSaveIncidentSnapshot();
  } catch {
    showCopyToast('保存事故报告失败。', { title: '保存失败' });
  }
  appStore.activePageId = 'home';
};

const { loadAvailableModels } = useCatalogLoader();

onMounted(() => {
  void loadIncidentSchema();
  void loadIncidentSessionSummaries();
  void loadAvailableModels();
});
</script>

<style scoped src="../styles/components/incident-page.css"></style>
