import type { ChatAttachment, ChatMessageRole, ChatToolStatus } from './chat';

export interface ChatSessionNodePayload {
  id: string;
  role: ChatMessageRole;
  content: string;
  traceId?: string | null;
  apiContent?: string | null;
  requestSkillIds?: string[] | null;
  files?: ChatAttachment[];
  toolStatuses?: ChatToolStatus[];
  timestamp: string;
  parentId: string | null;
  childIds: string[];
}

export interface ChatSessionSnapshotPayload {
  messageNodes: ChatSessionNodePayload[];
  rootChildIds: string[];
  selectedRootChildId: string | null;
  selectedChildIdByParent: Record<string, string>;
  selectedModel: string;
  selectedRerankerModel?: string | null;
}

export interface ChatSessionSummary {
  id: string;
  title: string;
  status?: string;
  statusLabel?: string;
  createdAt: string;
  updatedAt: string;
  selectedModel?: string;
  selectedRerankerModel?: string | null;
}

export interface ChatSessionDetail extends ChatSessionSummary {
  snapshot: ChatSessionSnapshotPayload;
}
