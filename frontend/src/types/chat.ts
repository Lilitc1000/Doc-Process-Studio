export type ChatMessageRole = 'user' | 'assistant' | 'system';

export interface ChatAttachment {
  name: string;
  size_label: string;
  attachment_id?: string;
  download_url?: string;
  expires_at?: string;
  mime_type?: string;
  source?: string;
}

export interface ChatEditAttachment extends ChatAttachment {
  request_file?: File | null;
}

export interface ChatToolStatus {
  id: string;
  tool_name?: string;
  label?: string;
  message: string;
  phase?: string;
  created_at: string;
}

export interface ChatMessageNode {
  id: string;
  role: ChatMessageRole;
  content: string;
  trace_id?: string;
  api_content?: string;
  files?: ChatAttachment[];
  tool_statuses?: ChatToolStatus[];
  request_files?: File[];
  request_skill_ids?: string[];
  timestamp: Date;
  parent_id: string | null;
  child_ids: string[];
}

export type ChatMessageDisplay = Pick<
  ChatMessageNode,
  | 'id'
  | 'role'
  | 'content'
  | 'trace_id'
  | 'files'
  | 'request_skill_ids'
  | 'tool_statuses'
  | 'timestamp'
>;

export interface ApiChatMessage {
  role: ChatMessageRole;
  content: string;
}

export interface ChatRequestSnapshot {
  user_message_id: string;
  conversation_id: string;
  model: string;
  reranker_model: string;
  selected_skill_ids: string[];
  messages: ApiChatMessage[];
  files: File[];
  attachment_ids: string[];
}

export interface ActiveGenerationState {
  assistant_id: string;
  user_message_id: string;
  controller: AbortController;
}

export interface OllamaStreamMessage {
  role?: ChatMessageRole | string;
  content?: string;
  tool_calls?: Array<{
    function?: {
      name?: string;
      arguments?: unknown;
    };
  }>;
}

export interface ChatStreamEvent {
  model?: string;
  created_at?: string;
  message?: OllamaStreamMessage | string;
  done?: boolean;
  done_reason?: string;
  trace_id?: string;
  type?: string;
  content?: string;
  phase?: string;
  tool_name?: string;
  label?: string;
  attachment?: ChatAttachment;
}
