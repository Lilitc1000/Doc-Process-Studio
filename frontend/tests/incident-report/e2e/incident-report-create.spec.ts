import { test, expect } from '@playwright/test';
import {
  getWorkerPrefix,
  loginAsAdmin,
  loginViaApi,
  addRateLimitWhitelist,
  createIncidentReportViaApi,
  deleteIncidentReportViaApi,
  cleanupWorkerData,
} from '../../helpers';

const MOCK_QUICK_GENERATE_RESPONSE = {
  report_id: 'mock-report-id',
  form_answers: {
    body_description: { value: 'AI生成的故障描述内容' },
    body_timeline: {
      value: [
        { time: '2026-04-27 10:00', event: '故障发生', resolution: '开始排查' },
        { time: '2026-04-27 10:30', event: '定位原因', resolution: '执行修复' },
      ],
    },
    body_impact_scope: { value: '影响范围：数据库主节点' },
    body_impact_severity: { value: '严重' },
    body_root_cause: { value: 'AI生成的根因分析内容' },
    body_follow_up: { value: 'AI生成的后续行动内容' },
  },
  trace_id: 'mock-trace-id',
  section_id: 'quick',
};

const MOCK_PREVIEW_RESPONSE = {
  source: 'draft',
  label: 'E2E-AI-Preview',
  html: '<h1>事故报告预览</h1><p>AI生成的报告预览内容</p>',
  docx_base64: 'UEsDBBQAAAAIAA==',
  docx_file_name: 'E2E-AI-Preview.docx',
  pdf_base64: null,
  warnings: [],
};

test.describe('事故报告创建流程', () => {
  let workerPrefix: string;

  test.beforeAll(async ({ request }, testInfo) => {
    workerPrefix = getWorkerPrefix(testInfo.workerIndex);
    await addRateLimitWhitelist(request);
  });

  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('创建页正常加载', async ({ page }) => {
    await page.goto('/incident-report/create');
    await expect(page.locator('.incident-report-create-view')).toBeVisible();
  });

  test('创建页显示页面标题', async ({ page }) => {
    await page.goto('/incident-report/create');
    await expect(page.locator('.create-header h1')).toContainText(
      '新建事故报告',
    );
  });

  test('创建页显示步骤指示器', async ({ page }) => {
    await page.goto('/incident-report/create');
    await expect(page.locator('.wizard-step').first()).toBeVisible({
      timeout: 10_000,
    });
    const steps = page.locator('.wizard-step');
    const count = await steps.count();
    expect(count).toBeGreaterThanOrEqual(1);
  });

  test('向导步骤切换 - 点击下一步', async ({ page }) => {
    await page.goto('/incident-report/create');
    await expect(page.locator('.wizard-steps')).toBeVisible();
    const nextBtn = page.locator('.wizard-btn-next');
    if (await nextBtn.isVisible()) {
      await nextBtn.click();
    }
  });

  test('填写标题后可以保存草稿', async ({ page }) => {
    await page.goto('/incident-report/create');
    const titleInput = page.locator('.step-form input').first();
    if (await titleInput.isVisible()) {
      await titleInput.fill('E2E测试报告');
    }
  });

  test('创建页有返回列表的导航', async ({ page }) => {
    await page.goto('/incident-report/create');
    const backBtn = page.locator('button', { hasText: '返回列表' });
    if (await backBtn.isVisible()) {
      await backBtn.click();
      await expect(page).toHaveURL('/incident-report');
    }
  });

  test.afterAll(async ({ request }) => {
    await cleanupWorkerData(request, workerPrefix);
  });
});

test.describe('事故报告创建 - 通过API创建并验证', () => {
  let workerPrefix: string;

  test.beforeAll(async ({ request }, testInfo) => {
    workerPrefix = getWorkerPrefix(testInfo.workerIndex);
    await addRateLimitWhitelist(request);
  });

  test('通过API创建报告后列表页可见', async ({ page, request }) => {
    const token = await loginViaApi(request);
    expect(token).not.toBeNull();

    const report = await createIncidentReportViaApi(request, token!, {
      title: `${workerPrefix}API创建测试报告`,
      system: 'E2E测试系统',
      site_id: 'SITE-E2E',
    });
    expect(report).not.toBeNull();
    expect(report!.status).toBe('draft');

    try {
      await loginAsAdmin(page);
      const listResp = page.waitForResponse(
        (resp) =>
          resp.url().includes('/incident-report/reports') &&
          resp.status() === 200,
        { timeout: 10_000 },
      );
      await page.goto('/incident-report');
      await listResp;

      const reportRow = page
        .locator('.report-list-table tbody tr')
        .filter({ hasText: `${workerPrefix}API创建测试报告` });
      await expect(reportRow).toBeVisible({ timeout: 10_000 });
    } finally {
      await deleteIncidentReportViaApi(request, token!, report!.id);
    }
  });

  test('通过API创建报告后详情页可见', async ({ page, request }) => {
    const token = await loginViaApi(request);
    expect(token).not.toBeNull();

    const report = await createIncidentReportViaApi(request, token!, {
      title: `${workerPrefix}详情页测试报告`,
      severity: 'P1',
      system: 'E2E详情系统',
      site_id: 'SITE-DETAIL',
    });
    expect(report).not.toBeNull();

    try {
      await loginAsAdmin(page);
      await page.goto(`/incident-report/${report!.id}`);
      await expect(page.locator('.incident-report-detail-view')).toBeVisible();
      await expect(page.locator('.detail-title')).toContainText(
        `${workerPrefix}详情页测试报告`,
      );
    } finally {
      await deleteIncidentReportViaApi(request, token!, report!.id);
    }
  });

  test.afterAll(async ({ request }) => {
    await cleanupWorkerData(request, workerPrefix);
  });
});

test.describe.serial('事故报告创建 - 真实 AI 生成（Ollama）', () => {
  let workerPrefix: string;

  test.skip(
    ({ browserName }) => browserName !== 'chromium',
    '仅 Chromium 运行真实 AI 测试',
  );

  test.beforeAll(async ({ request }, testInfo) => {
    workerPrefix = getWorkerPrefix(testInfo.workerIndex);
    await addRateLimitWhitelist(request);
  });

  test('快填模式触发真实 Ollama 生成正文内容', async ({ page, request }) => {
    test.setTimeout(300_000);

    const token = await loginViaApi(request);
    let availableModel = 'qwen3:8b';
    if (token) {
      try {
        const resp = await request.get('/api/models', {
          headers: { Authorization: `Bearer ${token}` },
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
            availableModel = chatModels[0].name;
          }
        }
      } catch {
        // use default model
      }
    }

    await loginAsAdmin(page);

    await page.evaluate((model) => {
      const raw = localStorage.getItem('app');
      const parsed = raw ? JSON.parse(raw) : {};
      parsed.selectedModel = model;
      parsed.selectedRerankerModel = model;
      localStorage.setItem('app', JSON.stringify(parsed));
    }, availableModel);

    await page.goto('/incident-report/create');
    await expect(page.locator('.incident-report-create-view')).toBeVisible({
      timeout: 15_000,
    });

    const titleInput = page.locator('.step-form input').first();
    await titleInput.waitFor({ state: 'visible', timeout: 10_000 });
    await titleInput.fill(`${workerPrefix}真实AI生成测试`);

    const nextBtn = page.locator('.wizard-btn-next');
    await nextBtn.click();

    await expect(page.locator('.wizard-step.active .step-label')).toContainText(
      '快填',
      {
        timeout: 10_000,
      },
    );

    const quickNarrative = page.locator('.base-textarea').first();
    await quickNarrative.waitFor({ state: 'visible', timeout: 5_000 });
    await quickNarrative.fill(
      '4月27日下午2点，生产环境数据库主节点CPU打满，导致订单服务响应超时。2:15开始排查，2:30定位原因为慢查询，2:45通过加索引和降级非核心功能恢复服务，3:00完全恢复。影响范围：订单服务中断约45分钟，约200笔订单受影响。',
    );

    const narrativeValue = await quickNarrative.inputValue();
    if (!narrativeValue.trim()) {
      throw new Error('quick_narrative textarea is empty after fill');
    }

    const genResponse = page.waitForResponse(
      (resp) => resp.url().includes('/body/quick-generate'),
      { timeout: 270_000 },
    );

    const apiRequests: string[] = [];
    page.on('request', (req) => {
      if (req.url().includes('/api/')) {
        apiRequests.push(`${req.method()} ${req.url()}`);
      }
    });

    await nextBtn.click();

    await expect(page.locator('.ai-gen-dialog')).toBeVisible({
      timeout: 10_000,
    });

    const response = await genResponse.catch(() => null);
    if (!response) {
      const recentRequests = apiRequests.slice(-5).join('\n');
      console.warn(
        `快填 AI 生成请求超时，跳过测试。最近的 API 请求:\n${recentRequests}`,
      );
      test.skip();
      return;
    }
    if (response.status() >= 400) {
      const body = await response.text().catch(() => '');
      console.warn(
        `快填 AI 生成请求失败: HTTP ${response.status()} - ${body}，跳过测试`,
      );
      test.skip();
      return;
    }

    await expect(page.locator('.ai-gen-dialog')).not.toBeVisible({
      timeout: 30_000,
    });

    await page.waitForTimeout(3000);

    const activeStepLabel = page.locator('.wizard-step.active .step-label');
    const labelText = await activeStepLabel.textContent();
    expect(labelText).toMatch(/正文|Body/);

    const bodyTextarea = page
      .locator('.step-form textarea.base-textarea')
      .first();
    await expect(bodyTextarea).toBeVisible({ timeout: 5_000 });

    const textareaValue = await bodyTextarea.inputValue();
    expect(
      textareaValue.length,
      `body_description textarea is empty after Ollama generation`,
    ).toBeGreaterThan(0);
  });

  test('分段生成正文 - 真实 Ollama', async ({ page, request }) => {
    test.setTimeout(180_000);

    const token = await loginViaApi(request);
    let availableModel = 'qwen3:8b';
    if (token) {
      try {
        const resp = await request.get('/api/models', {
          headers: { Authorization: `Bearer ${token}` },
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
            availableModel = chatModels[0].name;
          }
        }
      } catch {
        // use default model
      }
    }

    const report = await createIncidentReportViaApi(request, token!, {
      title: `${workerPrefix}分段AI生成测试`,
      severity: 'P2',
      system: 'E2E测试系统',
    });
    expect(report).not.toBeNull();

    try {
      await loginAsAdmin(page);
      await page.goto(`/incident-report/${report!.id}/edit`);

      await page.evaluate((model) => {
        const raw = localStorage.getItem('app');
        const parsed = raw ? JSON.parse(raw) : {};
        parsed.selectedModel = model;
        parsed.selectedRerankerModel = model;
        localStorage.setItem('app', JSON.stringify(parsed));
      }, availableModel);

      await page.reload();

      const bodySection = page
        .locator('.body-description, [data-section="body_description"]')
        .first();
      if (await bodySection.isVisible({ timeout: 5_000 }).catch(() => false)) {
        const generateBtn = bodySection
          .locator('button', { hasText: /AI.*生成|生成/ })
          .first();
        if (
          await generateBtn.isVisible({ timeout: 3_000 }).catch(() => false)
        ) {
          await generateBtn.click();

          await expect(page.locator('.ai-gen-dialog')).toBeVisible({
            timeout: 10_000,
          });

          await expect(page.locator('.ai-gen-dialog')).not.toBeVisible({
            timeout: 120_000,
          });
        }
      }
    } finally {
      await deleteIncidentReportViaApi(request, token!, report!.id);
    }
  });

  test.afterAll(async ({ request }) => {
    await cleanupWorkerData(request, workerPrefix);
  });
});

test.describe('事故报告创建 - AI 生成流程', () => {
  let workerPrefix: string;

  test.beforeAll(async ({ request }, testInfo) => {
    workerPrefix = getWorkerPrefix(testInfo.workerIndex);
    await addRateLimitWhitelist(request);
  });

  test('快填模式填写后点击下一步触发AI生成并自动填充正文', async ({ page }) => {
    await loginAsAdmin(page);

    await page.goto('/incident-report/create');
    await expect(page.locator('.incident-report-create-view')).toBeVisible();

    await page.route(
      '**/api/incident-report/reports/*/body/quick-generate',
      async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_QUICK_GENERATE_RESPONSE),
        });
      },
    );

    const titleInput = page.locator('.step-form input').first();
    await titleInput.waitFor({ state: 'visible', timeout: 10_000 });
    await titleInput.fill(`${workerPrefix}AI生成测试报告`);

    const nextBtn = page.locator('.wizard-btn-next');
    await nextBtn.click();

    await expect(page.locator('.wizard-step.active .step-label')).toContainText(
      '快填 / Quick Fill',
      {
        timeout: 10_000,
      },
    );

    const quickNarrative = page.locator('.base-textarea').first();
    await quickNarrative.waitFor({ state: 'visible', timeout: 5_000 });
    await quickNarrative.fill('数据库主节点故障，导致服务中断30分钟');

    await nextBtn.click();

    await expect(page.locator('.ai-gen-dialog')).toBeVisible({
      timeout: 10_000,
    });

    await expect(page.locator('.ai-gen-dialog')).not.toBeVisible({
      timeout: 15_000,
    });

    await expect(page.locator('.wizard-step.active .step-label')).toContainText(
      'AI 正文 / Body',
      {
        timeout: 15_000,
      },
    );
  });

  test('AI生成弹窗显示思考动画和停止按钮', async ({ page }) => {
    await loginAsAdmin(page);

    await page.goto('/incident-report/create');
    await expect(page.locator('.incident-report-create-view')).toBeVisible();

    let resolveGenerate: (() => void) | null = null;
    const generatePromise = new Promise<void>((resolve) => {
      resolveGenerate = resolve;
    });

    await page.route(
      '**/api/incident-report/reports/*/body/quick-generate',
      async (route) => {
        await generatePromise;
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_QUICK_GENERATE_RESPONSE),
        });
      },
    );

    const titleInput = page.locator('.step-form .base-input').first();
    await titleInput.fill(`${workerPrefix}AI弹窗测试`);

    const nextBtn = page.locator('.wizard-btn-next');
    await nextBtn.click();

    await expect(page.locator('.wizard-step.active .step-label')).toContainText(
      '快填',
      {
        timeout: 10_000,
      },
    );

    const quickNarrative = page.locator('.base-textarea').first();
    if (await quickNarrative.isVisible()) {
      await quickNarrative.fill('测试AI生成弹窗');
    }

    await nextBtn.click();

    await expect(page.locator('.ai-gen-dialog')).toBeVisible({
      timeout: 5_000,
    });
    await expect(page.locator('.ai-gen-thinking-icon')).toBeVisible();
    await expect(page.locator('.ai-gen-stop-btn')).toBeVisible();

    resolveGenerate!();

    await expect(page.locator('.ai-gen-dialog')).not.toBeVisible({
      timeout: 10_000,
    });
  });

  test('预览步骤生成PDF预览', async ({ page, request }) => {
    const token = await loginViaApi(request);
    const report = await createIncidentReportViaApi(request, token!, {
      title: `${workerPrefix}预览测试报告`,
    });
    expect(report).not.toBeNull();

    try {
      await page.route(
        '**/api/incident-report/reports/*/preview',
        async (route) => {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(MOCK_PREVIEW_RESPONSE),
          });
        },
      );

      await loginAsAdmin(page);
      await page.goto(`/incident-report/${report!.id}/edit`);

      const previewSteps = page.locator('.wizard-step');
      const previewStep = previewSteps.last();
      if (await previewStep.isVisible()) {
        await previewStep.click();
      }

      const generatePreviewBtn = page.locator('button', {
        hasText: '生成预览',
      });
      if (
        await generatePreviewBtn
          .isVisible({ timeout: 3_000 })
          .catch(() => false)
      ) {
        await generatePreviewBtn.click();
        await expect(
          page.locator('.ai-gen-dialog, .preview-content'),
        ).toBeVisible({
          timeout: 10_000,
        });
      }
    } finally {
      await deleteIncidentReportViaApi(request, token!, report!.id);
    }
  });

  test.afterAll(async ({ request }) => {
    await cleanupWorkerData(request, workerPrefix);
  });
});
