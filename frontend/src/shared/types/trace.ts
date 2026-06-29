export interface TraceReplayRound {
  round?: number;
  at?: string;
  normalizedToolCalls?: unknown[];
  statusEvents?: unknown[];
  toolTraceMessages?: Array<{
    role?: string;
    name?: string;
    content?: string;
  }>;
  errorMessage?: string | null;
  disableTools?: boolean;
  toolCallsConsumed?: number;
}

export interface TraceReplayPayload {
  traceId?: string;
  tenantId?: string;
  conversationId?: string;
  userMessageId?: string;
  model?: string;
  rerankerModel?: string;
  startedAt?: string;
  planner?: Record<string, unknown> | null;
  events?: Array<{
    type?: string;
    at?: string;
    detail?: Record<string, unknown>;
  }>;
  rounds?: TraceReplayRound[];
  final?: {
    doneReason?: string | null;
    error?: string | null;
    finishedAt?: string | null;
  };
}

export interface TraceReplayResponse {
  traceId: string;
  payload: TraceReplayPayload;
}
