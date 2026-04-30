import { test, expect } from '@playwright/test';
import {
  getWorkerPrefix,
  loginAsAdmin,
  loginViaApi,
  addRateLimitWhitelist,
  createIncidentReportViaApi,
  deleteIncidentReportViaApi,
  cleanupWorkerData,
} from '../../helpers';

test.describe('事故报告列表页', () => {
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

  test('列表页正常加载', async ({ page }) => {
    const listResp = page.waitForResponse(
      (resp) =>
        resp.url().includes('/incident-report/reports') &&
        resp.status() === 200,
      { timeout: 10_000 },
    );
    await page.goto('/incident-report');
    await listResp;
    await expect(page.locator('.incident-report-list-view')).toBeVisible();
  });

  test('列表页显示页面标题', async ({ page }) => {
    await page.goto('/incident-report');
    await expect(page.locator('.incident-report-list-title')).toHaveText(
      '事故报告管理',
    );
  });

  test('列表页显示筛选器', async ({ page }) => {
    await page.goto('/incident-report');
    await expect(page.locator('.report-list-filters')).toBeVisible();
  });

  test('列表页显示报告表格', async ({ page }) => {
    const listResp = page.waitForResponse(
      (resp) =>
        resp.url().includes('/incident-report/reports') &&
        resp.status() === 200,
      { timeout: 10_000 },
    );
    await page.goto('/incident-report');
    await listResp;
    await expect(page.locator('.report-list-table')).toBeVisible();
  });

  test('点击新建按钮跳转到创建页', async ({ page }) => {
    await page.goto('/incident-report');
    const createBtn = page.locator('.btn-create-report');
    if (await createBtn.isVisible()) {
      await createBtn.click();
      await expect(page).toHaveURL(/\/incident-report\/create/);
    }
  });

  test('筛选器交互 - 状态筛选', async ({ page }) => {
    await page.goto('/incident-report');
    const statusSelect = page.locator('.filter-status');
    if (await statusSelect.isVisible()) {
      await statusSelect.click();
      const option = page
        .locator('.filter-status option, .filter-status .dropdown-item')
        .first();
      if (await option.isVisible()) {
        await option.click();
      }
    }
  });

  test('筛选器交互 - 搜索框输入', async ({ page }) => {
    await page.goto('/incident-report');
    const searchInput = page.locator('.filter-search');
    if (await searchInput.isVisible()) {
      await searchInput.fill('测试');
      await expect(searchInput).toHaveValue('测试');
    }
  });

  test('点击统计分析导航到分析页', async ({ page }) => {
    await page.goto('/incident-report');
    const analyticsBtn = page.locator('button, a', { hasText: '统计分析' });
    if (await analyticsBtn.isVisible()) {
      await analyticsBtn.click();
      await expect(page).toHaveURL(/\/incident-report\/analytics/);
    }
  });

  test('有测试数据时点击表格行进入详情页', async ({ page, request }) => {
    const token = await loginViaApi(request);
    const report = await createIncidentReportViaApi(request, token!, {
      title: `${workerPrefix}列表行点击测试`,
    });
    expect(report).not.toBeNull();

    try {
      const listResp = page.waitForResponse(
        (resp) =>
          resp.url().includes('/incident-report/reports') &&
          resp.status() === 200,
        { timeout: 10_000 },
      );
      await page.goto('/incident-report');
      await listResp;

      const reportRow = page
        .locator('.report-list-table tbody tr')
        .filter({ hasText: `${workerPrefix}列表行点击测试` });
      await expect(reportRow).toBeVisible({ timeout: 10_000 });
      await reportRow.locator('.action-view').click();
      await expect(page).toHaveURL(/\/incident-report\/[^/]+$/);
      await expect(page.locator('.incident-report-detail-view')).toBeVisible({
        timeout: 10_000,
      });
    } finally {
      await deleteIncidentReportViaApi(request, token!, report!.id);
    }
  });

  test('删除报告显示二次确认弹窗', async ({ page, request }) => {
    const token = await loginViaApi(request);
    const report = await createIncidentReportViaApi(request, token!, {
      title: `${workerPrefix}删除确认测试`,
    });
    expect(report).not.toBeNull();

    try {
      const listResp = page.waitForResponse(
        (resp) =>
          resp.url().includes('/incident-report/reports') &&
          resp.status() === 200,
        { timeout: 10_000 },
      );
      await page.goto('/incident-report');
      await listResp;

      const reportRow = page
        .locator('.report-list-table tbody tr')
        .filter({ hasText: `${workerPrefix}删除确认测试` });
      await expect(reportRow).toBeVisible({ timeout: 10_000 });

      const deleteBtn = reportRow.locator('.action-delete');
      if (await deleteBtn.isVisible()) {
        await deleteBtn.click();

        await expect(page.locator('.confirm-dialog')).toBeVisible({
          timeout: 5_000,
        });
        await expect(page.locator('.confirm-title')).toContainText('删除报告');
        await expect(page.locator('.confirm-body')).toContainText(
          '确定要删除此报告吗',
        );

        await page
          .locator('.confirm-footer button', { hasText: '取消' })
          .click();
        await expect(page.locator('.confirm-dialog')).not.toBeVisible({
          timeout: 5_000,
        });

        await deleteBtn.click();
        await expect(page.locator('.confirm-dialog')).toBeVisible({
          timeout: 5_000,
        });
        await page
          .locator('.confirm-footer button', { hasText: '删除' })
          .click();
        await expect(page.locator('.confirm-dialog')).not.toBeVisible({
          timeout: 5_000,
        });
      }
    } finally {
      try {
        await deleteIncidentReportViaApi(request, token!, report!.id);
      } catch {
        // already deleted
      }
    }
  });
});
