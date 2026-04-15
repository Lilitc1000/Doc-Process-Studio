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
  fieldPath: string;
  kind: IncidentFormKind;
  options: IncidentFormOption[];
  allowCustom: boolean;
  required: boolean;
  placeholder?: string | null;
}

export interface IncidentFormAnswer {
  value?: string | string[] | null;
  customValue?: string;
}

export interface IncidentSnapshot {
  formAnswers: Record<string, IncidentFormAnswer>;
  reportData?: Record<string, unknown> | null;
  generatedAttachment?: ChatAttachment | null;
  generatedTraceId?: string | null;
  generatedAt?: string | null;
  isLocked: boolean;
  fallbackUsed: boolean;
  polishError?: string | null;
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
  introMessage: string;
  steps: IncidentFormStep[];
}

export interface IncidentGenerateResponse {
  session: IncidentSessionSummary;
  snapshot: IncidentSnapshot;
  traceId: string;
}
