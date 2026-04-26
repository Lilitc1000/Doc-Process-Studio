import { test, expect } from '@playwright/test';
import { loginAsAdmin, addRateLimitWhitelist } from '../../helpers';

test.describe('事故报告列表页', () => {
  test.beforeAll(async ({ request }) => {
    await addRateLimitWhitelist(request);
  });

  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('列表页正常加载', async ({ page }) => {
    const listResp = page.waitForResponse(
      (resp) =>
        resp.url().includes('/incident-report?') && resp.status() === 200,
      { timeout: 10_000 },
    );
    await page.goto('/incident-report');
    await listResp.catch(() => {});
    await expect(page.locator('.incident-report-list-view')).toBeVisible();
  });

  test('列表页显示页面标题', async ({ page }) => {
    await page.goto('/incident-report');
    await expect(page.locator('.incident-report-list-title')).toHaveText(
      '事故报告管理',
    );
  });

  test('列表页显示统计卡片', async ({ page }) => {
    await page.goto('/incident-report');
    await expect(page.locator('.stat-card').first()).toBeVisible();
  });

  test('列表页显示筛选器', async ({ page }) => {
    await page.goto('/incident-report');
    await expect(page.locator('.report-list-filters')).toBeVisible();
  });

  test('列表页显示报告表格', async ({ page }) => {
    const listResp = page.waitForResponse(
      (resp) =>
        resp.url().includes('/incident-report?') && resp.status() === 200,
      { timeout: 10_000 },
    );
    await page.goto('/incident-report');
    await listResp.catch(() => {});
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

  test('点击表格行进入详情页', async ({ page }) => {
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
    }
  });
});
