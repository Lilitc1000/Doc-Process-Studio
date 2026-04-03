export type ChatMessageRole = 'user' | 'assistant' | 'system';

export interface ChatAttachment {
  name: string;
  sizeLabel: string;
}

export interface ChatMessageNode {
  id: string;
  role: ChatMessageRole;
  content: string;
  apiContent?: string;
  files?: ChatAttachment[];
  requestFiles?: File[];
  timestamp: Date;
  parentId: string | null;
  childIds: string[];
}

export type ChatMessageDisplay = Pick<
  ChatMessageNode,
  'id' | 'role' | 'content' | 'files' | 'timestamp'
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
}
