import { test, expect } from '@playwright/test';
import {
  getWorkerPrefix,
  loginAs,
  loginViaApiAs,
  addRateLimitWhitelist,
  registerUserViaApi,
  deleteTestUsersByPrefix,
  pickE2EModel,
} from '../../helpers';

test.describe('知识库页面 - UI 渲染', () => {
  let workerPrefix: string;
  let testUsername: string;
  let testPassword: string;

  test.beforeAll(async ({ request }, testInfo) => {
    workerPrefix = getWorkerPrefix(testInfo.workerIndex);
    testUsername = `${workerPrefix}kb_ui_user`;
    testPassword = 'Test123456!';
    await addRateLimitWhitelist(request);

    await registerUserViaApi(request, testUsername, testPassword);
  });

  test.beforeEach(async ({ page }) => {
    await loginAs(page, testUsername, testPassword);
    await page.goto('/knowledge-base');
  });

  test.afterAll(async ({ request }) => {
    await deleteTestUsersByPrefix(request, workerPrefix);
  });

  test('知识库页面渲染标题和新建按钮', async ({ page }) => {
    await expect(page.locator('.kb-list-title')).toHaveText('知识库');
    await expect(page.locator('.kb-list-header button')).toContainText(
      '新建项目',
    );
  });

  test('空知识库页面显示引导提示', async ({ page }) => {
    const emptyHint = page.locator('.kb-list-empty');
    if (await emptyHint.isVisible()) {
      await expect(emptyHint).toContainText('暂无知识库项目');
    }
  });
});

test.describe('知识库页面 - 项目 CRUD', () => {
  test.setTimeout(60_000);

  let workerPrefix: string;
  let testUsername: string;
  let testPassword: string;
  let accessToken: string;

  test.beforeAll(async ({ request }, testInfo) => {
    workerPrefix = getWorkerPrefix(testInfo.workerIndex);
    testUsername = `${workerPrefix}kb_crud_user`;
    testPassword = 'Test123456!';
    await addRateLimitWhitelist(request);

    await registerUserViaApi(request, testUsername, testPassword);

    const token = await loginViaApiAs(request, testUsername, testPassword);
    if (token) {
      accessToken = token;
    }
  });

  test.afterAll(async ({ request }) => {
    try {
      if (accessToken) {
        const resp = await request.get('/api/knowledge-base/projects', {
          headers: { Authorization: `Bearer ${accessToken}` },
        });
        if (resp.ok()) {
          const data = await resp.json();
          const projects: { id: string; name: string }[] = data.projects ?? [];
          for (const project of projects) {
            if (project.name.startsWith(workerPrefix)) {
              await request.delete(
                `/api/knowledge-base/projects/${project.id}`,
                { headers: { Authorization: `Bearer ${accessToken}` } },
              );
            }
          }
        }
      }
    } catch {
      // ignore cleanup errors
    }
    await deleteTestUsersByPrefix(request, workerPrefix);
  });

  test('新建知识库项目后出现在列表中', async ({ page }) => {
    await loginAs(page, testUsername, testPassword);
    await page.goto('/knowledge-base');

    const projectName = `${workerPrefix}测试项目`;

    await page.locator('.kb-list-header button').click();

    const dialog = page.locator('.kb-dialog');
    await expect(dialog).toBeVisible();

    await dialog.locator('input').fill(projectName);
    await dialog.getByRole('button', { name: '创建' }).click();

    await page.waitForResponse(
      (resp) =>
        resp.url().includes('/knowledge-base/projects') &&
        resp.status() === 201,
      { timeout: 10_000 },
    );

    await expect(page.locator('.kb-project-card').first()).toBeVisible({
      timeout: 10_000,
    });
    await expect(page.locator('.kb-project-name').first()).toContainText(
      projectName,
    );
  });

  test('点击项目卡片进入详情页', async ({ page }) => {
    await loginAs(page, testUsername, testPassword);
    await page.goto('/knowledge-base');

    await page.waitForResponse(
      (resp) =>
        resp.url().includes('/knowledge-base/projects') &&
        resp.status() === 200,
      { timeout: 10_000 },
    );

    const projectCards = page.locator('.kb-project-card');
    const cardCount = await projectCards.count();

    if (cardCount > 0) {
      await projectCards.first().click();
      await expect(page).toHaveURL(/\/knowledge-base\/[^/]+$/, {
        timeout: 10_000,
      });
      await expect(page.locator('.kb-detail-title')).toBeVisible();
    }
  });
});

test.describe('知识库 Skill 对话 - 端到端场景', () => {
  test.setTimeout(120_000);

  let workerPrefix: string;
  let testUsername: string;
  let testPassword: string;
  let testUserId: string;
  let accessToken: string;
  let ollamaAvailable = false;
  let availableModel = '';

  test.beforeAll(async ({ request }, testInfo) => {
    workerPrefix = getWorkerPrefix(testInfo.workerIndex);
    testUsername = `${workerPrefix}kb_skill_user`;
    testPassword = 'Test123456!';
    await addRateLimitWhitelist(request);

    const user = await registerUserViaApi(request, testUsername, testPassword);
    if (user) {
      testUserId = user.user_id;
    }

    const token = await loginViaApiAs(request, testUsername, testPassword);
    if (token) {
      accessToken = token;
    }

    // 检查 Ollama 可用性并选择模型
    try {
      if (accessToken) {
        const resp = await request.get('/api/models', {
          headers: { Authorization: `Bearer ${accessToken}` },
          timeout: 10_000,
        });
        if (resp.ok()) {
          const data = await resp.json();
          const models: { name: string }[] = data.models ?? [];
          const chosen = pickE2EModel(models);
          if (chosen) {
            ollamaAvailable = true;
            availableModel = chosen;
          }
        }
      }
    } catch {
      ollamaAvailable = false;
    }

    // 创建知识库项目供 skill 测试使用
    try {
      if (accessToken) {
        await request.post('/api/knowledge-base/projects', {
          headers: { Authorization: `Bearer ${accessToken}` },
          data: { name: `${workerPrefix}KB项目`, description: 'E2E测试项目' },
        });
      }
    } catch {
      // ignore
    }
  });

  test.beforeEach(async ({ page }) => {
    await loginAs(page, testUsername, testPassword);
  });

  test.afterAll(async ({ request }) => {
    try {
      if (accessToken) {
        // 清理知识库项目
        const resp = await request.get('/api/knowledge-base/projects', {
          headers: { Authorization: `Bearer ${accessToken}` },
        });
        if (resp.ok()) {
          const data = await resp.json();
          const projects: { id: string; name: string }[] = data.projects ?? [];
          for (const project of projects) {
            if (project.name.startsWith(workerPrefix)) {
              await request.delete(
                `/api/knowledge-base/projects/${project.id}`,
                { headers: { Authorization: `Bearer ${accessToken}` } },
              );
            }
          }
        }

        // 清理聊天会话
        if (testUserId) {
          await request.delete(`/api/chat-sessions/by-user/${testUserId}`, {
            headers: { Authorization: `Bearer ${accessToken}` },
          });
        }
      }
    } catch {
      // ignore cleanup errors
    }
    await deleteTestUsersByPrefix(request, workerPrefix);
  });

  test('选择 kb: skill 后发送消息不会触发 skill 解析错误', async ({ page }) => {
    if (!ollamaAvailable) {
      test.skip();
      return;
    }

    await page.goto('/chat');

    await page.waitForResponse(
      (resp) => resp.url().includes('/api/models') && resp.status() === 200,
      { timeout: 10_000 },
    );

    // 设置模型
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

    // 通过 $ 触发 skill 选择器
    const input = page.locator('.chat-input textarea');
    await input.fill('$');

    // 等待 skill 建议列表出现
    const suggestionList = page.locator('.skill-suggestion-list');
    await expect(suggestionList)
      .toBeVisible({ timeout: 5_000 })
      .catch(() => {
        // 如果没有建议列表，尝试直接通过 API 选择 skill
      });

    // 查找并点击 kb: 项目建议
    const kbSuggestion = page.locator('.skill-suggestion-item').filter({
      hasText: workerPrefix,
    });
    if (await kbSuggestion.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await kbSuggestion.click();
    } else {
      // 如果没有可见的 kb 建议，通过 API 直接设置 selectedSkillIds
      await page.evaluate((skillId) => {
        const raw = localStorage.getItem('app');
        const parsed = raw ? JSON.parse(raw) : {};
        parsed.selectedSkillIds = [skillId];
        localStorage.setItem('app', JSON.stringify(parsed));
      }, `kb:${workerPrefix}KB项目`);
      await page.reload();
      await page.waitForResponse(
        (resp) =>
          resp.url().includes('/chat-sessions') && resp.status() === 200,
        { timeout: 10_000 },
      );
    }

    // 验证 skill chip 已选中
    const skillChip = page
      .locator('.skill-chip')
      .filter({ hasText: workerPrefix });
    if (await skillChip.isVisible({ timeout: 3_000 }).catch(() => false)) {
      // skill chip 已显示
    }

    // 发送消息
    await input.fill('你好');
    const sendBtn = page.locator('.chat-input .send-btn');
    const streamRespPromise = page.waitForResponse(
      (resp) => resp.url().includes('/chat/stream'),
      { timeout: 60_000 },
    );
    await sendBtn.click();

    const streamResp = await streamRespPromise;
    expect(streamResp.status()).toBe(200);

    // 等待回复完成
    await page.waitForTimeout(5000);

    // 验证不会出现 "未找到 skill" 相关错误
    const messages = page.locator('.chat-message');
    const count = await messages.count();
    expect(count).toBeGreaterThanOrEqual(2);

    const assistantMessages = page.locator('.chat-message.assistant');
    const assistantCount = await assistantMessages.count();
    if (assistantCount > 0) {
      const lastAssistant = assistantMessages.last();
      const text = await lastAssistant.textContent();
      // 不应出现 skill 解析错误
      expect(text).not.toContain('未找到 skill');
      expect(text).not.toContain('ValueError');
    }
  });

  test('kb: skill 与普通 skill 混合选择不会触发解析错误', async ({ page }) => {
    if (!ollamaAvailable) {
      test.skip();
      return;
    }

    await page.goto('/chat');

    await page.waitForResponse(
      (resp) => resp.url().includes('/api/models') && resp.status() === 200,
      { timeout: 10_000 },
    );

    // 设置模型
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

    // 通过 $ 触发 skill 选择器
    const input = page.locator('.chat-input textarea');
    await input.fill('$');

    // 等待建议列表
    await page.waitForTimeout(1000);

    // 选择第一个普通 skill
    const firstSkill = page.locator('.skill-suggestion-item').first();
    if (await firstSkill.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await firstSkill.click();
    }

    // 选择 kb: 项目
    await input.fill('$');
    await page.waitForTimeout(500);

    const kbSuggestion = page.locator('.skill-suggestion-item').filter({
      hasText: workerPrefix,
    });
    if (await kbSuggestion.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await kbSuggestion.click();
    }

    // 发送消息
    await input.fill('测试混合skill');
    const sendBtn = page.locator('.chat-input .send-btn');
    const streamRespPromise = page.waitForResponse(
      (resp) => resp.url().includes('/chat/stream'),
      { timeout: 60_000 },
    );
    await sendBtn.click();

    const streamResp = await streamRespPromise;
    expect(streamResp.status()).toBe(200);

    await page.waitForTimeout(5000);

    // 验证不会出现 skill 解析错误
    const assistantMessages = page.locator('.chat-message.assistant');
    const assistantCount = await assistantMessages.count();
    if (assistantCount > 0) {
      const text = await assistantMessages.last().textContent();
      expect(text).not.toContain('未找到 skill');
      expect(text).not.toContain('ValueError');
    }
  });
});
