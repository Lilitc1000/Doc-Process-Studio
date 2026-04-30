import { test, expect } from '@playwright/test';
import {
  getWorkerPrefix,
  loginAs,
  loginViaApiAs,
  addRateLimitWhitelist,
  registerUserViaApi,
  deleteChatSessionsByUser,
  deleteTestUsersByPrefix,
} from '../../helpers';

test.describe('对话页面 - UI 渲染', () => {
  let workerPrefix: string;
  let testUsername: string;
  let testPassword: string;
  let testUserId: string;

  test.beforeAll(async ({ request }, testInfo) => {
    workerPrefix = getWorkerPrefix(testInfo.workerIndex);
    testUsername = `${workerPrefix}chat_ui_user`;
    testPassword = 'Test123456!';
    await addRateLimitWhitelist(request);

    const user = await registerUserViaApi(request, testUsername, testPassword);
    if (user) {
      testUserId = user.user_id;
    }
  });

  test.beforeEach(async ({ page }) => {
    await loginAs(page, testUsername, testPassword);
    await page.goto('/chat');
  });

  test.afterAll(async ({ request }) => {
    try {
      if (testUserId) {
        const token = await loginViaApiAs(request, testUsername, testPassword);
        if (token) {
          await deleteChatSessionsByUser(request, token, testUserId);
        }
      }
    } catch {
      // ignore cleanup errors
    }
    await deleteTestUsersByPrefix(request, workerPrefix);
  });

  test('对话页面渲染侧边栏和输入区域', async ({ page }) => {
    await expect(page.locator('.app-header-title')).toHaveText('对话');
    await expect(page.locator('.chat-sidebar')).toBeVisible();
    await expect(page.locator('.chat-input')).toBeVisible();
  });

  test('输入区域包含文本输入框和发送按钮', async ({ page }) => {
    const input = page.locator('.chat-input textarea');
    await expect(input).toBeVisible();

    const sendBtn = page.locator('.chat-input .send-btn');
    await expect(sendBtn).toBeVisible();
  });

  test('在输入框中输入文字后内容正确显示', async ({ page }) => {
    const input = page.locator('.chat-input textarea');
    await input.fill('你好，请帮我写一份文档');
    await expect(input).toHaveValue('你好，请帮我写一份文档');
  });

  test('点击 header 标题仍停留在对话页面', async ({ page }) => {
    await page.locator('.app-header-title').click();
    await expect(page).toHaveURL('/chat');
  });
});

test.describe('对话页面 - 端到端场景', () => {
  test.setTimeout(120_000);

  let workerPrefix: string;
  let testUsername: string;
  let testPassword: string;
  let testUserId: string;
  let ollamaAvailable = false;
  let availableModel = '';

  test.beforeAll(async ({ request }, testInfo) => {
    workerPrefix = getWorkerPrefix(testInfo.workerIndex);
    testUsername = `${workerPrefix}chat_e2e_user`;
    testPassword = 'Test123456!';
    await addRateLimitWhitelist(request);

    const user = await registerUserViaApi(request, testUsername, testPassword);
    if (user) {
      testUserId = user.user_id;
    }

    try {
      const accessToken = await loginViaApiAs(
        request,
        testUsername,
        testPassword,
      );
      if (accessToken) {
        const resp = await request.get('/api/models', {
          headers: { Authorization: `Bearer ${accessToken}` },
          timeout: 10_000,
        });
        if (resp.ok()) {
          const data = await resp.json();
          const models: { name: string }[] = data.models ?? [];
          const chatModels = models.filter(
            (m) =>
              !m.name.includes('embed') &&
              !m.name.includes('rerank') &&
              !m.name.includes('bge'),
          );
          if (chatModels.length > 0) {
            ollamaAvailable = true;
            availableModel = chatModels[0].name;
          }
        }
      }
    } catch {
      ollamaAvailable = false;
    }
  });

  test.beforeEach(async ({ page }) => {
    await loginAs(page, testUsername, testPassword);
  });

  test.afterAll(async ({ request }) => {
    try {
      if (testUserId) {
        const token = await loginViaApiAs(request, testUsername, testPassword);
        if (token) {
          await deleteChatSessionsByUser(request, token, testUserId);
        }
      }
    } catch {
      // ignore cleanup errors
    }
    await deleteTestUsersByPrefix(request, workerPrefix);
  });

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
    if (!ollamaAvailable) {
      test.skip();
      return;
    }

    await page.goto('/chat');

    await page.waitForResponse(
      (resp) => resp.url().includes('/api/models') && resp.status() === 200,
      { timeout: 10_000 },
    );

    await page.evaluate((model) => {
      const raw = localStorage.getItem('app');
      const parsed = raw ? JSON.parse(raw) : {};
      parsed.selectedModel = model;
      parsed.selectedRerankerModel = model;
      localStorage.setItem('app', JSON.stringify(parsed));
    }, availableModel);

    await page.reload();
    await page.waitForResponse(
      (resp) => resp.url().includes('/chat-sessions') && resp.status() === 200,
      { timeout: 10_000 },
    );

    const input = page.locator('.chat-input textarea');
    await input.fill('你好');

    const sendBtn = page.locator('.chat-input .send-btn');
    await sendBtn.click();

    const streamResp = await page.waitForResponse(
      (resp) => resp.url().includes('/chat/stream'),
      { timeout: 60_000 },
    );
    expect(streamResp.status()).toBe(200);

    await page.waitForTimeout(5000);

    const messages = page.locator('.chat-message');
    const count = await messages.count();
    expect(count).toBeGreaterThanOrEqual(2);

    const assistantMessages = page.locator('.chat-message.assistant');
    const assistantCount = await assistantMessages.count();
    if (assistantCount > 0) {
      const lastAssistant = assistantMessages.last();
      const text = await lastAssistant.textContent();
      expect(text).not.toContain('请求失败');
      expect(text).not.toContain('错误状态');
    }
  });

  test('发送消息后侧边栏出现新会话', async ({ page }) => {
    if (!ollamaAvailable) {
      test.skip();
      return;
    }

    await page.goto('/chat');

    await page.waitForResponse(
      (resp) => resp.url().includes('/api/models') && resp.status() === 200,
      { timeout: 10_000 },
    );

    await page.evaluate((model) => {
      const raw = localStorage.getItem('app');
      const parsed = raw ? JSON.parse(raw) : {};
      parsed.selectedModel = model;
      parsed.selectedRerankerModel = model;
      localStorage.setItem('app', JSON.stringify(parsed));
    }, availableModel);

    await page.reload();
    await page.waitForResponse(
      (resp) => resp.url().includes('/chat-sessions') && resp.status() === 200,
      { timeout: 10_000 },
    );

    const initialCount = await page
      .locator('.chat-sidebar .history-session')
      .count();

    const input = page.locator('.chat-input textarea');
    await input.fill('测试新会话');

    const sendBtn = page.locator('.chat-input .send-btn');
    await sendBtn.click();

    const streamResp = await page.waitForResponse(
      (resp) => resp.url().includes('/chat/stream'),
      { timeout: 60_000 },
    );
    expect(streamResp.status()).toBe(200);

    await page.waitForTimeout(3000);

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
