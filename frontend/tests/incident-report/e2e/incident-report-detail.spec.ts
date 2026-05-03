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

test.describe('事故报告详情页', () => {
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
    await page.goto('/incident-report/nonexistent-id');
    await expect(page.locator('.detail-empty')).toHaveText('报告不存在');
  });

  test('加载中显示加载状态', async ({ page }) => {
    const detailResp = page.waitForResponse(
      (resp) =>
        resp.url().includes('/incident-report/reports/nonexistent-id') &&
        resp.status() === 404,
      { timeout: 10_000 },
    );
    await page.goto('/incident-report/nonexistent-id');
    const loading = page.locator('.detail-loading');
    if (await loading.isVisible()) {
      await expect(loading).toHaveText('加载中...');
    }
    await detailResp;
  });

  test('详情页显示报告编号和标题', async ({ page, request }) => {
    const token = await loginViaApi(request);
    const report = await createIncidentReportViaApi(request, token!, {
      title: `${workerPrefix}编号标题测试`,
    });
    expect(report).not.toBeNull();

    try {
      await page.goto(`/incident-report/${report!.id}`);
      await expect(page.locator('.incident-report-detail-view')).toBeVisible({
        timeout: 10_000,
      });
      await expect(page.locator('.detail-ref')).toBeVisible();
      await expect(page.locator('.detail-title')).toContainText(
        `${workerPrefix}编号标题测试`,
      );
    } finally {
      await deleteIncidentReportViaApi(request, token!, report!.id);
    }
  });

  test('详情页显示基本信息卡片', async ({ page, request }) => {
    const token = await loginViaApi(request);
    const report = await createIncidentReportViaApi(request, token!, {
      title: `${workerPrefix}基本信息卡片测试`,
      severity: 'P0',
      system: 'E2E系统',
      site_id: 'SITE-001',
    });
    expect(report).not.toBeNull();

    try {
      await page.goto(`/incident-report/${report!.id}`);
      await expect(page.locator('.incident-report-detail-view')).toBeVisible({
        timeout: 10_000,
      });
      await expect(page.locator('.detail-info-card')).toBeVisible();
    } finally {
      await deleteIncidentReportViaApi(request, token!, report!.id);
    }
  });

  test('详情页显示状态徽章', async ({ page, request }) => {
    const token = await loginViaApi(request);
    const report = await createIncidentReportViaApi(request, token!, {
      title: `${workerPrefix}状态徽章测试`,
    });
    expect(report).not.toBeNull();

    try {
      await page.goto(`/incident-report/${report!.id}`);
      await expect(page.locator('.incident-report-detail-view')).toBeVisible({
        timeout: 10_000,
      });
      await expect(page.locator('.status-badge')).toBeVisible();
    } finally {
      await deleteIncidentReportViaApi(request, token!, report!.id);
    }
  });

  test('详情页显示评论区域', async ({ page, request }) => {
    const token = await loginViaApi(request);
    const report = await createIncidentReportViaApi(request, token!, {
      title: `${workerPrefix}评论区域测试`,
    });
    expect(report).not.toBeNull();

    try {
      await page.goto(`/incident-report/${report!.id}`);
      await expect(page.locator('.incident-report-detail-view')).toBeVisible({
        timeout: 10_000,
      });
      await expect(page.locator('.report-comments')).toBeVisible();
    } finally {
      await deleteIncidentReportViaApi(request, token!, report!.id);
    }
  });

  test('详情页以卡片形式展示报告内容', async ({ page, request }) => {
    const token = await loginViaApi(request);
    const report = await createIncidentReportViaApi(request, token!, {
      title: `${workerPrefix}卡片展示测试`,
      severity: 'P1',
      system: 'E2E测试系统',
      site_id: 'SITE-TABLE',
    });
    expect(report).not.toBeNull();

    try {
      await page.goto(`/incident-report/${report!.id}`);
      await expect(page.locator('.incident-report-detail-view')).toBeVisible({
        timeout: 10_000,
      });

      await expect(page.locator('.detail-sections')).toBeVisible({
        timeout: 5_000,
      });
      await expect(page.locator('.detail-section').first()).toBeVisible();
      await expect(page.locator('.section-title').first()).toBeVisible();
      await expect(page.locator('.field-row').first()).toBeVisible();
    } finally {
      await deleteIncidentReportViaApi(request, token!, report!.id);
    }
  });

  test('详情页卡片包含故障记录分区', async ({ page, request }) => {
    const token = await loginViaApi(request);
    const report = await createIncidentReportViaApi(request, token!, {
      title: `${workerPrefix}故障记录分区测试`,
      system: 'E2E测试系统',
      site_id: 'SITE-SECTION-A',
    });
    expect(report).not.toBeNull();

    try {
      await page.goto(`/incident-report/${report!.id}`);
      await expect(page.locator('.incident-report-detail-view')).toBeVisible({
        timeout: 10_000,
      });

      const sectionA = page.locator('.detail-section', {
        hasText: '故障记录',
      });
      await expect(sectionA).toBeVisible({ timeout: 5_000 });
    } finally {
      await deleteIncidentReportViaApi(request, token!, report!.id);
    }
  });

  test('详情页显示审核时间线', async ({ page, request }) => {
    const token = await loginViaApi(request);
    const report = await createIncidentReportViaApi(request, token!, {
      title: `${workerPrefix}审核时间线测试`,
    });
    expect(report).not.toBeNull();

    try {
      await page.goto(`/incident-report/${report!.id}`);
      await expect(page.locator('.incident-report-detail-view')).toBeVisible({
        timeout: 10_000,
      });
      await expect(page.locator('.report-audit-timeline')).toBeVisible();
    } finally {
      await deleteIncidentReportViaApi(request, token!, report!.id);
    }
  });

  test('点击返回列表按钮导航回列表页', async ({ page, request }) => {
    const token = await loginViaApi(request);
    const report = await createIncidentReportViaApi(request, token!, {
      title: `${workerPrefix}返回列表导航测试`,
    });
    expect(report).not.toBeNull();

    try {
      await page.goto(`/incident-report/${report!.id}`);
      await expect(page.locator('.incident-report-detail-view')).toBeVisible({
        timeout: 10_000,
      });
      await page
        .locator('.detail-header button', { hasText: '返回列表' })
        .click();
      await expect(page).toHaveURL('/incident-report');
    } finally {
      await deleteIncidentReportViaApi(request, token!, report!.id);
    }
  });

  test('点击导航栏标题导航到列表页', async ({ page, request }) => {
    const token = await loginViaApi(request);
    const report = await createIncidentReportViaApi(request, token!, {
      title: `${workerPrefix}标题导航测试`,
    });
    expect(report).not.toBeNull();

    try {
      await page.goto(`/incident-report/${report!.id}`);
      await expect(page.locator('.incident-report-detail-view')).toBeVisible({
        timeout: 10_000,
      });
      await expect(page.locator('.app-header-title-btn')).toBeVisible();
      await page.locator('.app-header-title-btn').click();
      await expect(page).toHaveURL('/incident-report');
    } finally {
      await deleteIncidentReportViaApi(request, token!, report!.id);
    }
  });
});
