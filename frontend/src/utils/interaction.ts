import type {
  ChatInteractionCard,
  ChatInteractionKind,
  ChatInteractionOption,
} from '../types/chat';

const resolveText = (value: unknown, fallback = '') => {
  return typeof value === 'string' ? value : fallback;
};

const resolveBoolean = (value: unknown, fallback = false) => {
  return typeof value === 'boolean' ? value : fallback;
};

const resolveNumber = (value: unknown, fallback = 0) => {
  return typeof value === 'number' ? value : fallback;
};

const resolveKind = (value: unknown): ChatInteractionKind => {
  if (
    value === 'single_select' ||
    value === 'multi_select' ||
    value === 'text'
  ) {
    return value;
  }
  return 'single_select';
};

const normalizeOptions = (raw: unknown): ChatInteractionOption[] => {
  if (!Array.isArray(raw)) {
    return [];
  }

  const options: ChatInteractionOption[] = [];
  for (const item of raw) {
    if (!item || typeof item !== 'object') {
      continue;
    }

    const record = item as Record<string, unknown>;
    const value = resolveText(record.value).trim();
    const label = resolveText(record.label).trim();
    if (!value || !label) {
      continue;
    }

    options.push({
      value,
      label,
      description:
        typeof record.description === 'string' ? record.description : undefined,
    });
  }

  return options;
};

export const normalizeInteractionCard = (
  raw: unknown,
): ChatInteractionCard | null => {
  if (!raw || typeof raw !== 'object') {
    return null;
  }

  const record = raw as Record<string, unknown>;
  const sessionId = resolveText(record.sessionId ?? record.session_id).trim();
  const stepId = resolveText(record.stepId ?? record.step_id).trim();
  if (!sessionId || !stepId) {
    return null;
  }

  return {
    sessionId,
    stepId,
    title: resolveText(record.title),
    prompt: resolveText(record.prompt),
    kind: resolveKind(record.kind),
    allowCustom: resolveBoolean(record.allowCustom ?? record.allow_custom),
    required: resolveBoolean(record.required, true),
    placeholder:
      typeof (record.placeholder ?? null) === 'string'
        ? (record.placeholder as string)
        : null,
    currentStep: resolveNumber(record.currentStep ?? record.current_step, 1),
    totalSteps: resolveNumber(record.totalSteps ?? record.total_steps, 1),
    options: normalizeOptions(record.options),
  };
};
