// shared 桶文件：统一导出全局基础设施

// --- UI 原子组件 ---
export { default as BaseButton } from './ui/BaseButton.vue';
export { default as BaseInput } from './ui/BaseInput.vue';
export { default as BaseTextarea } from './ui/BaseTextarea.vue';
export { default as BaseDropdown } from './ui/BaseDropdown.vue';
export { default as BaseFileUpload } from './ui/BaseFileUpload.vue';
export { default as BaseDateTimePicker } from './ui/BaseDateTimePicker.vue';
export { default as PasswordInput } from './ui/PasswordInput.vue';
export { default as BaseConfirmDialog } from './ui/BaseConfirmDialog.vue';

// --- UI 业务组件（跨域共享） ---
export { default as SessionSidebar } from './components/SessionSidebar.vue';
export { default as FloatingToast } from './components/FloatingToast.vue';
export { default as TraceReplayModal } from './components/TraceReplayModal.vue';
export { default as AiGeneratingModal } from './components/AiGeneratingModal.vue';
export { default as UserAvatar } from './components/UserAvatar.vue';
export { default as UserMenuDropdown } from './components/UserMenuDropdown.vue';
export { default as UserProfileModal } from './components/UserProfileModal.vue';

// --- Stores ---
export { useAppStore } from './stores/app';
export type { PageId, KBProjectOption } from './stores/app';

// --- Composables ---
export { useCatalogLoader } from './composables/useCatalogLoader';
export { useCopyToast } from './composables/useCopyToast';
export { useTraceModal } from './composables/useTraceModal';
export { useUserProfile } from './composables/useUserProfile';

// --- API ---
export { apiClient } from './api/request';
export { fetchAvailableModels, fetchAvailableSkills } from './api/catalog';
export { fetchAgentTraceReplay } from './api/trace';

// --- Utils ---
export { AVATAR_COLORS } from './utils/avatar-colors';
export { formatFileSize, getFileTypeVisual } from './utils/file';
export {
  FILE_TYPE_VISUALS,
  FILE_EXTENSION_VISUAL_MAP,
  MIME_TYPE_CATEGORY_MAP,
} from './utils/file-type-visuals';
export type { FileTypeVisual } from './utils/file-type-visuals';
export { createConversationId, createMessageId } from './utils/ids';
export { logger } from './utils/logger';
export { getErrorMessage } from './utils/error';
export { triggerBlobDownload } from './utils/download';
export {
  renderMarkdown,
  shouldUseMarkdownRendering,
  renderPlainText,
  getCachedRenderedContent,
  setCachedRenderedContent,
  prewarmRenderedContentCache,
} from './utils/render-markdown';
export { formatDate, formatDateTime, formatDateTimeFull } from './utils/date';
export { isRequestCanceled } from './utils/cancel';
export { extractModelNames, normalizeSkillCatalog } from './utils/catalog';
export type { RemoteModelRecord, ModelCatalogPayload } from './utils/catalog';

// --- Types ---
export type { SkillOption, SkillCatalogPayload } from './types/skill';
export type {
  TraceReplayRound,
  TraceReplayPayload,
  TraceReplayResponse,
} from './types/trace';

// --- Directives ---
export { default as safeHtml } from './directives/safe-html';
