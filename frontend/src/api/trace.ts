import { apiClient } from './client';
import type { TraceReplayResponse } from '../types/trace';

export const fetchAgentTraceReplay = async (
  traceId: string,
  options?: { tenantId?: string },
) => {
  const response = await apiClient.get<TraceReplayResponse>(
    `/system/agent-traces/${encodeURIComponent(traceId)}`,
    {
      params: options?.tenantId ? { tenant_id: options.tenantId } : undefined,
    },
  );
  return response.data;
};
