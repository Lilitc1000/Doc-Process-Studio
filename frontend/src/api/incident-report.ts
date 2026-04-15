import { apiClient } from './client';
import type {
  IncidentFormAnswer,
  IncidentFormSchemaPayload,
  IncidentFormStep,
  IncidentGenerateResponse,
  IncidentSessionDetail,
  IncidentSessionSummary,
  IncidentSnapshot,
} from '../types/incident-report';

const normalizeStep = (rawStep: Record<string, unknown>): IncidentFormStep => {
  return {
    id: String(rawStep.id ?? ''),
    title: String(rawStep.title ?? ''),
    prompt: String(rawStep.prompt ?? ''),
    fieldPath: String(rawStep.field_path ?? rawStep.fieldPath ?? ''),
    kind: String(rawStep.kind ?? 'text') as IncidentFormStep['kind'],
    options: Array.isArray(rawStep.options)
      ? rawStep.options.map((rawOption) => {
          const option = (rawOption ?? {}) as Record<string, unknown>;
          return {
            value: String(option.value ?? ''),
            label: String(option.label ?? ''),
            description:
              typeof option.description === 'string'
                ? option.description
                : null,
          };
        })
      : [],
    allowCustom: Boolean(rawStep.allow_custom ?? rawStep.allowCustom),
    required: rawStep.required === undefined ? true : Boolean(rawStep.required),
    placeholder:
      typeof rawStep.placeholder === 'string' ? rawStep.placeholder : null,
  };
};

const normalizeSnapshot = (
  rawSnapshot: Record<string, unknown>,
): IncidentSnapshot => {
  const formAnswers: Record<string, IncidentFormAnswer> = {};
  const rawAnswers = rawSnapshot.form_answers ?? rawSnapshot.formAnswers;
  if (rawAnswers && typeof rawAnswers === 'object') {
    for (const [stepId, rawAnswer] of Object.entries(
      rawAnswers as Record<string, unknown>,
    )) {
      const answer = (rawAnswer ?? {}) as Record<string, unknown>;
      formAnswers[stepId] = {
        value:
          typeof answer.value === 'string' || Array.isArray(answer.value)
            ? (answer.value as string | string[])
            : null,
        customValue:
          typeof answer.custom_value === 'string'
            ? answer.custom_value
            : typeof answer.customValue === 'string'
              ? answer.customValue
              : undefined,
      };
    }
  }

  return {
    formAnswers,
    reportData: (rawSnapshot.report_data ??
      rawSnapshot.reportData ??
      null) as Record<string, unknown> | null,
    generatedAttachment: (rawSnapshot.generated_attachment ??
      rawSnapshot.generatedAttachment ??
      null) as IncidentSnapshot['generatedAttachment'],
    generatedTraceId: String(
      rawSnapshot.generated_trace_id ?? rawSnapshot.generatedTraceId ?? '',
    ),
    generatedAt:
      typeof rawSnapshot.generated_at === 'string'
        ? rawSnapshot.generated_at
        : typeof rawSnapshot.generatedAt === 'string'
          ? rawSnapshot.generatedAt
          : null,
    isLocked: Boolean(rawSnapshot.is_locked ?? rawSnapshot.isLocked),
    fallbackUsed: Boolean(
      rawSnapshot.fallback_used ?? rawSnapshot.fallbackUsed,
    ),
    polishError:
      typeof rawSnapshot.polish_error === 'string'
        ? rawSnapshot.polish_error
        : typeof rawSnapshot.polishError === 'string'
          ? rawSnapshot.polishError
          : null,
  };
};

const normalizeSummary = (
  rawSummary: Record<string, unknown>,
): IncidentSessionSummary => {
  return {
    id: String(rawSummary.id ?? ''),
    title: String(rawSummary.title ?? ''),
    status: String(
      rawSummary.status ?? 'draft',
    ) as IncidentSessionSummary['status'],
    created_at: String(rawSummary.created_at ?? rawSummary.createdAt ?? ''),
    updated_at: String(rawSummary.updated_at ?? rawSummary.updatedAt ?? ''),
  };
};

const normalizeDetail = (
  rawDetail: Record<string, unknown>,
): IncidentSessionDetail => {
  return {
    ...normalizeSummary(rawDetail),
    snapshot: normalizeSnapshot(
      (rawDetail.snapshot ?? {}) as Record<string, unknown>,
    ),
  };
};

const normalizeGenerateResponse = (
  rawPayload: Record<string, unknown>,
): IncidentGenerateResponse => {
  return {
    session: normalizeSummary(
      (rawPayload.session ?? {}) as Record<string, unknown>,
    ),
    snapshot: normalizeSnapshot(
      (rawPayload.snapshot ?? {}) as Record<string, unknown>,
    ),
    traceId: String(rawPayload.trace_id ?? rawPayload.traceId ?? ''),
  };
};

export const fetchIncidentFormSchema =
  async (): Promise<IncidentFormSchemaPayload> => {
    const response = await apiClient.get<{
      intro_message?: string;
      introMessage?: string;
      steps?: Record<string, unknown>[];
    }>('/incident-report/schema');
    const payload = response.data;
    return {
      introMessage: String(payload.intro_message ?? payload.introMessage ?? ''),
      steps: Array.isArray(payload.steps)
        ? payload.steps.map(normalizeStep)
        : [],
    };
  };

export const fetchIncidentSessionSummaries = async (): Promise<
  IncidentSessionSummary[]
> => {
  const response = await apiClient.get<{
    sessions?: Record<string, unknown>[];
  }>('/incident-report/sessions');
  const sessions = response.data.sessions ?? [];
  return sessions.map(normalizeSummary);
};

export const createIncidentSession = async (payload: { title: string }) => {
  const response = await apiClient.post<Record<string, unknown>>(
    '/incident-report/sessions',
    payload,
  );
  return normalizeSummary(response.data);
};

export const fetchIncidentSessionDetail = async (sessionId: string) => {
  const response = await apiClient.get<Record<string, unknown>>(
    `/incident-report/sessions/${sessionId}`,
  );
  return normalizeDetail(response.data);
};

export const saveIncidentSessionSnapshot = async (
  sessionId: string,
  snapshot: IncidentSnapshot,
) => {
  const response = await apiClient.put<Record<string, unknown>>(
    `/incident-report/sessions/${sessionId}`,
    {
      snapshot: {
        form_answers: Object.fromEntries(
          Object.entries(snapshot.formAnswers).map(([stepId, answer]) => {
            return [
              stepId,
              {
                value: answer.value ?? null,
                custom_value: answer.customValue ?? '',
              },
            ];
          }),
        ),
      },
    },
  );
  return normalizeDetail(response.data);
};

export const generateIncidentAttachment = async (
  sessionId: string,
  payload: {
    model: string;
    rerankerModel?: string;
    outputName?: string;
  },
  options?: {
    signal?: AbortSignal;
  },
) => {
  const response = await apiClient.post<Record<string, unknown>>(
    `/incident-report/sessions/${sessionId}/generate`,
    {
      model: payload.model,
      reranker_model: payload.rerankerModel ?? '',
      output_name: payload.outputName ?? '',
    },
    {
      signal: options?.signal,
    },
  );
  return normalizeGenerateResponse(response.data);
};

export const renameIncidentSession = async (
  sessionId: string,
  title: string,
) => {
  const response = await apiClient.patch<Record<string, unknown>>(
    `/incident-report/sessions/${sessionId}/title`,
    { title },
  );
  return normalizeSummary(response.data);
};

export const removeIncidentSession = async (sessionId: string) => {
  await apiClient.delete(`/incident-report/sessions/${sessionId}`);
};
