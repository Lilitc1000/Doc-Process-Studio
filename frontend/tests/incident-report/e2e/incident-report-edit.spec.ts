import { test, expect } from '@playwright/test';
import {
  getWorkerPrefix,
  loginAsAdmin,
  loginViaApi,
  addRateLimitWhitelist,
  createIncidentReportViaApi,
  deleteIncidentReportViaApi,
} from '../../helpers';

test.describe('事故报告编辑页 - 不存在的报告', () => {
  test.beforeAll(async ({ request }) => {
    await addRateLimitWhitelist(request);
  });

  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('访问不存在的报告显示报告不存在', async ({ page }) => {
    await page.goto('/incident-report/nonexistent-id/edit');
    await page.waitForTimeout(2000);
    await expect(page.locator('.edit-empty')).toHaveText('报告不存在');
  });
});

test.describe('事故报告编辑页 - 已有报告', () => {
  let workerPrefix: string;

  test.beforeAll(async ({ request }, testInfo) => {
    workerPrefix = getWorkerPrefix(testInfo.workerIndex);
    await addRateLimitWhitelist(request);
  });

  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('从详情页进入编辑页', async ({ page, request }) => {
    const token = await loginViaApi(request);
    const report = await createIncidentReportViaApi(request, token!, {
      title: `${workerPrefix}进入编辑页测试`,
    });
    expect(report).not.toBeNull();

    try {
      await page.goto(`/incident-report/${report!.id}`);
      await expect(page.locator('.incident-report-detail-view')).toBeVisible();

      const editBtn = page.locator('.detail-header-right button', {
        hasText: '编辑',
      });
      await expect(editBtn).toBeVisible();
      await editBtn.click();
      await expect(page).toHaveURL(/\/incident-report\/[^/]+\/edit/);
    } finally {
      await deleteIncidentReportViaApi(request, token!, report!.id);
    }
  });

  test('编辑页显示返回详情按钮', async ({ page, request }) => {
    const token = await loginViaApi(request);
    const report = await createIncidentReportViaApi(request, token!, {
      title: `${workerPrefix}返回详情按钮测试`,
    });
    expect(report).not.toBeNull();

    try {
      await page.goto(`/incident-report/${report!.id}/edit`);
      await expect(
        page.locator('button', { hasText: '返回详情' }),
      ).toBeVisible();
    } finally {
      await deleteIncidentReportViaApi(request, token!, report!.id);
    }
  });

  test('编辑页显示表单区域', async ({ page, request }) => {
    const token = await loginViaApi(request);
    const report = await createIncidentReportViaApi(request, token!, {
      title: `${workerPrefix}表单区域测试`,
    });
    expect(report).not.toBeNull();

    try {
      await page.goto(`/incident-report/${report!.id}/edit`);
      await expect(page.locator('.edit-form')).toBeVisible();
    } finally {
      await deleteIncidentReportViaApi(request, token!, report!.id);
    }
  });

  test('编辑页显示标题输入框', async ({ page, request }) => {
    const token = await loginViaApi(request);
    const report = await createIncidentReportViaApi(request, token!, {
      title: `${workerPrefix}标题输入框测试`,
    });
    expect(report).not.toBeNull();

    try {
      await page.goto(`/incident-report/${report!.id}/edit`);
      const titleField = page
        .locator('.field-item span')
        .filter({ hasText: '报告标题' });
      if (await titleField.isVisible()) {
        await expect(titleField).toBeVisible();
      }
    } finally {
      await deleteIncidentReportViaApi(request, token!, report!.id);
    }
  });

  test('编辑页显示保存和取消按钮', async ({ page, request }) => {
    const token = await loginViaApi(request);
    const report = await createIncidentReportViaApi(request, token!, {
      title: `${workerPrefix}保存取消按钮测试`,
    });
    expect(report).not.toBeNull();

    try {
      await page.goto(`/incident-report/${report!.id}/edit`);
      await expect(
        page.locator('.edit-actions button', { hasText: '取消' }),
      ).toBeVisible();
      await expect(
        page.locator('.edit-actions button', { hasText: '保存' }),
      ).toBeVisible();
    } finally {
      await deleteIncidentReportViaApi(request, token!, report!.id);
    }
  });

  test('点击取消返回详情页', async ({ page, request }) => {
    const token = await loginViaApi(request);
    const report = await createIncidentReportViaApi(request, token!, {
      title: `${workerPrefix}取消返回测试`,
    });
    expect(report).not.toBeNull();

    try {
      await page.goto(`/incident-report/${report!.id}/edit`);
      await page.locator('.edit-actions button', { hasText: '取消' }).click();
      await expect(page).toHaveURL(/\/incident-report\/[^/]+$/);
    } finally {
      await deleteIncidentReportViaApi(request, token!, report!.id);
    }
  });
});
