import { ref } from 'vue';
import {
  fetchIncidentReportDetail,
  fetchIncidentReportAuditLogs,
} from '../../../../api/incident-report';
import type {
  IncidentReportDetailItem,
  IncidentAuditLogEntry,
} from '../../../../types/incident-report/incident-report';

export function useReportDetail() {
  const report = ref<IncidentReportDetailItem | null>(null);
  const auditLogs = ref<IncidentAuditLogEntry[]>([]);
  const loading = ref(false);

  const load = async (reportId: string) => {
    loading.value = true;
    try {
      const [reportData, logs] = await Promise.all([
        fetchIncidentReportDetail(reportId),
        fetchIncidentReportAuditLogs(reportId),
      ]);
      report.value = reportData;
      auditLogs.value = logs;
    } finally {
      loading.value = false;
    }
  };

  return { report, auditLogs, loading, load };
}
