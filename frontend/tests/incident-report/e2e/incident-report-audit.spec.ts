import { test, expect } from '@playwright/test';
import {
  getWorkerPrefix,
  loginAsAdmin,
  loginViaApi,
  addRateLimitWhitelist,
  createIncidentReportViaApi,
  submitIncidentReportViaApi,
  deleteIncidentReportViaApi,
  cleanupWorkerData,
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

  test.afterAll(async ({ request }) => {
    await cleanupWorkerData(request, workerPrefix);
  });

  test('从详情页点击审核按钮弹出审核对话框', async ({ page, request }) => {
    const token = await loginViaApi(request);
    const report = await createIncidentReportViaApi(request, token!, {
      title: `${workerPrefix}审核弹窗测试`,
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
      await expect(page.locator('.incident-report-detail-view')).toBeVisible({
        timeout: 10_000,
      });

      const auditBtn = page.locator('.detail-header-right button', {
        hasText: '审核',
      });
      await expect(auditBtn).toBeVisible();
      await auditBtn.click();

      await expect(page.locator('.audit-dialog')).toBeVisible();
      await expect(
        page.locator('.audit-dialog .form-label', { hasText: '审核意见' }),
      ).toBeVisible();
    } finally {
      await deleteIncidentReportViaApi(request, token!, report!.id);
    }
  });

  test('审核对话框包含驳回和通过按钮', async ({ page, request }) => {
    const token = await loginViaApi(request);
    const report = await createIncidentReportViaApi(request, token!, {
      title: `${workerPrefix}审核按钮测试`,
      severity: 'P1',
    });
    expect(report).not.toBeNull();

    await submitIncidentReportViaApi(request, token!, report!.id);

    try {
      await page.goto(`/incident-report/${report!.id}`);
      await expect(page.locator('.incident-report-detail-view')).toBeVisible({
        timeout: 10_000,
      });

      const auditBtn = page.locator('.detail-header-right button', {
        hasText: '审核',
      });
      await auditBtn.click();
      await expect(page.locator('.audit-dialog')).toBeVisible();

      await expect(
        page.locator('.audit-dialog-footer button', { hasText: '驳回' }),
      ).toBeVisible();
      await expect(
        page.locator('.audit-dialog-footer button', { hasText: '通过' }),
      ).toBeVisible();
    } finally {
      await deleteIncidentReportViaApi(request, token!, report!.id);
    }
  });

  test('点击遮罩层关闭审核对话框', async ({ page, request }) => {
    const token = await loginViaApi(request);
    const report = await createIncidentReportViaApi(request, token!, {
      title: `${workerPrefix}审核关闭测试`,
    });
    expect(report).not.toBeNull();

    await submitIncidentReportViaApi(request, token!, report!.id);

    try {
      await page.goto(`/incident-report/${report!.id}`);
      await expect(page.locator('.incident-report-detail-view')).toBeVisible({
        timeout: 10_000,
      });

      const auditBtn = page.locator('.detail-header-right button', {
        hasText: '审核',
      });
      await auditBtn.click();
      await expect(page.locator('.audit-dialog')).toBeVisible();

      await page
        .locator('.audit-overlay')
        .click({ position: { x: 10, y: 10 } });
      await expect(page.locator('.audit-dialog')).not.toBeVisible();
    } finally {
      await deleteIncidentReportViaApi(request, token!, report!.id);
    }
  });
});
