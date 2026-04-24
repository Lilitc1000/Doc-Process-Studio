import { test, expect } from '@playwright/test';

test.describe('全局导航', () => {
  test('通过 header 首页按钮从子页面返回首页', async ({ page }) => {
    await page.goto('/chat');
    await expect(page.locator('.app-header-title')).toHaveText('对话');

    await page.locator('.app-header-home').click();
    await expect(page).toHaveURL('/');
    await expect(page.locator('.home-title')).toHaveText('文档处理平台');
  });

  test('从首页进入对话页面再返回首页', async ({ page }) => {
    await page.goto('/');
    await page.locator('.home-card-label', { hasText: '对话' }).click();
    await expect(page).toHaveURL('/chat');

    await page.locator('.app-header-home').click();
    await expect(page).toHaveURL('/');
  });

  test('从首页进入事故报告页面再返回首页', async ({ page }) => {
    await page.goto('/');
    await page.locator('.home-card-label', { hasText: '事故报告' }).click();
    await expect(page).toHaveURL('/incident-report');

    await page.locator('.app-header-home').click();
    await expect(page).toHaveURL('/');
  });

  test('从首页进入设置页面再返回首页', async ({ page }) => {
    await page.goto('/');
    await page.locator('.home-card-label', { hasText: '设置' }).click();
    await expect(page).toHaveURL('/settings');

    await page.locator('.app-header-home').click();
    await expect(page).toHaveURL('/');
  });

  test('直接访问各路由页面均正常加载', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('.app-header')).toHaveCount(0);

    for (const path of ['/chat', '/incident-report', '/settings']) {
      await page.goto(path);
      await expect(page.locator('.app-header')).toBeVisible();
    }
  });

  test('浏览器后退和前进导航正常工作', async ({ page }) => {
    await page.goto('/');
    await page.locator('.home-card-label', { hasText: '对话' }).click();
    await expect(page).toHaveURL('/chat');

    await page.locator('.app-header-home').click();
    await expect(page).toHaveURL('/');

    await page.goBack();
    await expect(page).toHaveURL('/chat');

    await page.goForward();
    await expect(page).toHaveURL('/');
  });
});
