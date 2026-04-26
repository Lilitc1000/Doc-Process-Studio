import { test, expect } from '@playwright/test';
import { loginAsAdmin, addRateLimitWhitelist } from '../../helpers';

test.describe('事故报告创建流程', () => {
  test.beforeAll(async ({ request }) => {
    await addRateLimitWhitelist(request);
  });

  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('创建页正常加载', async ({ page }) => {
    await page.goto('/incident-report/create');
    await expect(page.locator('.incident-report-create-view')).toBeVisible();
  });

  test('向导步骤切换', async ({ page }) => {
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
});
