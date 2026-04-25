import { test, expect } from '@playwright/test';
import { loginAsAdmin, addRateLimitWhitelist } from '../../helpers';

test.describe('设置页面', () => {
  test.beforeAll(async ({ request }) => {
    await addRateLimitWhitelist(request);
  });

  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('设置页面渲染模型配置区域', async ({ page }) => {
    await page.goto('/settings');

    await expect(page.locator('.app-header-title')).toHaveText('设置');
    await expect(page.locator('.settings-section-title')).toHaveText(
      '模型配置',
    );
  });

  test('显示聊天模型和重排序模型两个下拉框', async ({ page }) => {
    await page.goto('/settings');

    const labels = page.locator('.selector-label');
    await expect(labels.nth(0)).toHaveText('聊天模型');
    await expect(labels.nth(1)).toHaveText('重排序模型');
  });

  test('点击聊天模型下拉框展开选项列表', async ({ page }) => {
    await page.goto('/settings');

    const dropdown = page.locator('.base-dropdown').first();
    await dropdown.locator('.base-dropdown-trigger').click();

    await expect(page.locator('.base-dropdown-panel')).toBeVisible();
  });

  test('选择聊天模型后下拉框显示所选模型', async ({ page }) => {
    await page.goto('/settings');

    const dropdown = page.locator('.base-dropdown').first();
    await dropdown.locator('.base-dropdown-trigger').click();

    await expect(page.locator('.base-dropdown-panel')).toBeVisible();

    const firstOption = page.locator('.base-dropdown-option').first();
    const optionLabel = await firstOption.locator('span').first().textContent();
    await firstOption.click();

    await expect(dropdown.locator('.base-dropdown-trigger-text')).toHaveText(
      optionLabel ?? '',
    );
  });
});
