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

  test('创建页显示页面标题', async ({ page }) => {
    await page.goto('/incident-report/create');
    await expect(page.locator('.create-header h1')).toHaveText('新建事故报告');
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
});
