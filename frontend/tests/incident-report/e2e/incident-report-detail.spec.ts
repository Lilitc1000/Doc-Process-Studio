import { test, expect } from '@playwright/test';
import {
  getWorkerPrefix,
  loginAsAdmin,
  loginViaApi,
  addRateLimitWhitelist,
  createIncidentReportViaApi,
  deleteIncidentReportViaApi,
} from '../../helpers';

test.describe('事故报告详情页 - 不存在的报告', () => {
  test.beforeAll(async ({ request }) => {
    await addRateLimitWhitelist(request);
  });

  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('访问不存在的报告显示报告不存在', async ({ page }) => {
    await page.goto('/incident-report/nonexistent-id');
    await page.waitForTimeout(2000);
    await expect(page.locator('.detail-empty')).toHaveText('报告不存在');
  });

  test('加载中显示加载状态', async ({ page }) => {
    await page.goto('/incident-report/nonexistent-id');
    const loading = page.locator('.detail-loading');
    if (await loading.isVisible()) {
      await expect(loading).toHaveText('加载中...');
    }
  });
});

test.describe('事故报告详情页 - 已有报告', () => {
  let workerPrefix: string;

  test.beforeAll(async ({ request }, testInfo) => {
    workerPrefix = getWorkerPrefix(testInfo.workerIndex);
    await addRateLimitWhitelist(request);
  });

  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('从列表页点击报告行进入详情页', async ({ page, request }) => {
    const token = await loginViaApi(request);
    const report = await createIncidentReportViaApi(request, token!, {
      title: `${workerPrefix}列表进入详情测试`,
    });
    expect(report).not.toBeNull();

    try {
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
        .filter({ hasText: `${workerPrefix}列表进入详情测试` });
      await expect(reportRow).toBeVisible({ timeout: 10_000 });
      await reportRow.locator('.action-view').click();
      await expect(page).toHaveURL(/\/incident-report\/[^/]+$/);
      await expect(page.locator('.incident-report-detail-view')).toBeVisible();
    } finally {
      await deleteIncidentReportViaApi(request, token!, report!.id);
    }
  });

  test('详情页显示返回列表按钮', async ({ page, request }) => {
    const token = await loginViaApi(request);
    const report = await createIncidentReportViaApi(request, token!, {
      title: `${workerPrefix}返回列表按钮测试`,
    });
    expect(report).not.toBeNull();

    try {
      await page.goto(`/incident-report/${report!.id}`);
      await expect(
        page.locator('.detail-header button', { hasText: '返回列表' }),
      ).toBeVisible();
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
      await expect(page.locator('.report-comments')).toBeVisible();
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
      await expect(page.locator('.report-audit-timeline')).toBeVisible();
    } finally {
      await deleteIncidentReportViaApi(request, token!, report!.id);
    }
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
      await expect(page.locator('.detail-title')).toBeVisible();
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
      await page
        .locator('.detail-header button', { hasText: '返回列表' })
        .click();
      await expect(page).toHaveURL('/incident-report');
    } finally {
      await deleteIncidentReportViaApi(request, token!, report!.id);
    }
  });
});
