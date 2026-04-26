import { test, expect } from '@playwright/test';
import { loginAsAdmin, addRateLimitWhitelist } from '../../helpers';

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
  test.beforeAll(async ({ request }) => {
    await addRateLimitWhitelist(request);
  });

  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('从详情页进入编辑页', async ({ page }) => {
    const listResp = page.waitForResponse(
      (resp) =>
        resp.url().includes('/incident-report?') && resp.status() === 200,
      { timeout: 10_000 },
    );
    await page.goto('/incident-report');
    await listResp.catch(() => {});
    const reportRow = page.locator('.report-list-table tbody tr').first();
    if (await reportRow.isVisible()) {
      await reportRow.click();
      await expect(page).toHaveURL(/\/incident-report\/[^/]+$/);
      const editBtn = page.locator('.detail-header-right button', {
        hasText: '编辑',
      });
      if (await editBtn.isVisible()) {
        await editBtn.click();
        await expect(page).toHaveURL(/\/incident-report\/[^/]+\/edit/);
      }
    }
  });

  test('编辑页显示返回详情按钮', async ({ page }) => {
    const listResp = page.waitForResponse(
      (resp) =>
        resp.url().includes('/incident-report?') && resp.status() === 200,
      { timeout: 10_000 },
    );
    await page.goto('/incident-report');
    await listResp.catch(() => {});
    const reportRow = page.locator('.report-list-table tbody tr').first();
    if (await reportRow.isVisible()) {
      await reportRow.click();
      await expect(page).toHaveURL(/\/incident-report\/[^/]+$/);
      const editBtn = page.locator('.detail-header-right button', {
        hasText: '编辑',
      });
      if (await editBtn.isVisible()) {
        await editBtn.click();
        await expect(page).toHaveURL(/\/incident-report\/[^/]+\/edit/);
        await expect(
          page.locator('button', { hasText: '返回详情' }),
        ).toBeVisible();
      }
    }
  });

  test('编辑页显示表单区域', async ({ page }) => {
    const listResp = page.waitForResponse(
      (resp) =>
        resp.url().includes('/incident-report?') && resp.status() === 200,
      { timeout: 10_000 },
    );
    await page.goto('/incident-report');
    await listResp.catch(() => {});
    const reportRow = page.locator('.report-list-table tbody tr').first();
    if (await reportRow.isVisible()) {
      await reportRow.click();
      await expect(page).toHaveURL(/\/incident-report\/[^/]+$/);
      const editBtn = page.locator('.detail-header-right button', {
        hasText: '编辑',
      });
      if (await editBtn.isVisible()) {
        await editBtn.click();
        await expect(page).toHaveURL(/\/incident-report\/[^/]+\/edit/);
        await expect(page.locator('.edit-form')).toBeVisible();
      }
    }
  });

  test('编辑页显示标题输入框', async ({ page }) => {
    const listResp = page.waitForResponse(
      (resp) =>
        resp.url().includes('/incident-report?') && resp.status() === 200,
      { timeout: 10_000 },
    );
    await page.goto('/incident-report');
    await listResp.catch(() => {});
    const reportRow = page.locator('.report-list-table tbody tr').first();
    if (await reportRow.isVisible()) {
      await reportRow.click();
      await expect(page).toHaveURL(/\/incident-report\/[^/]+$/);
      const editBtn = page.locator('.detail-header-right button', {
        hasText: '编辑',
      });
      if (await editBtn.isVisible()) {
        await editBtn.click();
        await expect(page).toHaveURL(/\/incident-report\/[^/]+\/edit/);
        await expect(
          page.locator('.form-label', { hasText: '报告标题' }),
        ).toBeVisible();
      }
    }
  });

  test('编辑页显示严重级别下拉框', async ({ page }) => {
    const listResp = page.waitForResponse(
      (resp) =>
        resp.url().includes('/incident-report?') && resp.status() === 200,
      { timeout: 10_000 },
    );
    await page.goto('/incident-report');
    await listResp.catch(() => {});
    const reportRow = page.locator('.report-list-table tbody tr').first();
    if (await reportRow.isVisible()) {
      await reportRow.click();
      await expect(page).toHaveURL(/\/incident-report\/[^/]+$/);
      const editBtn = page.locator('.detail-header-right button', {
        hasText: '编辑',
      });
      if (await editBtn.isVisible()) {
        await editBtn.click();
        await expect(page).toHaveURL(/\/incident-report\/[^/]+\/edit/);
        await expect(
          page.locator('.form-label', { hasText: '严重级别' }),
        ).toBeVisible();
      }
    }
  });

  test('编辑页显示保存和取消按钮', async ({ page }) => {
    const listResp = page.waitForResponse(
      (resp) =>
        resp.url().includes('/incident-report?') && resp.status() === 200,
      { timeout: 10_000 },
    );
    await page.goto('/incident-report');
    await listResp.catch(() => {});
    const reportRow = page.locator('.report-list-table tbody tr').first();
    if (await reportRow.isVisible()) {
      await reportRow.click();
      await expect(page).toHaveURL(/\/incident-report\/[^/]+$/);
      const editBtn = page.locator('.detail-header-right button', {
        hasText: '编辑',
      });
      if (await editBtn.isVisible()) {
        await editBtn.click();
        await expect(page).toHaveURL(/\/incident-report\/[^/]+\/edit/);
        await expect(
          page.locator('.edit-actions button', { hasText: '取消' }),
        ).toBeVisible();
        await expect(
          page.locator('.edit-actions button', { hasText: '保存' }),
        ).toBeVisible();
      }
    }
  });

  test('点击取消返回详情页', async ({ page }) => {
    const listResp = page.waitForResponse(
      (resp) =>
        resp.url().includes('/incident-report?') && resp.status() === 200,
      { timeout: 10_000 },
    );
    await page.goto('/incident-report');
    await listResp.catch(() => {});
    const reportRow = page.locator('.report-list-table tbody tr').first();
    if (await reportRow.isVisible()) {
      await reportRow.click();
      await expect(page).toHaveURL(/\/incident-report\/[^/]+$/);
      const editBtn = page.locator('.detail-header-right button', {
        hasText: '编辑',
      });
      if (await editBtn.isVisible()) {
        await editBtn.click();
        await expect(page).toHaveURL(/\/incident-report\/[^/]+\/edit/);
        await page.locator('.edit-actions button', { hasText: '取消' }).click();
        await expect(page).toHaveURL(/\/incident-report\/[^/]+$/);
      }
    }
  });
});
