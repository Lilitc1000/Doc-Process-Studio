import { useIncidentReportStore } from '../../../stores/incident-report';
import {
  fetchIncidentReportFormSchema,
  saveIncidentReportSessionSnapshot,
} from '../../../api/incident-report';
import type { IncidentReportFormAnswer } from '../../../types/incident-report/incident-report';

const cloneFormAnswers = (
  answers: Record<string, IncidentReportFormAnswer>,
) => {
  return JSON.parse(JSON.stringify(answers)) as Record<
    string,
    IncidentReportFormAnswer
  >;
};

export const useIncidentReportForm = () => {
  const incidentReportStore = useIncidentReportStore();

  let saveDebounceTimer: number | null = null;
  let hasQueuedSnapshotSave = false;
  let isSnapshotSaveInFlight = false;
  let snapshotSavePromise: Promise<void> | null = null;

  const loadIncidentReportSchema = async () => {
    try {
      incidentReportStore.incidentReportSchema =
        await fetchIncidentReportFormSchema();
    } catch (error) {
      console.error('加载事故报告表单定义失败。', error);
    }
  };

  const flushSaveIncidentReportSnapshot = async () => {
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

        const session = incidentReportStore.activeIncidentReportSession;
        const sessionId = incidentReportStore.activeIncidentReportSessionId;
        if (!session || !sessionId || session.snapshot.isLocked) {
          return;
        }

        try {
          const detail = await saveIncidentReportSessionSnapshot(
            sessionId,
            session.snapshot,
          );
          if (!detail || typeof detail.id !== 'string') {
            return;
          }

          if (
            incidentReportStore.activeIncidentReportSessionId !== sessionId ||
            incidentReportStore.activeIncidentReportSession?.id !== sessionId
          ) {
            return;
          }

          if (
            hasQueuedSnapshotSave &&
            incidentReportStore.activeIncidentReportSession
          ) {
            const latestLocalAnswers = cloneFormAnswers(
              incidentReportStore.activeIncidentReportSession.snapshot
                .formAnswers,
            );
            incidentReportStore.activeIncidentReportSession = {
              ...detail,
              snapshot: {
                ...detail.snapshot,
                formAnswers: latestLocalAnswers,
              },
            };
          } else {
            incidentReportStore.activeIncidentReportSession = detail;
          }

          incidentReportStore.mergeSummary({
            id: detail.id,
            title: detail.title,
            status: detail.status,
            createdAt: detail.createdAt,
            updatedAt: detail.updatedAt,
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

  const scheduleSaveIncidentReportSnapshot = () => {
    if (saveDebounceTimer !== null) {
      window.clearTimeout(saveDebounceTimer);
      saveDebounceTimer = null;
    }
    saveDebounceTimer = window.setTimeout(() => {
      void flushSaveIncidentReportSnapshot();
    }, 450);
  };

  const updateIncidentReportAnswers = (
    answers: Record<string, IncidentReportFormAnswer>,
  ) => {
    if (
      !incidentReportStore.activeIncidentReportSession ||
      incidentReportStore.activeIncidentReportSession.snapshot.isLocked
    ) {
      return;
    }
    incidentReportStore.activeIncidentReportSession = {
      ...incidentReportStore.activeIncidentReportSession,
      snapshot: {
        ...incidentReportStore.activeIncidentReportSession.snapshot,
        formAnswers: cloneFormAnswers(answers),
      },
      status: 'draft',
    };
    if (isSnapshotSaveInFlight) {
      hasQueuedSnapshotSave = true;
    }
    scheduleSaveIncidentReportSnapshot();
  };

  const clearFormTimers = () => {
    if (saveDebounceTimer !== null) {
      window.clearTimeout(saveDebounceTimer);
      saveDebounceTimer = null;
    }
    hasQueuedSnapshotSave = false;
  };

  return {
    loadIncidentReportSchema,
    updateIncidentReportAnswers,
    flushSaveIncidentReportSnapshot,
    clearFormTimers,
  };
};
