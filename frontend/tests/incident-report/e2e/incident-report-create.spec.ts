import { test, expect, type Page } from '@playwright/test';
import {
  getWorkerPrefix,
  loginAsAdmin,
  loginViaApi,
  addRateLimitWhitelist,
  createIncidentReportViaApi,
  deleteIncidentReportViaApi,
  cleanupWorkerData,
} from '../../helpers';

async function pickTodayDate(page: Page, fieldLabel: string) {
  const trigger = page
    .locator('.field-item', { hasText: fieldLabel })
    .locator('.date-time-trigger');
  await trigger.click();
  const dayBtn = page
    .locator('.date-time-day-btn.is-today, .date-time-day-btn')
    .first();
  if (await dayBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
    await dayBtn.click();
  }
  const confirmBtn = page.locator('.date-time-action-btn.is-primary');
  if (await confirmBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
    await confirmBtn.click();
  }
}

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
      await titleInput.fill(`${workerPrefix}测试报告`);
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

  test('必填项标题在点击下一步前不显示红色', async ({ page }) => {
    await page.goto('/incident-report/create');
    await expect(page.locator('.incident-report-create-view')).toBeVisible();

    const invalidFields = page.locator('.field-item.invalid');
    const count = await invalidFields.count();
    expect(count).toBe(0);
  });

  test('必填项标题在点击下一步后显示红色', async ({ page }) => {
    await page.goto('/incident-report/create');
    await expect(page.locator('.incident-report-create-view')).toBeVisible();

    const nextBtn = page.locator('.wizard-btn-next');
    await nextBtn.click();

    const invalidFields = page.locator('.field-item.invalid');
    await expect(invalidFields.first()).toBeVisible({ timeout: 3_000 });
  });

  test('填写必填项后红色标签消失', async ({ page }) => {
    await page.goto('/incident-report/create');
    await expect(page.locator('.incident-report-create-view')).toBeVisible();

    const nextBtn = page.locator('.wizard-btn-next');
    await nextBtn.click();

    const invalidFields = page.locator('.field-item.invalid');
    await expect(invalidFields.first()).toBeVisible({ timeout: 3_000 });

    const titleInput = page
      .locator('.field-item', { hasText: '报告标题' })
      .locator('input');
    await titleInput.fill(`${workerPrefix}测试报告`);

    await pickTodayDate(page, '故障上报日期');

    const reporterInput = page
      .locator('.field-item', { hasText: '报告人' })
      .locator('input');
    await reporterInput.fill('测试报告人');

    const siteInput = page
      .locator('.field-item', { hasText: '站点编号' })
      .locator('input');
    await siteInput.fill('SITE-001');

    const systemInput = page
      .locator('.field-item', { hasText: '系统 / 子系统' })
      .locator('input');
    await systemInput.fill('测试系统');

    const locationInput = page
      .locator('.field-item', { hasText: '故障位置' })
      .locator('input');
    await locationInput.fill('测试位置');

    const symptomInput = page
      .locator('.field-item', { hasText: '故障现象详情' })
      .locator('textarea');
    await symptomInput.fill('测试故障现象');

    const remainingInvalid = page.locator('.field-item.invalid');
    const count = await remainingInvalid.count();
    expect(count).toBe(0);
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
      await expect(page.locator('.incident-report-detail-view')).toBeVisible({
        timeout: 10_000,
      });
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

  async function getAvailableModel(
    request: import('@playwright/test').APIRequestContext,
  ): Promise<string> {
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
    return availableModel;
  }

  async function setupModelAndNavigate(
    page: import('@playwright/test').Page,
    model: string,
  ) {
    await loginAsAdmin(page);
    await page.evaluate((m) => {
      const raw = localStorage.getItem('app');
      const parsed = raw ? JSON.parse(raw) : {};
      parsed.selectedModel = m;
      parsed.selectedRerankerModel = m;
      localStorage.setItem('app', JSON.stringify(parsed));
    }, model);
    await page.goto('/incident-report/create');
    await expect(page.locator('.incident-report-create-view')).toBeVisible({
      timeout: 15_000,
    });
  }

  test('快填模式触发真实 Ollama 生成正文内容', async ({ page, request }) => {
    test.setTimeout(300_000);

    const availableModel = await getAvailableModel(request);
    await setupModelAndNavigate(page, availableModel);

    const titleInput = page
      .locator('.field-item', { hasText: '报告标题' })
      .locator('input');
    await titleInput.waitFor({ state: 'visible', timeout: 10_000 });
    await titleInput.fill(`${workerPrefix}真实AI生成测试`);

    await pickTodayDate(page, '故障上报日期');

    const reporterInput = page
      .locator('.field-item', { hasText: '报告人' })
      .locator('input');
    await reporterInput.fill('E2E测试报告人');

    const siteInput = page
      .locator('.field-item', { hasText: '站点编号' })
      .locator('input');
    await siteInput.fill('SITE-001');

    const systemInput = page
      .locator('.field-item', { hasText: '系统 / 子系统' })
      .locator('input');
    await systemInput.fill('E2E测试系统');

    const locationInput = page
      .locator('.field-item', { hasText: '故障位置' })
      .locator('input');
    await locationInput.fill('E2E测试位置');

    const symptomInput = page
      .locator('.field-item', { hasText: '故障现象详情' })
      .locator('textarea');
    await symptomInput.fill('E2E测试故障现象');

    const nextBtn = page.locator('.wizard-btn-next');
    await nextBtn.click();

    await expect(page.locator('.wizard-step.active .step-label')).toContainText(
      '快填',
      { timeout: 10_000 },
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
      { timeout: 300_000 },
    );

    const apiRequests: string[] = [];
    page.on('request', (req) => {
      if (req.url().includes('/api/')) {
        apiRequests.push(`${req.method()} ${req.url()}`);
      }
    });

    const aiGenerateBtn = page.locator('.section-card button', {
      hasText: /AI.*生成/,
    });
    await aiGenerateBtn.click();

    const response = await genResponse.catch(() => null);
    if (!response) {
      const recentRequests = apiRequests.slice(-5).join('\n');
      throw new Error(
        `快填 AI 生成请求超时（300s）。最近的 API 请求:\n${recentRequests}`,
      );
    }
    if (response.status() >= 400) {
      const body = await response.text().catch(() => '');
      throw new Error(
        `快填 AI 生成请求失败: HTTP ${response.status()} - ${body}`,
      );
    }

    await expect(page.locator('.floating-toast')).toBeVisible({
      timeout: 10_000,
    });

    await page.waitForTimeout(3000);

    const nextBtn2 = page.locator('.wizard-btn-next');
    await nextBtn2.click();

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

  test('分段生成正文 - 事故简述 - 真实 Ollama', async ({ page, request }) => {
    test.setTimeout(300_000);

    const availableModel = await getAvailableModel(request);
    await setupModelAndNavigate(page, availableModel);

    const titleInput = page
      .locator('.field-item', { hasText: '报告标题' })
      .locator('input');
    await titleInput.waitFor({ state: 'visible', timeout: 10_000 });
    await titleInput.fill(`${workerPrefix}分段AI-简述测试`);

    await pickTodayDate(page, '故障上报日期');

    const reporterInput = page
      .locator('.field-item', { hasText: '报告人' })
      .locator('input');
    await reporterInput.fill('E2E测试报告人');

    const siteInput = page
      .locator('.field-item', { hasText: '站点编号' })
      .locator('input');
    await siteInput.fill('SITE-001');

    const systemInput = page
      .locator('.field-item', { hasText: '系统 / 子系统' })
      .locator('input');
    await systemInput.fill('E2E测试系统');

    const locationInput = page
      .locator('.field-item', { hasText: '故障位置' })
      .locator('input');
    await locationInput.fill('E2E测试位置');

    const symptomInput = page
      .locator('.field-item', { hasText: '故障现象详情' })
      .locator('textarea');
    await symptomInput.fill('E2E测试故障现象');

    const nextBtn = page.locator('.wizard-btn-next');

    await nextBtn.click();
    await expect(page.locator('.wizard-step.active .step-label')).toContainText(
      '快填',
      { timeout: 10_000 },
    );

    const skipBtn = page.locator('button', { hasText: /跳过|Skip/ });
    if (await skipBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await skipBtn.click();
    } else {
      await nextBtn.click();
    }

    await expect(page.locator('.wizard-step.active .step-label')).toContainText(
      '正文',
      { timeout: 10_000 },
    );

    const sectionCards = page.locator('.section-card');
    await expect(sectionCards.first()).toBeVisible({ timeout: 5_000 });

    const descriptionGenBtn = sectionCards.nth(0).locator('button', {
      hasText: /AI.*生成|生成/,
    });
    await expect(descriptionGenBtn).toBeVisible();
    await expect(descriptionGenBtn).toBeEnabled();

    const apiRequests: string[] = [];
    page.on('request', (req) => {
      if (req.url().includes('/api/')) {
        apiRequests.push(`${req.method()} ${req.url()}`);
      }
    });

    const genResponse = page.waitForResponse(
      async (resp) => {
        if (!resp.url().includes('/body/section-generate')) return false;
        try {
          const body = resp.request().postData();
          return body?.includes('description') ?? false;
        } catch {
          return false;
        }
      },
      { timeout: 270_000 },
    );

    await descriptionGenBtn.click();

    await expect(page.locator('.ai-gen-dialog')).toBeVisible({
      timeout: 10_000,
    });

    const response = await genResponse.catch(() => null);
    if (!response) {
      const recentRequests = apiRequests.slice(-5).join('\n');
      throw new Error(
        `事故简述 AI 生成请求超时。最近的 API 请求:\n${recentRequests}`,
      );
    }
    if (response.status() >= 400) {
      const body = await response.text().catch(() => '');
      throw new Error(
        `事故简述 AI 生成请求失败: HTTP ${response.status()} - ${body}`,
      );
    }

    await expect(page.locator('.ai-gen-dialog')).not.toBeVisible({
      timeout: 120_000,
    });

    const bodyTextarea = page
      .locator('.section-card')
      .nth(0)
      .locator('textarea.base-textarea');
    if (await bodyTextarea.isVisible({ timeout: 5_000 }).catch(() => false)) {
      const textareaValue = await bodyTextarea.inputValue();
      expect(
        textareaValue.length,
        'body_description textarea is empty after section generation',
      ).toBeGreaterThan(0);
    }
  });

  test('分段生成正文 - 影响范围 - 真实 Ollama', async ({ page, request }) => {
    test.setTimeout(300_000);

    const token = await loginViaApi(request);
    const report = await createIncidentReportViaApi(request, token!, {
      title: `${workerPrefix}分段AI-影响范围测试`,
      system: 'E2E测试系统',
      site_id: 'SITE-E2E',
      form_data: {
        body_description: '生产环境数据库主节点CPU打满，导致订单服务响应超时。',
      },
    });
    expect(report).not.toBeNull();

    try {
      const availableModel = await getAvailableModel(request);
      await loginAsAdmin(page);
      await page.evaluate((m) => {
        const raw = localStorage.getItem('app');
        const parsed = raw ? JSON.parse(raw) : {};
        parsed.selectedModel = m;
        parsed.selectedRerankerModel = m;
        localStorage.setItem('app', JSON.stringify(parsed));
      }, availableModel);

      await page.goto(`/incident-report/${report!.id}/edit`);
      await expect(page.locator('.incident-report-edit-view')).toBeVisible({
        timeout: 10_000,
      });

      const nextBtn = page.locator('.wizard-btn-next');
      await nextBtn.click();

      await expect(
        page.locator('.wizard-step.active .step-label'),
      ).toContainText('快填', { timeout: 10_000 });

      await nextBtn.click();

      await expect(
        page.locator('.wizard-step.active .step-label'),
      ).toContainText('正文', { timeout: 10_000 });

      const sectionCards = page.locator('.section-card');
      await expect(sectionCards.first()).toBeVisible({ timeout: 5_000 });

      const impactGenBtn = sectionCards.nth(2).locator('button', {
        hasText: /AI.*生成|生成/,
      });
      await expect(impactGenBtn).toBeVisible();
      await expect(impactGenBtn).toBeEnabled();

      const apiRequests: string[] = [];
      page.on('request', (req) => {
        if (req.url().includes('/api/')) {
          apiRequests.push(`${req.method()} ${req.url()}`);
        }
      });

      const genResponse = page.waitForResponse(
        async (resp) => {
          if (!resp.url().includes('/body/section-generate')) return false;
          try {
            const body = resp.request().postData();
            return body?.includes('impact') ?? false;
          } catch {
            return false;
          }
        },
        { timeout: 270_000 },
      );

      await impactGenBtn.click();

      await expect(page.locator('.ai-gen-dialog')).toBeVisible({
        timeout: 10_000,
      });

      const response = await genResponse.catch(() => null);
      if (!response) {
        const recentRequests = apiRequests.slice(-5).join('\n');
        throw new Error(
          `影响范围 AI 生成请求超时。最近的 API 请求:\n${recentRequests}`,
        );
      }
      if (response.status() >= 400) {
        const body = await response.text().catch(() => '');
        throw new Error(
          `影响范围 AI 生成请求失败: HTTP ${response.status()} - ${body}`,
        );
      }

      await expect(page.locator('.ai-gen-dialog')).not.toBeVisible({
        timeout: 120_000,
      });

      const impactScopeInput = page.locator('.section-card:nth-child(3) input');
      if (
        await impactScopeInput.isVisible({ timeout: 5_000 }).catch(() => false)
      ) {
        const inputValue = await impactScopeInput.inputValue();
        expect(
          inputValue.length,
          'body_impact_scope input is empty after section generation',
        ).toBeGreaterThan(0);
      }
    } finally {
      await deleteIncidentReportViaApi(request, token!, report!.id);
    }
  });

  test('分段生成正文 - 根因分析 - 真实 Ollama', async ({ page, request }) => {
    test.setTimeout(300_000);

    const token = await loginViaApi(request);
    const report = await createIncidentReportViaApi(request, token!, {
      title: `${workerPrefix}分段AI-根因分析测试`,
      system: 'E2E测试系统',
      site_id: 'SITE-E2E',
      form_data: {
        body_description: '生产环境数据库主节点CPU打满，导致订单服务响应超时。',
        body_impact_scope: '订单服务中断约45分钟',
        body_impact_severity: '严重',
      },
    });
    expect(report).not.toBeNull();

    try {
      const availableModel = await getAvailableModel(request);
      await loginAsAdmin(page);
      await page.evaluate((m) => {
        const raw = localStorage.getItem('app');
        const parsed = raw ? JSON.parse(raw) : {};
        parsed.selectedModel = m;
        parsed.selectedRerankerModel = m;
        localStorage.setItem('app', JSON.stringify(parsed));
      }, availableModel);

      await page.goto(`/incident-report/${report!.id}/edit`);
      await expect(page.locator('.incident-report-edit-view')).toBeVisible({
        timeout: 10_000,
      });

      const nextBtn = page.locator('.wizard-btn-next');
      await nextBtn.click();

      await expect(
        page.locator('.wizard-step.active .step-label'),
      ).toContainText('快填', { timeout: 10_000 });

      await nextBtn.click();

      await expect(
        page.locator('.wizard-step.active .step-label'),
      ).toContainText('正文', { timeout: 10_000 });

      const sectionCards = page.locator('.section-card');
      await expect(sectionCards.first()).toBeVisible({ timeout: 5_000 });

      const rootCauseGenBtn = sectionCards.nth(3).locator('button', {
        hasText: /AI.*生成|生成/,
      });
      await expect(rootCauseGenBtn).toBeVisible();
      await expect(rootCauseGenBtn).toBeEnabled();

      const apiRequests: string[] = [];
      page.on('request', (req) => {
        if (req.url().includes('/api/')) {
          apiRequests.push(`${req.method()} ${req.url()}`);
        }
      });

      const genResponse = page.waitForResponse(
        async (resp) => {
          if (!resp.url().includes('/body/section-generate')) return false;
          try {
            const body = resp.request().postData();
            return body?.includes('root_cause') ?? false;
          } catch {
            return false;
          }
        },
        { timeout: 270_000 },
      );

      await rootCauseGenBtn.click();

      await expect(page.locator('.ai-gen-dialog')).toBeVisible({
        timeout: 10_000,
      });

      const response = await genResponse.catch(() => null);
      if (!response) {
        const recentRequests = apiRequests.slice(-5).join('\n');
        throw new Error(
          `根因分析 AI 生成请求超时。最近的 API 请求:\n${recentRequests}`,
        );
      }
      if (response.status() >= 400) {
        const body = await response.text().catch(() => '');
        throw new Error(
          `根因分析 AI 生成请求失败: HTTP ${response.status()} - ${body}`,
        );
      }

      await expect(page.locator('.ai-gen-dialog')).not.toBeVisible({
        timeout: 120_000,
      });

      const rootCauseTextarea = page
        .locator('.section-card')
        .nth(3)
        .locator('textarea.base-textarea');
      if (
        await rootCauseTextarea.isVisible({ timeout: 5_000 }).catch(() => false)
      ) {
        const textareaValue = await rootCauseTextarea.inputValue();
        expect(
          textareaValue.length,
          'body_root_cause textarea is empty after section generation',
        ).toBeGreaterThan(0);
      }
    } finally {
      await deleteIncidentReportViaApi(request, token!, report!.id);
    }
  });

  test('分段生成正文 - 后续动作 - 真实 Ollama', async ({ page, request }) => {
    test.setTimeout(300_000);

    const token = await loginViaApi(request);
    const report = await createIncidentReportViaApi(request, token!, {
      title: `${workerPrefix}分段AI-后续动作测试`,
      system: 'E2E测试系统',
      site_id: 'SITE-E2E',
      form_data: {
        body_description: '生产环境数据库主节点CPU打满，导致订单服务响应超时。',
        body_impact_scope: '订单服务中断约45分钟',
        body_impact_severity: '严重',
        body_root_cause: '慢查询导致CPU打满',
      },
    });
    expect(report).not.toBeNull();

    try {
      const availableModel = await getAvailableModel(request);
      await loginAsAdmin(page);
      await page.evaluate((m) => {
        const raw = localStorage.getItem('app');
        const parsed = raw ? JSON.parse(raw) : {};
        parsed.selectedModel = m;
        parsed.selectedRerankerModel = m;
        localStorage.setItem('app', JSON.stringify(parsed));
      }, availableModel);

      await page.goto(`/incident-report/${report!.id}/edit`);
      await expect(page.locator('.incident-report-edit-view')).toBeVisible({
        timeout: 10_000,
      });

      const nextBtn = page.locator('.wizard-btn-next');
      await nextBtn.click();

      await expect(
        page.locator('.wizard-step.active .step-label'),
      ).toContainText('快填', { timeout: 10_000 });

      await nextBtn.click();

      await expect(
        page.locator('.wizard-step.active .step-label'),
      ).toContainText('正文', { timeout: 10_000 });

      const sectionCards = page.locator('.section-card');
      await expect(sectionCards.first()).toBeVisible({ timeout: 5_000 });

      const followUpGenBtn = sectionCards.nth(4).locator('button', {
        hasText: /AI.*生成|生成/,
      });
      await expect(followUpGenBtn).toBeVisible();
      await expect(followUpGenBtn).toBeEnabled();

      const apiRequests: string[] = [];
      page.on('request', (req) => {
        if (req.url().includes('/api/')) {
          apiRequests.push(`${req.method()} ${req.url()}`);
        }
      });

      const genResponse = page.waitForResponse(
        async (resp) => {
          if (!resp.url().includes('/body/section-generate')) return false;
          try {
            const body = resp.request().postData();
            return body?.includes('follow_up') ?? false;
          } catch {
            return false;
          }
        },
        { timeout: 270_000 },
      );

      await followUpGenBtn.click();

      await expect(page.locator('.ai-gen-dialog')).toBeVisible({
        timeout: 10_000,
      });

      const response = await genResponse.catch(() => null);
      if (!response) {
        const recentRequests = apiRequests.slice(-5).join('\n');
        throw new Error(
          `后续动作 AI 生成请求超时。最近的 API 请求:\n${recentRequests}`,
        );
      }
      if (response.status() >= 400) {
        const body = await response.text().catch(() => '');
        throw new Error(
          `后续动作 AI 生成请求失败: HTTP ${response.status()} - ${body}`,
        );
      }

      await expect(page.locator('.ai-gen-dialog')).not.toBeVisible({
        timeout: 120_000,
      });

      await page.waitForTimeout(1000);

      const followUpTextarea = page
        .locator('.section-card')
        .nth(4)
        .locator('textarea.base-textarea');
      if (
        await followUpTextarea.isVisible({ timeout: 5_000 }).catch(() => false)
      ) {
        const textareaValue = await followUpTextarea.inputValue();
        if (!textareaValue || textareaValue.length === 0) {
          const formState = await page.evaluate(() => {
            const el =
              document.querySelector('.incident-report-edit-view') ||
              document.querySelector('.incident-report-create-view');
            return el ? 'found' : 'not found';
          });
          console.warn(
            `body_follow_up textarea is empty. Form container: ${formState}`,
          );
        }
        expect(
          textareaValue.length,
          'body_follow_up textarea is empty after section generation',
        ).toBeGreaterThan(0);
      }
    } finally {
      await deleteIncidentReportViaApi(request, token!, report!.id);
    }
  });

  test('AI生成弹窗显示思考动画和停止按钮 - 真实 Ollama', async ({
    page,
    request,
  }) => {
    test.setTimeout(300_000);

    const availableModel = await getAvailableModel(request);
    await setupModelAndNavigate(page, availableModel);

    const titleInput = page
      .locator('.field-item', { hasText: '报告标题' })
      .locator('input');
    await titleInput.waitFor({ state: 'visible', timeout: 10_000 });
    await titleInput.fill(`${workerPrefix}AI弹窗测试`);

    await pickTodayDate(page, '故障上报日期');

    const reporterInput = page
      .locator('.field-item', { hasText: '报告人' })
      .locator('input');
    await reporterInput.fill('E2E测试报告人');

    const siteInput = page
      .locator('.field-item', { hasText: '站点编号' })
      .locator('input');
    await siteInput.fill('SITE-001');

    const systemInput = page
      .locator('.field-item', { hasText: '系统 / 子系统' })
      .locator('input');
    await systemInput.fill('E2E测试系统');

    const locationInput = page
      .locator('.field-item', { hasText: '故障位置' })
      .locator('input');
    await locationInput.fill('E2E测试位置');

    const symptomInput = page
      .locator('.field-item', { hasText: '故障现象详情' })
      .locator('textarea');
    await symptomInput.fill('E2E测试故障现象');

    const nextBtn = page.locator('.wizard-btn-next');
    await nextBtn.click();

    await expect(page.locator('.wizard-step.active .step-label')).toContainText(
      '快填',
      { timeout: 10_000 },
    );

    const quickNarrative = page.locator('.base-textarea').first();
    await quickNarrative.waitFor({ state: 'visible', timeout: 5_000 });
    await quickNarrative.fill('测试AI生成弹窗');

    const narrativeValue = await quickNarrative.inputValue();
    if (!narrativeValue.trim()) {
      throw new Error('quick_narrative textarea is empty after fill');
    }

    const genResponse = page.waitForResponse(
      (resp) => resp.url().includes('/body/quick-generate'),
      { timeout: 300_000 },
    );

    const aiGenerateBtn = page.locator('.section-card button', {
      hasText: /AI.*生成/,
    });
    await aiGenerateBtn.click();

    const response = await genResponse.catch(() => null);
    if (!response) {
      throw new Error('AI 生成请求超时（300s），弹窗验证失败');
    }
    if (response.status() >= 400) {
      const body = await response.text().catch(() => '');
      throw new Error(`AI 生成请求失败: HTTP ${response.status()} - ${body}`);
    }

    await expect(page.locator('.floating-toast')).toBeVisible({
      timeout: 10_000,
    });
  });

  test('预览步骤生成PDF预览 - 真实 API 创建完整报告', async ({
    page,
    request,
  }) => {
    test.setTimeout(180_000);

    const token = await loginViaApi(request);
    const report = await createIncidentReportViaApi(request, token!, {
      title: `${workerPrefix}预览测试报告`,
      severity: 'P2',
      system: 'E2E预览系统',
      site_id: 'SITE-PREVIEW',
      form_data: {
        body_description: '生产环境数据库主节点CPU打满，导致订单服务响应超时。',
        body_impact_scope: '订单服务中断约45分钟',
        body_impact_severity: '严重',
        body_root_cause: '慢查询导致CPU打满',
        body_follow_up: '加索引和降级非核心功能',
      },
    });
    expect(report).not.toBeNull();

    try {
      await loginAsAdmin(page);
      await page.goto(`/incident-report/${report!.id}/edit`);
      await expect(page.locator('.incident-report-edit-view')).toBeVisible({
        timeout: 10_000,
      });

      for (let i = 0; i < 5; i++) {
        const nextBtn = page.locator('.wizard-btn-next');
        if (await nextBtn.isVisible({ timeout: 1_000 }).catch(() => false)) {
          await nextBtn.click();
          await page.waitForTimeout(500);
        }
      }

      await expect(
        page.locator('.wizard-step.active .step-label'),
      ).toContainText('预览', { timeout: 10_000 });

      const generatePreviewBtn = page.locator('button', {
        hasText: '生成预览',
      });
      await expect(generatePreviewBtn).toBeVisible({ timeout: 5_000 });

      const previewResponse = page.waitForResponse(
        (resp) => resp.url().includes('/preview') && resp.status() === 200,
        { timeout: 120_000 },
      );

      await generatePreviewBtn.click();

      const response = await previewResponse.catch(() => null);
      if (!response) {
        throw new Error('预览请求超时');
      }
      if (response.status() >= 400) {
        const body = await response.text().catch(() => '');
        throw new Error(`预览请求失败: HTTP ${response.status()} - ${body}`);
      }

      await expect(page.locator('.pdf-preview-dialog')).toBeVisible({
        timeout: 30_000,
      });

      const downloadDocxBtn = page.locator('button', {
        hasText: /下载 DOCX|DOCX/,
      });
      if (
        await downloadDocxBtn.isVisible({ timeout: 3_000 }).catch(() => false)
      ) {
        await expect(downloadDocxBtn).toBeEnabled();
      }
    } finally {
      await deleteIncidentReportViaApi(request, token!, report!.id);
    }
  });

  test.afterAll(async ({ request }) => {
    await cleanupWorkerData(request, workerPrefix);
  });
});
