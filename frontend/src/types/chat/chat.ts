export type ChatMessageRole = 'user' | 'assistant' | 'system';

export interface ChatAttachment {
  name: string;
  sizeLabel: string;
  attachmentId?: string;
  downloadUrl?: string;
  expiresAt?: string;
  mimeType?: string;
  source?: string;
}

export interface ChatEditAttachment extends ChatAttachment {
  requestFile?: File | null;
}

export interface ChatToolStatus {
  id: string;
  toolName?: string;
  label?: string;
  message: string;
  phase?: string;
  createdAt: string;
}

export interface ChatMessageNode {
  id: string;
  role: ChatMessageRole;
  content: string;
  traceId?: string;
  apiContent?: string;
  files?: ChatAttachment[];
  toolStatuses?: ChatToolStatus[];
  requestFiles?: File[];
  requestSkillIds?: string[];
  timestamp: Date;
  parentId: string | null;
  childIds: string[];
}

export type ChatMessageDisplay = Pick<
  ChatMessageNode,
  | 'id'
  | 'role'
  | 'content'
  | 'traceId'
  | 'files'
  | 'requestSkillIds'
  | 'toolStatuses'
  | 'timestamp'
>;

export interface ApiChatMessage {
  role: ChatMessageRole;
  content: string;
}

export interface ChatRequestSnapshot {
  userMessageId: string;
  conversationId: string;
  model: string;
  rerankerModel: string;
  selectedSkillIds: string[];
  messages: ApiChatMessage[];
  files: File[];
  attachmentIds: string[];
}

export interface ActiveGenerationState {
  assistantId: string;
  userMessageId: string;
  controller: AbortController;
}

export interface OllamaStreamMessage {
  role?: ChatMessageRole | string;
  content?: string;
  toolCalls?: Array<{
    function?: {
      name?: string;
      arguments?: unknown;
    };
  }>;
}

export interface ChatStreamEvent {
  model?: string;
  createdAt?: string;
  message?: OllamaStreamMessage | string;
  done?: boolean;
  doneReason?: string;
  traceId?: string;
  type?: string;
  content?: string;
  phase?: string;
  toolName?: string;
  label?: string;
  attachment?: ChatAttachment;
}
