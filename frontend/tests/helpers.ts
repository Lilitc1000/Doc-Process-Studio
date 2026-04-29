import { expect } from '@playwright/test';
import type { Page, APIRequestContext } from '@playwright/test';

export function getWorkerPrefix(workerIndex: number): string {
  return `e2e_w${workerIndex}_`;
}

export async function loginAsAdmin(page: Page) {
  await page.goto('/login');
  await page.locator('input').nth(0).fill('admin');
  await page.locator('input').nth(1).fill('admin123');
  await page.locator('button[type="submit"]').click();
  await expect(page).toHaveURL('/', { timeout: 10_000 });
}

export async function loginAs(page: Page, username: string, password: string) {
  await page.goto('/login');
  await page.locator('input').nth(0).fill(username);
  await page.locator('input').nth(1).fill(password);
  await page.locator('button[type="submit"]').click();
  await expect(page).toHaveURL('/', { timeout: 10_000 });
}

export async function loginViaApi(request: APIRequestContext) {
  const resp = await request.post('/api/auth/login', {
    form: { username: 'admin', password: 'admin123' },
  });
  if (!resp.ok()) return null;
  const data = await resp.json();
  return data.access_token as string;
}

export async function loginViaApiAs(
  request: APIRequestContext,
  username: string,
  password: string,
) {
  const resp = await request.post('/api/auth/login', {
    form: { username, password },
  });
  if (!resp.ok()) return null;
  const data = await resp.json();
  return data.access_token as string;
}

export async function addRateLimitWhitelist(request: APIRequestContext) {
  await request.post('/api/auth/rate-limit-whitelist');
}

export async function registerUserViaApi(
  request: APIRequestContext,
  username: string,
  password: string,
) {
  const registerResp = await request.post('/api/auth/register', {
    data: { username, password },
  });
  if (registerResp.ok()) {
    return registerResp.json() as Promise<{
      user_id: string;
      username: string;
    }>;
  }
  if (registerResp.status() === 409) {
    const loginResp = await request.post('/api/auth/login', {
      form: { username, password },
    });
    if (loginResp.ok()) {
      const token = (await loginResp.json()).access_token as string;
      const meResp = await request.get('/api/auth/me', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (meResp.ok()) {
        const me = await meResp.json();
        return { user_id: me.user_id, username: me.username } as {
          user_id: string;
          username: string;
        };
      }
    }
  }
  return null;
}

export async function assignIncidentRoleViaApi(
  request: APIRequestContext,
  token: string,
  userId: string,
  role: string,
) {
  const resp = await request.post('/api/incident-report/roles', {
    headers: { Authorization: `Bearer ${token}` },
    data: { user_id: userId, role },
  });
  return resp.ok();
}

export async function createIncidentReportViaApi(
  request: APIRequestContext,
  token: string,
  payload: {
    title: string;
    severity?: string;
    system?: string;
    site_id?: string;
    fault_date?: string;
    form_data?: Record<string, unknown>;
  },
) {
  const uniqueRef = `E2E-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
  const defaultFormData: Record<string, unknown> = {
    manual_reference_no: uniqueRef,
    manual_fault_date: '2026-04-27',
    manual_reporting_person: 'E2E Tester',
    manual_site_id: payload.site_id ?? 'SITE-E2E',
    manual_system: payload.system ?? 'E2E System',
    manual_fault_symptom: 'E2E test fault symptom',
    manual_severity: payload.severity ?? 'P2',
  };
  const mergedFormData = { ...defaultFormData, ...payload.form_data };
  const data = {
    ...payload,
    severity: payload.severity ?? 'P2',
    form_data: mergedFormData,
  };
  const resp = await request.post('/api/incident-report/reports', {
    headers: { Authorization: `Bearer ${token}` },
    data,
  });
  if (!resp.ok()) {
    console.error(
      `createIncidentReportViaApi failed: ${resp.status()} ${await resp.text()}`,
    );
    return null;
  }
  return resp.json() as Promise<{
    id: string;
    ref_no: string;
    title: string;
    status: string;
    [key: string]: unknown;
  }>;
}

export async function submitIncidentReportViaApi(
  request: APIRequestContext,
  token: string,
  reportId: string,
) {
  const resp = await request.post(
    `/api/incident-report/reports/${reportId}/submit`,
    {
      headers: { Authorization: `Bearer ${token}` },
    },
  );
  if (!resp.ok()) {
    console.error(
      `submitIncidentReportViaApi failed: ${resp.status()} ${await resp.text()}`,
    );
    return null;
  }
  return resp.json() as Promise<{
    id: string;
    status: string;
    [key: string]: unknown;
  }>;
}

export async function approveIncidentReportViaApi(
  request: APIRequestContext,
  token: string,
  reportId: string,
  comment: string,
) {
  const resp = await request.post(
    `/api/incident-report/reports/${reportId}/approve`,
    {
      headers: { Authorization: `Bearer ${token}` },
      data: { comment },
    },
  );
  if (!resp.ok()) {
    console.error(
      `approveIncidentReportViaApi failed: ${resp.status()} ${await resp.text()}`,
    );
    return null;
  }
  return resp.json() as Promise<{
    id: string;
    status: string;
    [key: string]: unknown;
  }>;
}

export async function rejectIncidentReportViaApi(
  request: APIRequestContext,
  token: string,
  reportId: string,
  comment: string,
) {
  const resp = await request.post(
    `/api/incident-report/reports/${reportId}/reject`,
    {
      headers: { Authorization: `Bearer ${token}` },
      data: { comment },
    },
  );
  if (!resp.ok()) {
    console.error(
      `rejectIncidentReportViaApi failed: ${resp.status()} ${await resp.text()}`,
    );
    return null;
  }
  return resp.json() as Promise<{
    id: string;
    status: string;
    [key: string]: unknown;
  }>;
}

export async function assignHandlerViaApi(
  request: APIRequestContext,
  token: string,
  reportId: string,
  assigneeId: string,
) {
  const resp = await request.post(
    `/api/incident-report/reports/${reportId}/assign`,
    {
      headers: { Authorization: `Bearer ${token}` },
      data: { assignee_id: assigneeId },
    },
  );
  if (!resp.ok()) {
    console.error(
      `assignHandlerViaApi failed: ${resp.status()} ${await resp.text()}`,
    );
    return null;
  }
  return resp.json() as Promise<{
    id: string;
    status: string;
    [key: string]: unknown;
  }>;
}

export async function closeIncidentReportViaApi(
  request: APIRequestContext,
  token: string,
  reportId: string,
  comment?: string,
) {
  const resp = await request.post(
    `/api/incident-report/reports/${reportId}/close`,
    {
      headers: { Authorization: `Bearer ${token}` },
      data: comment ? { comment } : undefined,
    },
  );
  if (!resp.ok()) {
    console.error(
      `closeIncidentReportViaApi failed: ${resp.status()} ${await resp.text()}`,
    );
    return null;
  }
  return resp.json() as Promise<{
    id: string;
    status: string;
    [key: string]: unknown;
  }>;
}

export async function deleteIncidentReportViaApi(
  request: APIRequestContext,
  token: string,
  reportId: string,
) {
  const resp = await request.delete(
    `/api/incident-report/reports/${reportId}`,
    {
      headers: { Authorization: `Bearer ${token}` },
    },
  );
  return resp.ok();
}

export async function deleteTestUsersByPrefix(
  request: APIRequestContext,
  prefix: string,
) {
  await request.delete(`/api/auth/users/by-prefix/${prefix}`);
}

export async function deleteReportsByPrefix(
  request: APIRequestContext,
  token: string,
  prefix: string,
) {
  const resp = await request.get('/api/incident-report/reports', {
    headers: { Authorization: `Bearer ${token}` },
    params: { search: prefix, page_size: 100 },
  });
  if (!resp.ok()) return;
  const data = await resp.json();
  const items = data.items ?? data.reports ?? [];
  for (const report of items) {
    if (report.title?.startsWith(prefix)) {
      await request.delete(`/api/incident-report/reports/${report.id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
    }
  }
}

export async function cleanupWorkerData(
  request: APIRequestContext,
  workerPrefix: string,
) {
  const token = await loginViaApi(request);
  if (token) {
    await deleteReportsByPrefix(request, token, workerPrefix);
  }
  await deleteTestUsersByPrefix(request, workerPrefix);
}
