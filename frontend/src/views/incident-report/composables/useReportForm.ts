import { ref, watch } from 'vue';
import humps from 'humps';
import type { IncidentBodyGenerateResponse } from '../../../types/incident-report/incident-report';

export interface TimelineItem {
  time: string;
  event: string;
  resolution: string;
}

export const severityOptions = [
  { value: '', label: '请选择 / Select' },
  { value: 'minor', label: '一般 / Minor' },
  { value: 'major', label: '严重 / Major' },
  { value: 'critical', label: '致命 / Critical' },
];

export const statusOptions = [
  { value: '', label: '请选择 / Select' },
  { value: 'follow_up_action_required', label: '跟进中 / Follow-up' },
  { value: 'closed', label: '已关闭 / Closed' },
];

export const defaultFormAnswers: Record<string, string> = {
  manual_reference_no: '',
  manual_fault_time: '',
  manual_reporting_person: '',
  manual_verified_by: '',
  manual_location: '',
  manual_fault_symptom: '',
  manual_arrival_datetime: '',
  manual_clearance_datetime: '',
  manual_service_person: '',
  manual_fault_cause: '',
  manual_materials_used: '',
  manual_repair_details: '',
  manual_contractor_staff: '',
  manual_contractor_signature: '',
  manual_contractor_date: '',
  manual_status: '',
  manual_status_ref_no: '',
  manual_employer_rep: '',
  manual_employer_signature: '',
  manual_closeout_date: '',
  manual_comments: '',
  quick_narrative: '',
  body_description: '',
  body_affected_start_time: '',
  body_affected_end_time: '',
  body_impact_scope: '',
  body_impact_severity: '',
  body_business_impact: '',
  body_trigger: '',
  body_root_cause: '',
  body_follow_up: '',
  appendix_notes: '',
};

export function convertToIso(raw: string, baseDate?: string): string {
  const trimmed = raw.trim();
  const slashWithTime = trimmed.match(
    /^(\d{1,2})\/(\d{1,2})\/(\d{4})\s+(\d{1,2}):(\d{1,2})$/,
  );
  if (slashWithTime) {
    const [, d, m, y, h, min] = slashWithTime;
    return `${y}-${m.padStart(2, '0')}-${d.padStart(2, '0')}T${h.padStart(2, '0')}:${min.padStart(2, '0')}`;
  }
  const slashOnly = trimmed.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  if (slashOnly) {
    const [, d, m, y] = slashOnly;
    return `${y}-${m.padStart(2, '0')}-${d.padStart(2, '0')}`;
  }
  const timeOnly = trimmed.match(/^(\d{1,2}):(\d{1,2})$/);
  if (timeOnly) {
    const [, h, min] = timeOnly;
    const date = baseDate || new Date().toISOString().slice(0, 10);
    return `${date}T${h.padStart(2, '0')}:${min.padStart(2, '0')}`;
  }
  return trimmed;
}

export function applyGenerationResult(
  result: IncidentBodyGenerateResponse,
  formAnswers: Record<string, unknown>,
) {
  for (const [key, answer] of Object.entries(result.formAnswers)) {
    const snakeKey = humps.decamelize(key);
    formAnswers[snakeKey] = answer.value ?? '';
  }
}

export function buildFormPayload(
  formData: { title: string; severity: string; system: string; siteId: string; faultDate: string },
  formAnswers: Record<string, string>,
  bodyTimelineItems: TimelineItem[],
) {
  const formDataPayload: Record<string, unknown> = { ...formAnswers };
  formDataPayload.body_timeline = bodyTimelineItems;
  const startTime = formAnswers.body_affected_start_time?.trim();
  const endTime = formAnswers.body_affected_end_time?.trim();
  if (startTime || endTime) {
    formDataPayload.body_affected_date_summary =
      `${startTime || ''} - ${endTime || ''}`.trim();
  }
  if (formData.severity) {
    formDataPayload.manual_severity = formData.severity;
  }
  if (formData.faultDate) {
    formDataPayload.manual_fault_date = formData.faultDate;
  }
  if (formData.system) {
    formDataPayload.manual_system = formData.system;
  }
  if (formData.siteId) {
    formDataPayload.manual_site_id = formData.siteId;
  }
  return {
    title: formData.title,
    severity: formData.severity || undefined,
    system: formData.system || undefined,
    siteId: formData.siteId || undefined,
    faultDate: formData.faultDate || undefined,
    formData: formDataPayload,
  };
}

export function useReportFormState() {
  const formData = ref({
    title: '',
    severity: '',
    system: '',
    siteId: '',
    faultDate: '',
  });

  const formAnswers = ref<Record<string, string>>({ ...defaultFormAnswers });

  const bodyTimelineItems = ref<TimelineItem[]>([
    { time: '', event: '', resolution: '' },
  ]);

  const timelineTimeErrors = ref<Record<number, string>>({});

  watch(
    bodyTimelineItems,
    (items) => {
      formAnswers.value.body_timeline = JSON.stringify(items);
    },
    { deep: true },
  );

  const onBodyTimelineChange = (
    index: number,
    key: keyof TimelineItem,
    value: string,
  ) => {
    bodyTimelineItems.value[index][key] = value;
    if (key === 'time') {
      validateTimelineTimeOrder();
    }
  };

  const validateTimelineTimeOrder = () => {
    timelineTimeErrors.value = {};
    const items = bodyTimelineItems.value;
    for (let i = 1; i < items.length; i++) {
      const prevTime = items[i - 1].time?.trim();
      const currTime = items[i].time?.trim();
      if (prevTime && currTime && currTime < prevTime) {
        timelineTimeErrors.value[i] = '时间不能早于上一条';
      }
    }
  };

  const onBodyTimelineInput = (
    index: number,
    key: keyof TimelineItem,
    event: Event,
  ) => {
    const value = (event.target as HTMLInputElement).value;
    onBodyTimelineChange(index, key, value);
  };

  const getPayload = () =>
    buildFormPayload(formData.value, formAnswers.value, bodyTimelineItems.value);

  return {
    formData,
    formAnswers,
    bodyTimelineItems,
    timelineTimeErrors,
    onBodyTimelineChange,
    validateTimelineTimeOrder,
    onBodyTimelineInput,
    getPayload,
  };
}
