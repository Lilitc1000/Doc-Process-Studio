import { test, expect } from '@playwright/test';
import { loginAsAdmin, addRateLimitWhitelist } from '../../helpers';

test.describe('全局导航', () => {
  test.beforeAll(async ({ request }) => {
    await addRateLimitWhitelist(request);
  });

  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

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
    await expect(page.locator('.home-title')).toBeVisible();

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

  test('首页右上角显示用户头像', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('.app-header--home .user-avatar')).toBeVisible();
  });

  test('子页面显示浮动导航栏', async ({ page }) => {
    await page.goto('/chat');
    const header = page.locator('.app-header--sub');
    await expect(header).toBeVisible();
    await expect(page.locator('.app-header-home')).toBeVisible();
    await expect(page.locator('.app-header-title')).toHaveText('对话');
    await expect(page.locator('.user-avatar')).toBeVisible();
  });

  test('事故报告列表页标题不可点击', async ({ page }) => {
    await page.goto('/incident-report');
    await expect(page.locator('.app-header-title')).toHaveText('事故报告');
    await expect(page.locator('.app-header-title-btn')).not.toBeVisible();
  });

  test('访问不存在的路由显示 404 页面', async ({ page }) => {
    await page.goto('/nonexistent-page');
    await expect(page.locator('.not-found-code')).toHaveText('404');
    await expect(page.locator('.not-found-message')).toHaveText('页面不存在');
  });

  test('404 页面点击返回首页按钮导航到首页', async ({ page }) => {
    await page.goto('/nonexistent-page');
    await expect(page.locator('.not-found-code')).toBeVisible();
    await page.locator('.not-found-view .base-button').click();
    await expect(page).toHaveURL('/');
  });
});
