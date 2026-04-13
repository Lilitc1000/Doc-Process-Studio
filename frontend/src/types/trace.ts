export interface TraceReplayRound {
  round?: number;
  at?: string;
  normalized_tool_calls?: unknown[];
  status_events?: unknown[];
  tool_trace_messages?: Array<{
    role?: string;
    name?: string;
    content?: string;
  }>;
  error_message?: string | null;
  disable_tools?: boolean;
  tool_calls_consumed?: number;
}

export interface TraceReplayPayload {
  trace_id?: string;
  tenant_id?: string;
  conversation_id?: string;
  user_message_id?: string;
  model?: string;
  reranker_model?: string;
  started_at?: string;
  planner?: Record<string, unknown> | null;
  events?: Array<{
    type?: string;
    at?: string;
    detail?: Record<string, unknown>;
  }>;
  rounds?: TraceReplayRound[];
  final?: {
    done_reason?: string | null;
    error?: string | null;
    finished_at?: string | null;
  };
}

export interface TraceReplayResponse {
  trace_id: string;
  payload: TraceReplayPayload;
}
