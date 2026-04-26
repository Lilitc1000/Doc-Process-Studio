import { test, expect } from '@playwright/test';
import { loginAsAdmin, addRateLimitWhitelist } from '../../helpers';

test.describe('事故报告统计分析页', () => {
  test.beforeAll(async ({ request }) => {
    await addRateLimitWhitelist(request);
  });

  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('统计分析页正常加载', async ({ page }) => {
    await page.goto('/incident-report/analytics');
    await expect(page.locator('.incident-report-analytics-view')).toBeVisible();
  });

  test('统计分析页显示标题', async ({ page }) => {
    await page.goto('/incident-report/analytics');
    await expect(page.locator('.analytics-header h1')).toHaveText('统计分析');
  });

  test('统计分析页显示返回列表按钮', async ({ page }) => {
    await page.goto('/incident-report/analytics');
    await expect(page.locator('.analytics-header button')).toContainText(
      '返回列表',
    );
  });

  test('统计分析页显示统计卡片', async ({ page }) => {
    const overviewResp = page.waitForResponse(
      (resp) =>
        resp.url().includes('/incident-report/analytics/overview') &&
        resp.status() === 200,
      { timeout: 10_000 },
    );
    await page.goto('/incident-report/analytics');
    await overviewResp.catch(() => {});
    await expect(page.locator('.stats-cards')).toBeVisible();
  });

  test('统计分析页显示图表区域', async ({ page }) => {
    await page.goto('/incident-report/analytics');
    await page.waitForTimeout(2000);
    await expect(page.locator('.analytics-charts')).toBeVisible();
  });

  test('点击返回按钮导航到列表页', async ({ page }) => {
    await page.goto('/incident-report/analytics');
    await page.locator('.analytics-header button').click();
    await expect(page).toHaveURL('/incident-report');
  });
});
