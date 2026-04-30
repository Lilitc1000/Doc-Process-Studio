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

test.describe('事故报告编辑页', () => {
  let workerPrefix: string;

  test.beforeAll(async ({ request }, testInfo) => {
    workerPrefix = getWorkerPrefix(testInfo.workerIndex);
    await addRateLimitWhitelist(request);
  });

  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test.afterAll(async ({ request }) => {
    await cleanupWorkerData(request, workerPrefix);
  });

  test('访问不存在的报告显示报告不存在', async ({ page }) => {
    await page.goto('/incident-report/nonexistent-id/edit');
    await expect(page.locator('.edit-empty')).toHaveText('报告不存在');
  });

  test('编辑页显示5步向导', async ({ page, request }) => {
    const token = await loginViaApi(request);
    const report = await createIncidentReportViaApi(request, token!, {
      title: `${workerPrefix}向导步骤测试`,
    });
    expect(report).not.toBeNull();

    try {
      await page.goto(`/incident-report/${report!.id}/edit`);
      await expect(page.locator('.incident-report-edit-view')).toBeVisible({
        timeout: 10_000,
      });

      const steps = page.locator('.wizard-step');
      await expect(steps.first()).toBeVisible({ timeout: 5_000 });
      const count = await steps.count();
      expect(count).toBe(5);

      const stepLabels = await steps.locator('.step-label').allTextContents();
      expect(stepLabels[0]).toMatch(/首页|Cover/);
      expect(stepLabels[1]).toMatch(/快填|QuickFill/);
      expect(stepLabels[2]).toMatch(/正文|Body/);
      expect(stepLabels[3]).toMatch(/附录|Appendix/);
      expect(stepLabels[4]).toMatch(/预览|Preview/);
    } finally {
      await deleteIncidentReportViaApi(request, token!, report!.id);
    }
  });

  test('从详情页进入编辑页', async ({ page, request }) => {
    const token = await loginViaApi(request);
    const report = await createIncidentReportViaApi(request, token!, {
      title: `${workerPrefix}进入编辑页测试`,
    });
    expect(report).not.toBeNull();

    try {
      await page.goto(`/incident-report/${report!.id}`);
      await expect(page.locator('.incident-report-detail-view')).toBeVisible({
        timeout: 10_000,
      });

      const editBtn = page.locator('.detail-header-right button', {
        hasText: '编辑',
      });
      await expect(editBtn).toBeVisible();
      await editBtn.click();
      await expect(page).toHaveURL(/\/incident-report\/[^/]+\/edit/);
      await expect(page.locator('.incident-report-edit-view')).toBeVisible({
        timeout: 10_000,
      });
    } finally {
      await deleteIncidentReportViaApi(request, token!, report!.id);
    }
  });

  test('编辑页首页步骤显示表单区域和标题输入框', async ({ page, request }) => {
    const token = await loginViaApi(request);
    const report = await createIncidentReportViaApi(request, token!, {
      title: `${workerPrefix}表单区域测试`,
    });
    expect(report).not.toBeNull();

    try {
      await page.goto(`/incident-report/${report!.id}/edit`);
      await expect(page.locator('.incident-report-edit-view')).toBeVisible({
        timeout: 10_000,
      });

      await expect(
        page.locator('.wizard-step.active .step-label'),
      ).toContainText('首页', { timeout: 5_000 });

      await expect(page.locator('.field-item').first()).toBeVisible();
    } finally {
      await deleteIncidentReportViaApi(request, token!, report!.id);
    }
  });

  test('编辑页显示取消和下一步按钮', async ({ page, request }) => {
    const token = await loginViaApi(request);
    const report = await createIncidentReportViaApi(request, token!, {
      title: `${workerPrefix}按钮测试`,
    });
    expect(report).not.toBeNull();

    try {
      await page.goto(`/incident-report/${report!.id}/edit`);
      await expect(page.locator('.incident-report-edit-view')).toBeVisible({
        timeout: 10_000,
      });
      await expect(
        page.locator('.wizard-actions button', { hasText: '取消' }),
      ).toBeVisible();
      await expect(page.locator('.wizard-btn-next')).toBeVisible();
    } finally {
      await deleteIncidentReportViaApi(request, token!, report!.id);
    }
  });

  test('点击取消返回列表页', async ({ page, request }) => {
    const token = await loginViaApi(request);
    const report = await createIncidentReportViaApi(request, token!, {
      title: `${workerPrefix}取消返回测试`,
    });
    expect(report).not.toBeNull();

    try {
      await page.goto(`/incident-report/${report!.id}/edit`);
      await expect(page.locator('.incident-report-edit-view')).toBeVisible({
        timeout: 10_000,
      });

      await page.locator('.wizard-actions button', { hasText: '取消' }).click();
      await expect(page).toHaveURL('/incident-report');
    } finally {
      await deleteIncidentReportViaApi(request, token!, report!.id);
    }
  });

  test('编辑页取消按钮返回到列表页', async ({ page, request }) => {
    const token = await loginViaApi(request);
    const report = await createIncidentReportViaApi(request, token!, {
      title: `${workerPrefix}返回列表页测试`,
    });
    expect(report).not.toBeNull();

    try {
      await page.goto(`/incident-report/${report!.id}/edit`);
      await expect(page.locator('.incident-report-edit-view')).toBeVisible({
        timeout: 10_000,
      });

      const cancelBtn = page.locator('.wizard-actions button', {
        hasText: '取消',
      });
      await cancelBtn.click();
      await expect(page).toHaveURL('/incident-report');
    } finally {
      await deleteIncidentReportViaApi(request, token!, report!.id);
    }
  });

  test('编辑页向导步骤切换 - 从首页到AI正文', async ({ page, request }) => {
    const token = await loginViaApi(request);
    const report = await createIncidentReportViaApi(request, token!, {
      title: `${workerPrefix}步骤切换测试`,
    });
    expect(report).not.toBeNull();

    try {
      await page.goto(`/incident-report/${report!.id}/edit`);
      await expect(page.locator('.incident-report-edit-view')).toBeVisible({
        timeout: 10_000,
      });

      await expect(
        page.locator('.wizard-step.active .step-label'),
      ).toContainText('首页');

      const nextBtn = page.locator('.wizard-btn-next');
      await nextBtn.click();

      await expect(
        page.locator('.wizard-step.active .step-label'),
      ).toContainText('快填', { timeout: 5_000 });

      await nextBtn.click();

      await expect(
        page.locator('.wizard-step.active .step-label'),
      ).toContainText('正文', { timeout: 5_000 });

      const generateButtons = page.locator('.section-card button', {
        hasText: /AI.*生成|生成/,
      });
      const btnCount = await generateButtons.count();
      expect(btnCount).toBeGreaterThanOrEqual(1);
    } finally {
      await deleteIncidentReportViaApi(request, token!, report!.id);
    }
  });

  test('编辑页AI正文步骤显示分段生成按钮', async ({ page, request }) => {
    const token = await loginViaApi(request);
    const report = await createIncidentReportViaApi(request, token!, {
      title: `${workerPrefix}AI正文按钮测试`,
    });
    expect(report).not.toBeNull();

    try {
      await page.goto(`/incident-report/${report!.id}/edit`);
      await expect(page.locator('.incident-report-edit-view')).toBeVisible({
        timeout: 10_000,
      });

      const nextBtn = page.locator('.wizard-btn-next');
      await nextBtn.click();
      await expect(
        page.locator('.wizard-step.active .step-label'),
      ).toContainText('快填', { timeout: 5_000 });
      await nextBtn.click();

      await expect(
        page.locator('.wizard-step.active .step-label'),
      ).toContainText('正文', { timeout: 5_000 });

      const sectionGenButtons = page.locator('.section-header button', {
        hasText: /AI.*生成/,
      });
      const sectionBtnCount = await sectionGenButtons.count();
      expect(sectionBtnCount).toBe(4);

      for (let i = 0; i < sectionBtnCount; i++) {
        await expect(sectionGenButtons.nth(i)).toBeVisible();
        await expect(sectionGenButtons.nth(i)).toBeEnabled();
      }

      const timelineItemGenButtons = page.locator('.timeline-row button', {
        hasText: /AI.*生成/,
      });
      const timelineBtnCount = await timelineItemGenButtons.count();
      expect(timelineBtnCount).toBeGreaterThanOrEqual(1);
    } finally {
      await deleteIncidentReportViaApi(request, token!, report!.id);
    }
  });

  test('编辑页预览步骤显示生成预览按钮', async ({ page, request }) => {
    const token = await loginViaApi(request);
    const report = await createIncidentReportViaApi(request, token!, {
      title: `${workerPrefix}预览步骤测试`,
    });
    expect(report).not.toBeNull();

    try {
      await page.goto(`/incident-report/${report!.id}/edit`);
      await expect(page.locator('.incident-report-edit-view')).toBeVisible({
        timeout: 10_000,
      });

      const nextBtn = page.locator('.wizard-btn-next');
      for (let i = 0; i < 4; i++) {
        await nextBtn.click();
        await page.waitForTimeout(500);
      }

      await expect(
        page.locator('.wizard-step.active .step-label'),
      ).toContainText('预览', { timeout: 5_000 });

      const generatePreviewBtn = page.locator('button', {
        hasText: '生成预览',
      });
      await expect(generatePreviewBtn).toBeVisible();
      await expect(generatePreviewBtn).toBeEnabled();
    } finally {
      await deleteIncidentReportViaApi(request, token!, report!.id);
    }
  });
});
