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
    await page.goto('/incident-report');
    await expect(page.locator('.incident-report-list-view')).toBeVisible();
  });

  test('列表页显示统计卡片', async ({ page }) => {
    await page.goto('/incident-report');
    await expect(page.locator('.stat-card').first()).toBeVisible();
  });

  test('列表页显示筛选器', async ({ page }) => {
    await page.goto('/incident-report');
    await expect(page.locator('.report-list-filters')).toBeVisible();
  });

  test('点击新建按钮跳转到创建页', async ({ page }) => {
    await page.goto('/incident-report');
    const createBtn = page.locator('.btn-create-report');
    if (await createBtn.isVisible()) {
      await createBtn.click();
      await expect(page).toHaveURL(/\/incident-report\/create/);
    }
  });
});
