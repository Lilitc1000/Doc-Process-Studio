import { ref } from 'vue';
import { fetchIncidentReportDetail, approveIncidentReport, rejectIncidentReport } from '../../../../api/incident-report';
import type { IncidentReportDetailItem } from '../../../../types/incident-report/incident-report';

export function useReportAudit() {
  const report = ref<IncidentReportDetailItem | null>(null);
  const loading = ref(false);
  const processing = ref(false);

  const load = async (reportId: string) => {
    loading.value = true;
    try {
      report.value = await fetchIncidentReportDetail(reportId);
    } finally {
      loading.value = false;
    }
  };

  const approve = async (reportId: string, comment: string) => {
    processing.value = true;
    try {
      report.value = await approveIncidentReport(reportId, comment);
    } finally {
      processing.value = false;
    }
  };

  const reject = async (reportId: string, comment: string) => {
    processing.value = true;
    try {
      report.value = await rejectIncidentReport(reportId, comment);
    } finally {
      processing.value = false;
    }
  };

  return { report, loading, processing, load, approve, reject };
}
