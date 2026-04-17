import { useIncidentStore } from '../stores/incident';
import {
  fetchIncidentFormSchema,
  saveIncidentSessionSnapshot,
} from '../api/incident-report';
import type { IncidentFormAnswer } from '../types/incident-report';

const cloneFormAnswers = (answers: Record<string, IncidentFormAnswer>) => {
  return JSON.parse(JSON.stringify(answers)) as Record<
    string,
    IncidentFormAnswer
  >;
};

export const useIncidentForm = () => {
  const incidentStore = useIncidentStore();

  let saveDebounceTimer: number | null = null;
  let hasQueuedSnapshotSave = false;
  let isSnapshotSaveInFlight = false;
  let snapshotSavePromise: Promise<void> | null = null;

  const loadIncidentSchema = async () => {
    try {
      incidentStore.incidentSchema = await fetchIncidentFormSchema();
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

        const session = incidentStore.activeIncidentSession;
        const sessionId = incidentStore.activeIncidentSessionId;
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
            incidentStore.activeIncidentSessionId !== sessionId ||
            incidentStore.activeIncidentSession?.id !== sessionId
          ) {
            return;
          }

          if (hasQueuedSnapshotSave && incidentStore.activeIncidentSession) {
            const latestLocalAnswers = cloneFormAnswers(
              incidentStore.activeIncidentSession.snapshot.form_answers,
            );
            incidentStore.activeIncidentSession = {
              ...detail,
              snapshot: {
                ...detail.snapshot,
                form_answers: latestLocalAnswers,
              },
            };
          } else {
            incidentStore.activeIncidentSession = detail;
          }

          incidentStore.mergeSummary({
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
      !incidentStore.activeIncidentSession ||
      incidentStore.activeIncidentSession.snapshot.is_locked
    ) {
      return;
    }
    incidentStore.activeIncidentSession = {
      ...incidentStore.activeIncidentSession,
      snapshot: {
        ...incidentStore.activeIncidentSession.snapshot,
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
    loadIncidentSchema,
    updateIncidentAnswers,
    flushSaveIncidentSnapshot,
    clearFormTimers,
  };
};
