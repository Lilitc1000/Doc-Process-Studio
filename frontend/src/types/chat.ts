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
  apiContent?: string;
  files?: ChatAttachment[];
  toolStatuses?: ChatToolStatus[];
  requestFiles?: File[];
  timestamp: Date;
  parentId: string | null;
  childIds: string[];
}

export type ChatMessageDisplay = Pick<
  ChatMessageNode,
  'id' | 'role' | 'content' | 'files' | 'toolStatuses' | 'timestamp'
>;

export interface ApiChatMessage {
  role: ChatMessageRole;
  content: string;
}

export interface ChatRequestSnapshot {
  userMessageId: string;
  conversationId: string;
  model: string;
  skillId: string;
  messages: ApiChatMessage[];
  files: File[];
  attachmentIds: string[];
}

export interface ActiveGenerationState {
  assistantId: string;
  userMessageId: string;
  controller: AbortController;
}

export interface ChatStreamEvent {
  type?: string;
  content?: string;
  message?: string;
  finish_reason?: string;
  phase?: string;
  tool_name?: string;
  label?: string;
  attachment?: ChatAttachment;
}
