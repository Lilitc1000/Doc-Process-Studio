import type { ChatAttachment, ChatMessageRole } from './chat';

export interface ChatSessionNodePayload {
  id: string;
  role: ChatMessageRole;
  content: string;
  api_content?: string | null;
  files?: ChatAttachment[];
  timestamp: string;
  parent_id: string | null;
  child_ids: string[];
}

export interface ChatSessionSnapshotPayload {
  message_nodes: ChatSessionNodePayload[];
  root_child_ids: string[];
  selected_root_child_id: string | null;
  selected_child_id_by_parent: Record<string, string>;
  selected_processing_mode: string;
  selected_model: string;
}

export interface ChatSessionSummary {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  selected_processing_mode: string;
  selected_model: string;
}

export interface ChatSessionDetail extends ChatSessionSummary {
  snapshot: ChatSessionSnapshotPayload;
}

export interface SessionGroup {
  id: string;
  label: string;
  sessions: ChatSessionSummary[];
}
