import { ref } from 'vue';
import { fetchIncidentReportDetail, updateIncidentReport } from '../../../../api/incident-report';
import type { IncidentReportDetailItem } from '../../../../types/incident-report/incident-report';

export function useReportEdit() {
  const report = ref<IncidentReportDetailItem | null>(null);
  const loading = ref(false);
  const saving = ref(false);

  const load = async (reportId: string) => {
    loading.value = true;
    try {
      report.value = await fetchIncidentReportDetail(reportId);
    } finally {
      loading.value = false;
    }
  };

  const save = async (reportId: string, payload: {
    title?: string;
    severity?: string;
    system?: string;
    site_id?: string;
    fault_date?: string;
    form_data?: Record<string, unknown>;
  }) => {
    saving.value = true;
    try {
      report.value = await updateIncidentReport(reportId, payload);
    } finally {
      saving.value = false;
    }
  };

  return { report, loading, saving, load, save };
}
