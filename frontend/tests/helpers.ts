import { expect } from '@playwright/test';
import type { Page, APIRequestContext } from '@playwright/test';

export const E2E_PREFIX = 'e2e_';

export async function loginAsAdmin(page: Page) {
  await page.goto('/login');
  await page.locator('input').nth(0).fill('admin');
  await page.locator('input').nth(1).fill('admin123');
  await page.locator('button[type="submit"]').click();
  await expect(page).toHaveURL('/', { timeout: 10_000 });
}

export async function loginViaApi(request: APIRequestContext) {
  const resp = await request.post('/api/auth/login', {
    form: { username: 'admin', password: 'admin123' },
  });
  if (!resp.ok()) return null;
  const data = await resp.json();
  return data.access_token as string;
}

export async function addRateLimitWhitelist(request: APIRequestContext) {
  await request.post('/api/auth/rate-limit-whitelist');
}
