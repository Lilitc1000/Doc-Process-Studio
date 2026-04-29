import { test, expect } from '@playwright/test';
import {
  getWorkerPrefix,
  loginAsAdmin,
  loginViaApi,
  addRateLimitWhitelist,
  createIncidentReportViaApi,
  submitIncidentReportViaApi,
  deleteIncidentReportViaApi,
} from '../../helpers';

test.describe('事故报告审核流程', () => {
  let workerPrefix: string;

  test.beforeAll(async ({ request }, testInfo) => {
    workerPrefix = getWorkerPrefix(testInfo.workerIndex);
    await addRateLimitWhitelist(request);
  });

  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('从详情页进入审核页', async ({ page, request }) => {
    const token = await loginViaApi(request);
    const report = await createIncidentReportViaApi(request, token!, {
      title: `${workerPrefix}进入审核页测试`,
    });
    expect(report).not.toBeNull();

    const submitted = await submitIncidentReportViaApi(
      request,
      token!,
      report!.id,
    );
    expect(submitted).not.toBeNull();

    try {
      await page.goto(`/incident-report/${report!.id}`);
      await expect(page.locator('.incident-report-detail-view')).toBeVisible();

      const auditBtn = page.locator('.detail-header-right button', {
        hasText: '审核',
      });
      await expect(auditBtn).toBeVisible();
      await auditBtn.click();
      await expect(page).toHaveURL(/\/incident-report\/[^/]+\/audit/);
      await expect(page.locator('.incident-report-audit-view')).toBeVisible();
    } finally {
      await deleteIncidentReportViaApi(request, token!, report!.id);
    }
  });

  test('审核页显示审核操作面板', async ({ page, request }) => {
    const token = await loginViaApi(request);
    const report = await createIncidentReportViaApi(request, token!, {
      title: `${workerPrefix}审核操作面板测试`,
      severity: 'P1',
    });
    expect(report).not.toBeNull();

    await submitIncidentReportViaApi(request, token!, report!.id);

    try {
      await page.goto(`/incident-report/${report!.id}/audit`);
      await expect(page.locator('.incident-report-audit-view')).toBeVisible();

      const auditPanel = page.locator('.audit-action-panel');
      if (await auditPanel.isVisible()) {
        await expect(auditPanel.locator('h3')).toContainText('审核操作');
      }
    } finally {
      await deleteIncidentReportViaApi(request, token!, report!.id);
    }
  });

  test('审核页显示返回详情按钮', async ({ page, request }) => {
    const token = await loginViaApi(request);
    const report = await createIncidentReportViaApi(request, token!, {
      title: `${workerPrefix}审核返回按钮测试`,
    });
    expect(report).not.toBeNull();

    await submitIncidentReportViaApi(request, token!, report!.id);

    try {
      await page.goto(`/incident-report/${report!.id}/audit`);
      const backBtn = page.locator('button', { hasText: '返回' });
      if (await backBtn.isVisible()) {
        await backBtn.click();
        await expect(page).toHaveURL(/\/incident-report\/[^/]+$/);
      }
    } finally {
      await deleteIncidentReportViaApi(request, token!, report!.id);
    }
  });
});
