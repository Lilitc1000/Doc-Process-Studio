export type ChatMessageRole = 'user' | 'assistant' | 'system';

export type ChatInteractionKind = 'single_select' | 'multi_select' | 'text';

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

export interface ChatInteractionOption {
  value: string;
  label: string;
  description?: string | null;
}

export interface ChatInteractionCard {
  sessionId: string;
  stepId: string;
  title: string;
  prompt: string;
  kind: ChatInteractionKind;
  allowCustom: boolean;
  required: boolean;
  placeholder?: string | null;
  currentStep: number;
  totalSteps: number;
  options: ChatInteractionOption[];
}

export interface ChatInteractionAnswer {
  sessionId?: string;
  stepId: string;
  value?: string | string[];
  customValue?: string;
  useDefaultsForMissing?: boolean;
}

export interface ChatMessageNode {
  id: string;
  role: ChatMessageRole;
  content: string;
  apiContent?: string;
  files?: ChatAttachment[];
  toolStatuses?: ChatToolStatus[];
  interaction?: ChatInteractionCard | null;
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
  | 'files'
  | 'requestSkillIds'
  | 'toolStatuses'
  | 'interaction'
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
  interactionAnswer?: ChatInteractionAnswer;
}

export interface ActiveGenerationState {
  assistantId: string;
  userMessageId: string;
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
  type?: string;
  content?: string;
  phase?: string;
  tool_name?: string;
  label?: string;
  attachment?: ChatAttachment;
  status?: string;
  interaction?: ChatInteractionCard;
}
