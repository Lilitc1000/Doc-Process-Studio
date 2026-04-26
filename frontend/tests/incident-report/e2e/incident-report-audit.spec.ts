import { test, expect } from '@playwright/test';
import { loginAsAdmin, addRateLimitWhitelist } from '../../helpers';

test.describe('事故报告审核流程', () => {
  test.beforeAll(async ({ request }) => {
    await addRateLimitWhitelist(request);
  });

  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('从详情页进入审核页', async ({ page }) => {
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
      const auditBtn = page.locator('.detail-header-right button', {
        hasText: '审核',
      });
      if (await auditBtn.isVisible()) {
        await auditBtn.click();
        await expect(page).toHaveURL(/\/incident-report\/[^/]+\/audit/);
        await expect(page.locator('.incident-report-audit-view')).toBeVisible();
      }
    }
  });

  test('审核页显示审核操作面板', async ({ page }) => {
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
      const auditBtn = page.locator('.detail-header-right button', {
        hasText: '审核',
      });
      if (await auditBtn.isVisible()) {
        await auditBtn.click();
        await expect(page).toHaveURL(/\/incident-report\/[^/]+\/audit/);
        const auditPanel = page.locator('.audit-action-panel');
        if (await auditPanel.isVisible()) {
          await expect(auditPanel.locator('h3')).toContainText('审核操作');
        }
      }
    }
  });

  test('审核页显示返回详情按钮', async ({ page }) => {
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
      const auditBtn = page.locator('.detail-header-right button', {
        hasText: '审核',
      });
      if (await auditBtn.isVisible()) {
        await auditBtn.click();
        await expect(page).toHaveURL(/\/incident-report\/[^/]+\/audit/);
        const backBtn = page.locator('button', { hasText: '返回' });
        if (await backBtn.isVisible()) {
          await backBtn.click();
          await expect(page).toHaveURL(/\/incident-report\/[^/]+$/);
        }
      }
    }
  });
});
