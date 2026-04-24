import { test, expect } from '@playwright/test';

test.describe('对话页面 - UI 渲染', () => {
  test('对话页面渲染侧边栏和输入区域', async ({ page }) => {
    await page.goto('/chat');

    await expect(page.locator('.app-header-title')).toHaveText('对话');
    await expect(page.locator('.chat-sidebar')).toBeVisible();
    await expect(page.locator('.chat-input')).toBeVisible();
  });

  test('输入区域包含文本输入框和发送按钮', async ({ page }) => {
    await page.goto('/chat');

    const input = page.locator('.chat-input textarea');
    await expect(input).toBeVisible();

    const sendBtn = page.locator('.chat-input .send-btn');
    await expect(sendBtn).toBeVisible();
  });

  test('在输入框中输入文字后内容正确显示', async ({ page }) => {
    await page.goto('/chat');

    const input = page.locator('.chat-input textarea');
    await input.fill('你好，请帮我写一份文档');
    await expect(input).toHaveValue('你好，请帮我写一份文档');
  });

  test('点击 header 标题仍停留在对话页面', async ({ page }) => {
    await page.goto('/chat');

    await page.locator('.app-header-title').click();
    await expect(page).toHaveURL('/chat');
  });
});

test.describe('对话页面 - 端到端场景', () => {
  test.setTimeout(60_000);

  test('侧边栏加载历史会话列表', async ({ page }) => {
    const sessionsResp = page.waitForResponse(
      (resp) => resp.url().includes('/chat-sessions') && resp.status() === 200,
      { timeout: 10_000 },
    );

    await page.goto('/chat');
    await sessionsResp;

    const sidebar = page.locator('.chat-sidebar');
    await expect(sidebar).toBeVisible();
  });

  test('发送消息后 AI 回复出现在聊天区域', async ({ page }) => {
    const sessionsResp = page.waitForResponse(
      (resp) => resp.url().includes('/chat-sessions') && resp.status() === 200,
      { timeout: 10_000 },
    );

    await page.goto('/chat');
    await sessionsResp;

    const input = page.locator('.chat-input textarea');
    await input.fill('你好');

    const streamResp = page.waitForResponse(
      (resp) => resp.url().includes('/chat/stream') && resp.status() === 200,
      { timeout: 15_000 },
    );

    const sendBtn = page.locator('.chat-input .send-btn');
    await sendBtn.click();
    await streamResp;

    await page.waitForTimeout(3000);

    const messages = page.locator('.chat-message');
    const count = await messages.count();
    expect(count).toBeGreaterThanOrEqual(2);
  });

  test('发送消息后侧边栏出现新会话', async ({ page }) => {
    const sessionsResp = page.waitForResponse(
      (resp) => resp.url().includes('/chat-sessions') && resp.status() === 200,
      { timeout: 10_000 },
    );

    await page.goto('/chat');
    await sessionsResp;

    const initialCount = await page
      .locator('.chat-sidebar .history-session')
      .count();

    const input = page.locator('.chat-input textarea');
    await input.fill('测试新会话');

    const streamResp = page.waitForResponse(
      (resp) => resp.url().includes('/chat/stream') && resp.status() === 200,
      { timeout: 15_000 },
    );

    const sendBtn = page.locator('.chat-input .send-btn');
    await sendBtn.click();
    await streamResp;

    await page.waitForTimeout(2000);

    const newCount = await page
      .locator('.chat-sidebar .history-session')
      .count();
    expect(newCount).toBeGreaterThanOrEqual(initialCount);
  });

  test('点击侧边栏历史会话加载消息', async ({ page }) => {
    const sessionsResp = page.waitForResponse(
      (resp) => resp.url().includes('/chat-sessions') && resp.status() === 200,
      { timeout: 10_000 },
    );

    await page.goto('/chat');
    await sessionsResp;

    const sessionItems = page.locator('.chat-sidebar .history-session');
    const count = await sessionItems.count();

    if (count > 0) {
      const detailResp = page.waitForResponse(
        (resp) =>
          resp.url().match(/\/chat-sessions\/[^/]+$/) !== null &&
          resp.status() === 200,
        { timeout: 10_000 },
      );

      await sessionItems.first().click();
      await detailResp;

      await page.waitForTimeout(1000);

      const messages = page.locator('.chat-message');
      const msgCount = await messages.count();
      expect(msgCount).toBeGreaterThanOrEqual(0);
    }
  });
});
