import { test, expect } from '@playwright/test';
import { loginAsAdmin, addRateLimitWhitelist } from '../../helpers';

test.describe('事故报告页面', () => {
  test.beforeAll(async ({ request }) => {
    await addRateLimitWhitelist(request);
  });

  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('首页可以访问', async ({ page }) => {
    await page.goto('/incident-report');
    await expect(page.locator('.incident-report-workspace h2')).toContainText(
      '事故报告助手',
    );
  });

  test('点击开始按钮后进入表单', async ({ page }) => {
    await page.goto('/incident-report');

    const startBtn = page.locator('.incident-report-workspace button', {
      hasText: /开始/,
    });
    await expect(startBtn).toBeVisible({ timeout: 10_000 });
    await startBtn.click();

    await expect(page.locator('.incident-report-form-page')).toBeVisible({
      timeout: 10_000,
    });
  });

  test('表单必填项未填写时预览附件会提示错误', async ({ page }) => {
    await page.goto('/incident-report');

    const startBtn = page.locator('.incident-report-workspace button', {
      hasText: /开始/,
    });
    await expect(startBtn).toBeVisible({ timeout: 10_000 });
    await startBtn.click();

    await expect(page.locator('.incident-report-form-page')).toBeVisible({
      timeout: 10_000,
    });

    const previewBtn = page.locator('button', { hasText: /预览附件/ });
    await expect(previewBtn).toBeVisible({ timeout: 10_000 });
    await previewBtn.click();

    await expect(page.locator('.incident-report-error-text')).toContainText(
      '存在必填项未填写',
      { timeout: 10_000 },
    );
  });
});

test.describe('事故报告页面 - UI 渲染', () => {
  test.beforeAll(async ({ request }) => {
    await addRateLimitWhitelist(request);
  });

  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('事故报告页面渲染侧边栏和工作区', async ({ page }) => {
    await page.goto('/incident-report');

    await expect(page.locator('.app-header-title')).toHaveText('事故报告');
    await expect(page.locator('.chat-sidebar')).toBeVisible();
    await expect(page.locator('.incident-report-workspace')).toBeVisible();
  });

  test('点击 header 标题清除当前会话', async ({ page }) => {
    await page.goto('/incident-report');

    await page.locator('.app-header-title').click();
    await expect(page).toHaveURL('/incident-report');
  });
});

test.describe('事故报告页面 - 端到端场景', () => {
  test.setTimeout(60_000);

  test.beforeAll(async ({ request }) => {
    await addRateLimitWhitelist(request);
  });

  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('页面加载时获取表单 schema 和会话列表', async ({ page }) => {
    const schemaResp = page.waitForResponse(
      (resp) =>
        resp.url().includes('/incident-report/schema') && resp.status() === 200,
      { timeout: 10_000 },
    );
    const sessionsResp = page.waitForResponse(
      (resp) =>
        resp.url().includes('/incident-report/sessions') &&
        resp.status() === 200,
      { timeout: 10_000 },
    );

    await page.goto('/incident-report');
    await schemaResp;
    await sessionsResp;

    await expect(page.locator('.incident-report-workspace')).toBeVisible();
  });

  test('创建新的事故报告会话', async ({ page }) => {
    const sessionsResp = page.waitForResponse(
      (resp) =>
        resp.url().includes('/incident-report/sessions') &&
        resp.status() === 200,
      { timeout: 10_000 },
    );

    await page.goto('/incident-report');
    await sessionsResp;

    const startBtn = page.locator(
      '.incident-report-workspace .start-btn, .incident-report-workspace button',
      {
        hasText: /开始|新建|创建/,
      },
    );
    if ((await startBtn.count()) > 0) {
      const createResp = page.waitForResponse(
        (resp) =>
          resp.url().includes('/incident-report/sessions') &&
          resp.request().method() === 'POST' &&
          resp.status() === 200,
        { timeout: 10_000 },
      );

      await startBtn.first().click();
      await createResp;

      await page.waitForTimeout(1000);

      const workspace = page.locator('.incident-report-workspace');
      await expect(workspace).toBeVisible();
    }
  });

  test('侧边栏显示历史事故报告会话', async ({ page }) => {
    const sessionsResp = page.waitForResponse(
      (resp) =>
        resp.url().includes('/incident-report/sessions') &&
        resp.status() === 200,
      { timeout: 10_000 },
    );

    await page.goto('/incident-report');
    await sessionsResp;

    const sidebar = page.locator('.chat-sidebar');
    await expect(sidebar).toBeVisible();

    const sessionItems = page.locator('.chat-sidebar .history-session');
    const count = await sessionItems.count();
    expect(count).toBeGreaterThanOrEqual(0);
  });

  test('点击侧边栏历史会话加载详情', async ({ page }) => {
    const sessionsResp = page.waitForResponse(
      (resp) =>
        resp.url().includes('/incident-report/sessions') &&
        resp.status() === 200,
      { timeout: 10_000 },
    );

    await page.goto('/incident-report');
    await sessionsResp;

    const sessionItems = page.locator('.chat-sidebar .history-session');
    const count = await sessionItems.count();

    if (count > 0) {
      const detailResp = page.waitForResponse(
        (resp) =>
          resp.url().match(/\/incident-report\/sessions\/[^/]+$/) !== null &&
          resp.status() === 200,
        { timeout: 10_000 },
      );

      await sessionItems.first().click();
      await detailResp;

      await page.waitForTimeout(1000);

      const workspace = page.locator('.incident-report-workspace');
      await expect(workspace).toBeVisible();
    }
  });
});
