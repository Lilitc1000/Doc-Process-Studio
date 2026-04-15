import type { ChatAttachment } from './chat';

export type IncidentSessionStatus =
  | 'draft'
  | 'generating'
  | 'generated'
  | 'failed';

export interface IncidentFormOption {
  value: string;
  label: string;
  description?: string | null;
}

export type IncidentFormKind = 'single_select' | 'multi_select' | 'text';

export interface IncidentFormStep {
  id: string;
  title: string;
  prompt: string;
  field_path: string;
  kind: IncidentFormKind;
  options: IncidentFormOption[];
  allow_custom: boolean;
  required: boolean;
  placeholder?: string | null;
}

export interface IncidentFormAnswer {
  value?: string | string[] | null;
  custom_value?: string;
}

export interface IncidentSnapshot {
  form_answers: Record<string, IncidentFormAnswer>;
  report_data?: Record<string, unknown> | null;
  generated_attachment?: ChatAttachment | null;
  generated_trace_id?: string | null;
  generated_at?: string | null;
  is_locked: boolean;
  fallback_used: boolean;
  polish_error?: string | null;
}

export interface IncidentSessionSummary {
  id: string;
  title: string;
  status: IncidentSessionStatus;
  created_at: string;
  updated_at: string;
}

export interface IncidentSessionDetail extends IncidentSessionSummary {
  snapshot: IncidentSnapshot;
}

export interface IncidentFormSchemaPayload {
  intro_message: string;
  steps: IncidentFormStep[];
}

export interface IncidentGenerateResponse {
  session: IncidentSessionSummary;
  snapshot: IncidentSnapshot;
  trace_id: string;
}
