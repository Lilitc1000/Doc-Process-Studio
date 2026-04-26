import { ref } from 'vue';
import { fetchIncidentReportList } from '../../../../api/incident-report';
import type { IncidentReportSummaryItem } from '../../../../types/incident-report/incident-report';

export function useReportList() {
  const items = ref<IncidentReportSummaryItem[]>([]);
  const total = ref(0);
  const loading = ref(false);
  const page = ref(1);
  const pageSize = ref(20);

  const load = async (params?: {
    page?: number;
    pageSize?: number;
    status?: string;
    severity?: string;
    search?: string;
    startDate?: string;
    endDate?: string;
  }) => {
    loading.value = true;
    try {
      const response = await fetchIncidentReportList({
        page: params?.page ?? page.value,
        pageSize: params?.pageSize ?? pageSize.value,
        status: params?.status,
        severity: params?.severity,
        search: params?.search,
        startDate: params?.startDate,
        endDate: params?.endDate,
      });
      items.value = response.items;
      total.value = response.total;
      if (params?.page) page.value = params.page;
    } finally {
      loading.value = false;
    }
  };

  return { items, total, loading, page, pageSize, load };
}
