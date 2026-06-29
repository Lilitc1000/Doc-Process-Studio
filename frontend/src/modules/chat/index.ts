// chat 模块桶文件：统一导出聊天域公共 API

// --- Store ---
export { useChatStore } from './store/chat';

// --- API ---
export { downloadAttachment } from './api/chat-attachments';
export { streamChatReply } from './api/chat-stream';
export {
  fetchSessionSummaries,
  saveSession,
  fetchSessionDetail,
  renameSession,
  removeSession,
} from './api/chat-sessions';

// --- Types ---
export type {
  ChatMessageRole,
  ChatAttachment,
  ChatEditAttachment,
  ChatToolStatus,
  ChatMessageNode,
  ChatMessageDisplay,
  ApiChatMessage,
  ChatRequestSnapshot,
  ActiveGenerationState,
  OllamaStreamMessage,
  ChatStreamEvent,
} from './types/chat';
export type {
  ChatSessionNodePayload,
  ChatSessionSnapshotPayload,
  ChatSessionSummary,
  ChatSessionDetail,
} from './types/session';

// --- Utils ---
export { groupSessionsByDate } from './utils/session-groups';
export { parseStreamEvents } from './utils/chat-stream';
export {
  findNodeById,
  getSelectedChildId,
  buildDisplayedMessages,
  getMessagePathToNode,
  collectPersistedUploadedAttachmentIdsFromPath,
  getMessageSiblingIds,
  getMessageVersionCount,
  getMessageVersionIndex,
  canSwitchMessageVersion,
  resolveTargetVersionMessageId,
  findAdjacentVersionNodes,
  resolveCurrentLeafMessageId,
  resolveLastRoleMessageId,
} from './utils/message-tree';
