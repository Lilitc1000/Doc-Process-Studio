import { ref } from 'vue';
import {
  fetchIncidentReportDetail,
  fetchIncidentReportAuditLogs,
} from '../../../api/incident-report';
import type {
  IncidentReportDetailItem,
  IncidentAuditLogEntry,
} from '../../../types/incident-report';

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
    } catch {
      report.value = null;
      auditLogs.value = [];
    } finally {
      loading.value = false;
    }
  };

  const refreshLogs = async (reportId: string) => {
    try {
      auditLogs.value = await fetchIncidentReportAuditLogs(reportId);
    } catch {
      // keep existing logs on refresh failure
    }
  };

  return { report, auditLogs, loading, load, refreshLogs };
}
