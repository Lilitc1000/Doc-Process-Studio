import type { ChatAttachment } from '../chat/chat';

export type IncidentReportSessionStatus =
  | 'draft'
  | 'generating'
  | 'generated'
  | 'failed';

export interface IncidentReportFormOption {
  value: string;
  label: string;
  description?: string | null;
}

export type IncidentReportFormKind = 'single_select' | 'multi_select' | 'text';

export interface IncidentReportFormStep {
  id: string;
  title: string;
  prompt: string;
  fieldPath: string;
  kind: IncidentReportFormKind;
  options: IncidentReportFormOption[];
  allowCustom: boolean;
  required: boolean;
  placeholder?: string | null;
}

export interface IncidentReportFormAnswer {
  value?: unknown;
  customValue?: string;
}

export interface IncidentReportGeneratedVersion {
  version: number;
  label: string;
  generatedAt: string;
  attachment: ChatAttachment;
  reportData: Record<string, unknown>;
}

export interface IncidentReportSnapshot {
  formAnswers: Record<string, IncidentReportFormAnswer>;
  reportData?: Record<string, unknown> | null;
  generatedAttachment?: ChatAttachment | null;
  generatedVersions?: IncidentReportGeneratedVersion[];
  generatedTraceId?: string | null;
  sectionTraceIds?: Record<string, string>;
  generatedAt?: string | null;
  isLocked: boolean;
  fallbackUsed: boolean;
  polishError?: string | null;
}

export interface IncidentReportSessionSummary {
  id: string;
  title: string;
  status: IncidentReportSessionStatus;
  createdAt: string;
  updatedAt: string;
}

export interface IncidentReportSessionDetail extends IncidentReportSessionSummary {
  snapshot: IncidentReportSnapshot;
}

export interface IncidentReportFormSchemaPayload {
  introMessage: string;
  steps: IncidentReportFormStep[];
}

export interface IncidentReportBodyGenerateResponse {
  session: IncidentReportSessionSummary;
  snapshot: IncidentReportSnapshot;
  traceId: string;
  sectionId: string;
  timelineIndex?: number | null;
}

export interface IncidentReportPreviewResponse {
  source: 'draft' | 'version';
  version?: number | null;
  label: string;
  html: string;
  docxBase64?: string | null;
  docxFileName?: string | null;
  pdfBase64?: string | null;
  warnings: string[];
}
