import { test, expect } from '@playwright/test';
import { loginAsAdmin, addRateLimitWhitelist } from '../../helpers';

test.describe('首页', () => {
  test.beforeAll(async ({ request }) => {
    await addRateLimitWhitelist(request);
  });

  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('加载首页并显示平台标题和导航卡片', async ({ page }) => {
    await page.goto('/');

    await expect(page.locator('.home-title')).toHaveText('文档处理平台');
    await expect(page.locator('.home-card')).toHaveCount(3);

    const cardLabels = page.locator('.home-card-label');
    await expect(cardLabels.nth(0)).toHaveText('对话');
    await expect(cardLabels.nth(1)).toHaveText('事故报告');
    await expect(cardLabels.nth(2)).toHaveText('设置');
  });

  test('点击"对话"卡片导航到对话页面', async ({ page }) => {
    await page.goto('/');
    await page.locator('.home-card-label', { hasText: '对话' }).click();

    await expect(page).toHaveURL('/chat');
    await expect(page.locator('.app-header-title')).toHaveText('对话');
  });

  test('点击"事故报告"卡片导航到事故报告页面', async ({ page }) => {
    await page.goto('/');
    await page.locator('.home-card-label', { hasText: '事故报告' }).click();

    await expect(page).toHaveURL('/incident-report');
    await expect(page.locator('.app-header-title')).toHaveText('事故报告');
  });

  test('点击"设置"卡片导航到设置页面', async ({ page }) => {
    await page.goto('/');
    await page.locator('.home-card-label', { hasText: '设置' }).click();

    await expect(page).toHaveURL('/settings');
    await expect(page.locator('.app-header-title')).toHaveText('设置');
  });
});
