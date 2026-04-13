import type {
  ChatAttachment,
  ChatInteractionCard,
  ChatMessageRole,
  ChatToolStatus,
} from './chat';

export interface ChatSessionNodePayload {
  id: string;
  role: ChatMessageRole;
  content: string;
  trace_id?: string | null;
  api_content?: string | null;
  request_skill_ids?: string[] | null;
  files?: ChatAttachment[];
  tool_statuses?: ChatToolStatus[];
  interaction?: ChatInteractionCard | null;
  timestamp: string;
  parent_id: string | null;
  child_ids: string[];
}

export interface ChatSessionSnapshotPayload {
  message_nodes: ChatSessionNodePayload[];
  root_child_ids: string[];
  selected_root_child_id: string | null;
  selected_child_id_by_parent: Record<string, string>;
  selected_model: string;
  selected_reranker_model?: string | null;
}

export interface ChatSessionSummary {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  selected_model: string;
  selected_reranker_model?: string | null;
}

export interface ChatSessionDetail extends ChatSessionSummary {
  snapshot: ChatSessionSnapshotPayload;
}

export interface SessionGroup {
  id: string;
  label: string;
  sessions: ChatSessionSummary[];
}
