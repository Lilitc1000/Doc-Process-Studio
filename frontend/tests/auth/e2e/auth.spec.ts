import { test, expect } from '@playwright/test';
import { E2E_PREFIX, addRateLimitWhitelist } from '../../helpers';

test.describe('认证流程', () => {
  test.beforeAll(async ({ request }) => {
    await addRateLimitWhitelist(request);
  });

  test('未登录访问 /chat 重定向到 /login', async ({ page }) => {
    await page.goto('/chat');
    await expect(page).toHaveURL(/\/login/);
  });

  test('未登录访问 /incident-report 重定向到 /login', async ({ page }) => {
    await page.goto('/incident-report');
    await expect(page).toHaveURL(/\/login/);
  });

  test('未登录访问 /settings 重定向到 /login', async ({ page }) => {
    await page.goto('/settings');
    await expect(page).toHaveURL(/\/login/);
  });

  test('注册页面渲染正确', async ({ page }) => {
    await page.goto('/register');
    await expect(page.locator('h1')).toHaveText('注册');
    await expect(page.locator('.register-link')).toBeVisible();
  });

  test('注册新用户成功后跳转登录页', async ({ page }) => {
    await page.goto('/register');
    await page
      .locator('input')
      .nth(0)
      .fill(`${E2E_PREFIX}${Date.now() % 100000}`);
    await page.locator('input').nth(1).fill('test123456');
    await page.locator('input').nth(2).fill('test123456');
    await page.locator('button[type="submit"]').click();
    await expect(page).toHaveURL(/\/login/, { timeout: 10_000 });
  });

  test('重复用户名注册提示错误', async ({ page }) => {
    await page.goto('/register');

    await page.locator('input').nth(0).fill('admin');
    await page.locator('input').nth(1).fill('password123');
    await page.locator('input').nth(2).fill('password123');

    await page.locator('button[type="submit"]').click();

    await expect(page.locator('.register-error')).toBeVisible({
      timeout: 10_000,
    });
  });

  test('登录成功后跳转首页', async ({ page }) => {
    await page.goto('/login');

    await page.locator('input').nth(0).fill('admin');
    await page.locator('input').nth(1).fill('admin123');

    await page.locator('button[type="submit"]').click();

    await expect(page).toHaveURL('/', { timeout: 10_000 });
  });

  test('登录后导航到 /chat 页面显示用户头像', async ({ page }) => {
    await page.goto('/login');

    await page.locator('input').nth(0).fill('admin');
    await page.locator('input').nth(1).fill('admin123');

    await page.locator('button[type="submit"]').click();
    await expect(page).toHaveURL('/', { timeout: 10_000 });

    await page.goto('/chat');
    await expect(page.locator('.user-avatar')).toBeVisible({ timeout: 5_000 });
  });

  test('错误密码提示错误信息', async ({ page }) => {
    await page.goto('/login');

    await page.locator('input').nth(0).fill('admin');
    await page.locator('input').nth(1).fill('wrongpassword');

    await page.locator('button[type="submit"]').click();

    await expect(page.locator('.login-error')).toBeVisible({
      timeout: 10_000,
    });
  });

  test('登出后访问受保护路由重定向登录页', async ({ page }) => {
    await page.goto('/login');

    await page.locator('input').nth(0).fill('admin');
    await page.locator('input').nth(1).fill('admin123');

    await page.locator('button[type="submit"]').click();
    await expect(page).toHaveURL('/', { timeout: 10_000 });

    await page.goto('/chat');
    await expect(page.locator('.user-menu-trigger')).toBeVisible({
      timeout: 5_000,
    });
    await page.locator('.user-menu-trigger').click();

    await expect(page.locator('.user-menu-item-danger')).toBeVisible();
    await page.locator('.user-menu-item-danger').click();

    await expect(page).toHaveURL(/\/login/, { timeout: 10_000 });

    await page.goto('/chat');
    await expect(page).toHaveURL(/\/login/);
  });

  test('已登录用户访问 /login 重定向到首页', async ({ page }) => {
    await page.goto('/login');

    await page.locator('input').nth(0).fill('admin');
    await page.locator('input').nth(1).fill('admin123');

    await page.locator('button[type="submit"]').click();
    await expect(page).toHaveURL('/', { timeout: 10_000 });

    await page.goto('/login');
    await expect(page).toHaveURL('/', { timeout: 5_000 });
  });

  test('用户信息弹窗可打开和关闭', async ({ page }) => {
    await page.goto('/login');

    await page.locator('input').nth(0).fill('admin');
    await page.locator('input').nth(1).fill('admin123');

    await page.locator('button[type="submit"]').click();
    await expect(page).toHaveURL('/', { timeout: 10_000 });

    await page.goto('/chat');
    await expect(page.locator('.user-menu-trigger')).toBeVisible({
      timeout: 5_000,
    });
    await page.locator('.user-menu-trigger').click();

    await expect(page.locator('.user-menu-item').first()).toBeVisible();
    await page.locator('.user-menu-item').first().click();

    await expect(page.locator('.modal-container')).toBeVisible({
      timeout: 5_000,
    });

    await page.locator('.modal-overlay').click({ position: { x: 0, y: 0 } });
  });

  test.afterAll(async ({ request }) => {
    try {
      await request.delete(`/api/auth/users/by-prefix/${E2E_PREFIX}`);
    } catch {
      // ignore cleanup errors
    }
  });
});
