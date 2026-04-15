import { ref } from 'vue';
import {
  fetchIncidentFormSchema,
  saveIncidentSessionSnapshot,
} from '../api/incident-report';
import type {
  IncidentFormAnswer,
  IncidentFormSchemaPayload,
  IncidentSessionDetail,
  IncidentSessionSummary,
} from '../types/incident-report';

export interface IncidentFormDeps {
  activeIncidentSessionId: ReturnType<typeof ref<string | null>>;
  activeIncidentSession: ReturnType<typeof ref<IncidentSessionDetail | null>>;
  mergeSummary: (summary: IncidentSessionSummary) => void;
}

const cloneFormAnswers = (answers: Record<string, IncidentFormAnswer>) => {
  return JSON.parse(JSON.stringify(answers)) as Record<
    string,
    IncidentFormAnswer
  >;
};

export const useIncidentForm = (deps: IncidentFormDeps) => {
  const { activeIncidentSessionId, activeIncidentSession, mergeSummary } = deps;

  const incidentSchema = ref<IncidentFormSchemaPayload | null>(null);

  let saveDebounceTimer: number | null = null;
  let hasQueuedSnapshotSave = false;
  let isSnapshotSaveInFlight = false;
  let snapshotSavePromise: Promise<void> | null = null;

  const loadIncidentSchema = async () => {
    try {
      incidentSchema.value = await fetchIncidentFormSchema();
    } catch (error) {
      console.error('加载事故报告表单定义失败。', error);
    }
  };

  const flushSaveIncidentSnapshot = async () => {
    if (isSnapshotSaveInFlight) {
      hasQueuedSnapshotSave = true;
      if (snapshotSavePromise) {
        await snapshotSavePromise;
      }
      return;
    }

    isSnapshotSaveInFlight = true;
    snapshotSavePromise = (async () => {
      let shouldContinue = true;
      while (shouldContinue) {
        hasQueuedSnapshotSave = false;

        const session = activeIncidentSession.value;
        const sessionId = activeIncidentSessionId.value;
        if (!session || !sessionId || session.snapshot.is_locked) {
          return;
        }

        try {
          const detail = await saveIncidentSessionSnapshot(
            sessionId,
            session.snapshot,
          );
          if (!detail || typeof detail.id !== 'string') {
            return;
          }

          if (
            activeIncidentSessionId.value !== sessionId ||
            activeIncidentSession.value?.id !== sessionId
          ) {
            return;
          }

          if (hasQueuedSnapshotSave && activeIncidentSession.value) {
            const latestLocalAnswers = cloneFormAnswers(
              activeIncidentSession.value.snapshot.form_answers,
            );
            activeIncidentSession.value = {
              ...detail,
              snapshot: {
                ...detail.snapshot,
                form_answers: latestLocalAnswers,
              },
            };
          } else {
            activeIncidentSession.value = detail;
          }

          mergeSummary({
            id: detail.id,
            title: detail.title,
            status: detail.status,
            created_at: detail.created_at,
            updated_at: detail.updated_at,
          });
        } catch (error) {
          console.error('保存事故报告会话失败。', error);
        }

        shouldContinue = hasQueuedSnapshotSave;
      }
    })().finally(() => {
      isSnapshotSaveInFlight = false;
      snapshotSavePromise = null;
    });

    await snapshotSavePromise;
  };

  const scheduleSaveIncidentSnapshot = () => {
    if (saveDebounceTimer !== null) {
      window.clearTimeout(saveDebounceTimer);
      saveDebounceTimer = null;
    }
    saveDebounceTimer = window.setTimeout(() => {
      void flushSaveIncidentSnapshot();
    }, 450);
  };

  const updateIncidentAnswers = (
    answers: Record<string, IncidentFormAnswer>,
  ) => {
    if (
      !activeIncidentSession.value ||
      activeIncidentSession.value.snapshot.is_locked
    ) {
      return;
    }
    activeIncidentSession.value = {
      ...activeIncidentSession.value,
      snapshot: {
        ...activeIncidentSession.value.snapshot,
        form_answers: cloneFormAnswers(answers),
      },
      status: 'draft',
    };
    if (isSnapshotSaveInFlight) {
      hasQueuedSnapshotSave = true;
    }
    scheduleSaveIncidentSnapshot();
  };

  const clearFormTimers = () => {
    if (saveDebounceTimer !== null) {
      window.clearTimeout(saveDebounceTimer);
      saveDebounceTimer = null;
    }
    hasQueuedSnapshotSave = false;
  };

  return {
    incidentSchema,
    loadIncidentSchema,
    updateIncidentAnswers,
    flushSaveIncidentSnapshot,
    clearFormTimers,
  };
};
