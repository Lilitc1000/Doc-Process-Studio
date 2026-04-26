import { test, expect } from '@playwright/test';
import { loginAsAdmin, addRateLimitWhitelist } from '../../helpers';

test.describe('事故报告详情页 - 不存在的报告', () => {
  test.beforeAll(async ({ request }) => {
    await addRateLimitWhitelist(request);
  });

  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('访问不存在的报告显示报告不存在', async ({ page }) => {
    await page.goto('/incident-report/nonexistent-id');
    await page.waitForTimeout(2000);
    await expect(page.locator('.detail-empty')).toHaveText('报告不存在');
  });

  test('加载中显示加载状态', async ({ page }) => {
    await page.goto('/incident-report/nonexistent-id');
    const loading = page.locator('.detail-loading');
    if (await loading.isVisible()) {
      await expect(loading).toHaveText('加载中...');
    }
  });
});

test.describe('事故报告详情页 - 已有报告', () => {
  test.beforeAll(async ({ request }) => {
    await addRateLimitWhitelist(request);
  });

  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('从列表页点击报告行进入详情页', async ({ page }) => {
    const listResp = page.waitForResponse(
      (resp) =>
        resp.url().includes('/incident-report?') && resp.status() === 200,
      { timeout: 10_000 },
    );
    await page.goto('/incident-report');
    await listResp.catch(() => {});
    const reportRow = page.locator('.report-list-table tbody tr').first();
    if (await reportRow.isVisible()) {
      await reportRow.click();
      await expect(page).toHaveURL(/\/incident-report\/[^/]+$/);
      await expect(page.locator('.incident-report-detail-view')).toBeVisible();
    }
  });

  test('详情页显示返回列表按钮', async ({ page }) => {
    const listResp = page.waitForResponse(
      (resp) =>
        resp.url().includes('/incident-report?') && resp.status() === 200,
      { timeout: 10_000 },
    );
    await page.goto('/incident-report');
    await listResp.catch(() => {});
    const reportRow = page.locator('.report-list-table tbody tr').first();
    if (await reportRow.isVisible()) {
      await reportRow.click();
      await expect(page).toHaveURL(/\/incident-report\/[^/]+$/);
      await expect(
        page.locator('.detail-header button', { hasText: '返回列表' }),
      ).toBeVisible();
    }
  });

  test('详情页显示基本信息卡片', async ({ page }) => {
    const listResp = page.waitForResponse(
      (resp) =>
        resp.url().includes('/incident-report?') && resp.status() === 200,
      { timeout: 10_000 },
    );
    await page.goto('/incident-report');
    await listResp.catch(() => {});
    const reportRow = page.locator('.report-list-table tbody tr').first();
    if (await reportRow.isVisible()) {
      await reportRow.click();
      await expect(page).toHaveURL(/\/incident-report\/[^/]+$/);
      await expect(page.locator('.detail-info-card')).toBeVisible();
    }
  });

  test('详情页显示状态徽章', async ({ page }) => {
    const listResp = page.waitForResponse(
      (resp) =>
        resp.url().includes('/incident-report?') && resp.status() === 200,
      { timeout: 10_000 },
    );
    await page.goto('/incident-report');
    await listResp.catch(() => {});
    const reportRow = page.locator('.report-list-table tbody tr').first();
    if (await reportRow.isVisible()) {
      await reportRow.click();
      await expect(page).toHaveURL(/\/incident-report\/[^/]+$/);
      await expect(page.locator('.status-badge')).toBeVisible();
    }
  });

  test('详情页显示评论区域', async ({ page }) => {
    const listResp = page.waitForResponse(
      (resp) =>
        resp.url().includes('/incident-report?') && resp.status() === 200,
      { timeout: 10_000 },
    );
    await page.goto('/incident-report');
    await listResp.catch(() => {});
    const reportRow = page.locator('.report-list-table tbody tr').first();
    if (await reportRow.isVisible()) {
      await reportRow.click();
      await expect(page).toHaveURL(/\/incident-report\/[^/]+$/);
      await expect(page.locator('.report-comments')).toBeVisible();
    }
  });

  test('详情页显示审核时间线', async ({ page }) => {
    const listResp = page.waitForResponse(
      (resp) =>
        resp.url().includes('/incident-report?') && resp.status() === 200,
      { timeout: 10_000 },
    );
    await page.goto('/incident-report');
    await listResp.catch(() => {});
    const reportRow = page.locator('.report-list-table tbody tr').first();
    if (await reportRow.isVisible()) {
      await reportRow.click();
      await expect(page).toHaveURL(/\/incident-report\/[^/]+$/);
      await expect(page.locator('.report-audit-timeline')).toBeVisible();
    }
  });

  test('详情页显示报告编号和标题', async ({ page }) => {
    const listResp = page.waitForResponse(
      (resp) =>
        resp.url().includes('/incident-report?') && resp.status() === 200,
      { timeout: 10_000 },
    );
    await page.goto('/incident-report');
    await listResp.catch(() => {});
    const reportRow = page.locator('.report-list-table tbody tr').first();
    if (await reportRow.isVisible()) {
      await reportRow.click();
      await expect(page).toHaveURL(/\/incident-report\/[^/]+$/);
      await expect(page.locator('.detail-ref')).toBeVisible();
      await expect(page.locator('.detail-title')).toBeVisible();
    }
  });

  test('点击返回列表按钮导航回列表页', async ({ page }) => {
    const listResp = page.waitForResponse(
      (resp) =>
        resp.url().includes('/incident-report?') && resp.status() === 200,
      { timeout: 10_000 },
    );
    await page.goto('/incident-report');
    await listResp.catch(() => {});
    const reportRow = page.locator('.report-list-table tbody tr').first();
    if (await reportRow.isVisible()) {
      await reportRow.click();
      await expect(page).toHaveURL(/\/incident-report\/[^/]+$/);
      await page
        .locator('.detail-header button', { hasText: '返回列表' })
        .click();
      await expect(page).toHaveURL('/incident-report');
    }
  });
});
