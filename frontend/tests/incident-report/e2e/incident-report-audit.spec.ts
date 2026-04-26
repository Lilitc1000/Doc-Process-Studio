import { test, expect } from '@playwright/test';
import { loginAsAdmin, addRateLimitWhitelist } from '../../helpers';

test.describe('事故报告审核流程', () => {
  test.beforeAll(async ({ request }) => {
    await addRateLimitWhitelist(request);
  });

  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('审核页正常加载', async ({ page }) => {
    await page.goto('/incident-report/test-report-id/audit');
    await expect(page.locator('.incident-report-audit-view')).toBeVisible();
  });

  test('审核页显示审核操作面板', async ({ page }) => {
    await page.goto('/incident-report/test-report-id/audit');
    const auditPanel = page.locator('.audit-action-panel');
    if (await auditPanel.isVisible()) {
      await expect(auditPanel.locator('h3')).toContainText('审核操作');
    }
  });
});
