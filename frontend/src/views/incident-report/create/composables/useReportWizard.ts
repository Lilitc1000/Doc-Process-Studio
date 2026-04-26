import { ref } from 'vue';
import { createIncidentReport, submitIncidentReport, updateIncidentReport } from '../../../../api/incident-report';
import type { IncidentReportDetailItem } from '../../../../types/incident-report/incident-report';

export function useReportWizard() {
  const currentStep = ref(0);
  const saving = ref(false);
  const submitting = ref(false);

  const createAndSubmit = async (payload: {
    title: string;
    severity?: string;
    system?: string;
    site_id?: string;
    fault_date?: string;
    form_data?: Record<string, unknown>;
  }): Promise<IncidentReportDetailItem> => {
    submitting.value = true;
    try {
      const report = await createIncidentReport(payload);
      await submitIncidentReport(report.id);
      return report;
    } finally {
      submitting.value = false;
    }
  };

  const saveAsDraft = async (payload: {
    title: string;
    severity?: string;
    system?: string;
    site_id?: string;
    fault_date?: string;
    form_data?: Record<string, unknown>;
  }): Promise<IncidentReportDetailItem> => {
    saving.value = true;
    try {
      return await createIncidentReport(payload);
    } finally {
      saving.value = false;
    }
  };

  return { currentStep, saving, submitting, createAndSubmit, saveAsDraft };
}
