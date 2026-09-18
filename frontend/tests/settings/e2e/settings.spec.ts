import { test, expect } from '@playwright/test';
import {
  addRateLimitWhitelist,
  deleteTestUsersByPrefix,
  getWorkerPrefix,
  loginAs,
  loginAsAdmin,
  loginViaApiAs,
  registerUserViaApi,
} from '../../helpers';

/**
 * 设置页面的端到端测试。
 *
 * 范围刻意划在「界面状态」上：
 *
 * - **不点保存 / 不清除密钥**。这两个动作会改写全系统共享的 RAGFlow 配置，
 *   在真实环境里跑 e2e 不应产生这种副作用；保存与清除的行为由后端的
 *   集成测试（`backend/tests/settings/`）覆盖。
 * - 模型选择会写当前登录用户自己的偏好，属于本功能本身的行为，允许。
 *
 * 稳定性要点：设置是异步从服务端拉的，页面挂载瞬间 `enabledDraft` /
 * `baseUrlDraft` 还是初始值。所以每个用例都先在 `beforeEach` 里等
 * **Base URL 被服务端回填为非空**，再开始断言，避免"点了但被后续加载覆盖"的假失败。
 */

/** Base URL 输入框：用 aria-labelledby 定位，比按次序取第 N 个 input 稳。 */
const BASE_URL_INPUT = 'input[aria-labelledby="settings-base-url-label"]';

test.describe('设置页面', () => {
  test.beforeAll(async ({ request }) => {
    await addRateLimitWhitelist(request);
  });

  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
    await page.goto('/settings');
    // 服务端配置回填成功的信号：Base URL 不再为空
    await expect(page.locator(BASE_URL_INPUT)).not.toHaveValue('', {
      timeout: 15_000,
    });
  });

  test('设置页面渲染个人设置与 RAGFlow 两个分区', async ({ page }) => {
    await expect(page.locator('.app-header-title')).toHaveText('设置');
    const titles = page.locator('.settings-section-title');
    await expect(titles.nth(0)).toHaveText('个人设置');
    await expect(titles.nth(1)).toHaveText('RAGFlow 知识库');
  });

  test('显示生成模型和重排序模型两个下拉框', async ({ page }) => {
    const labels = page.locator('.selector-label');
    await expect(labels.nth(0)).toHaveText('生成模型');
    await expect(labels.nth(1)).toHaveText('重排序模型');
  });

  test('点击生成模型下拉框展开选项列表', async ({ page }) => {
    const dropdown = page.locator('.base-dropdown').first();
    await dropdown.locator('.base-dropdown-trigger').click();
    await expect(page.locator('.base-dropdown-panel')).toBeVisible();
  });

  test('选择生成模型后下拉框显示所选模型', async ({ page }) => {
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

  test('API 密钥默认只显示掩码，且页面上没有明文输入框', async ({ page }) => {
    const mask = page.getByTestId('secret-mask');
    await expect(mask).toBeVisible();
    await expect(mask).toContainText('•');

    // 只读态下不该出现任何可输入的密钥框
    await expect(page.locator('input[type="password"]')).toHaveCount(0);
  });

  test('点「修改」后输入框为空且为密码类型，取消可回到只读态', async ({
    page,
  }) => {
    const maskBefore = await page.getByTestId('secret-mask').textContent();
    expect(maskBefore ?? '').not.toBe('');

    await page.getByRole('button', { name: '修改' }).click();

    const keyInput = page.locator('input[type="password"]');
    await expect(keyInput).toBeVisible();
    // 关键：不回填已保存的值（掩码不是密钥，回填会让人以为可以直接保存）
    await expect(keyInput).toHaveValue('');

    await page.getByRole('button', { name: '取消' }).click();
    await expect(page.getByTestId('secret-mask')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toHaveCount(0);
  });

  test('眼睛图标可切换密钥输入的明文与密文', async ({ page }) => {
    await page.getByRole('button', { name: '修改' }).click();

    const keyInput = page.locator('.secret-editing input').first();
    await keyInput.fill('demo-key-for-visibility-test');
    await expect(keyInput).toHaveAttribute('type', 'password');

    await page.locator('.password-toggle-btn').click();
    await expect(keyInput).toHaveAttribute('type', 'text');
    await expect(keyInput).toHaveValue('demo-key-for-visibility-test');

    await page.locator('.password-toggle-btn').click();
    await expect(keyInput).toHaveAttribute('type', 'password');
  });

  test('Base URL 协议非法时给出行内校验提示并禁用保存', async ({ page }) => {
    const baseUrlInput = page.locator(BASE_URL_INPUT);
    const saveButton = page.getByRole('button', { name: '保存' });

    await baseUrlInput.fill('ftp://wrong-scheme:10108');
    await expect(page.locator('.field-error')).toContainText('http');
    await expect(saveButton).toBeDisabled();

    await baseUrlInput.fill('http://ok-host:10108');
    await expect(page.locator('.field-error')).toHaveCount(0);
    await expect(saveButton).toBeEnabled();
  });

  test('启用开关可点击并翻转 aria-checked', async ({ page }) => {
    const toggle = page.getByRole('switch');
    await expect(toggle).toBeVisible();

    const before = await toggle.getAttribute('aria-checked');
    await toggle.click();
    await expect(toggle).toHaveAttribute(
      'aria-checked',
      before === 'true' ? 'false' : 'true',
    );

    // 再点回来，确认不是单向变化
    await toggle.click();
    await expect(toggle).toHaveAttribute('aria-checked', before ?? 'false');
  });
});

/**
 * 非管理员视角。
 *
 * 补这段的原因：非管理员看到的「RAGFlow 知识库」是一个只读说明块
 * （`.settings-section--muted`），里面只有标题 + 说明文字，没有表单。
 * 而 `.settings-section-desc` 自带下边距（作用是在管理员视角里跟下方表单拉开距离），
 * 一旦它成了区块里的**最后一个元素**，这个下边距就直接变成卡片底部的一块纯空白 ——
 * 叠加区块自身的内边距后，底部留白会变成左右的两倍，看起来像"少画了东西"。
 */
test.describe('设置页面 - 非管理员视角', () => {
  test.beforeAll(async ({ request }) => {
    await addRateLimitWhitelist(request);
  });

  test('只读说明块底部没有多余空白，且不暴露任何可操作控件', async ({
    page,
    request,
  }, testInfo) => {
    // 沿用 e2e_w{workerIndex}_ 前缀：进程被强杀时 globalTeardown 也能兜底清掉。
    // ⚠️ 用户名上限 20 字符（后端 422 会直接拒），所以后缀用 base36 的短时间戳：
    //    "e2e_w0_" 占 7 位 + "sm_" 3 位 + 8 位 ≈ 18 位，留有余量。
    const username = `${getWorkerPrefix(testInfo.workerIndex)}sm_${Date.now().toString(36)}`;
    try {
      await registerUserViaApi(request, username, 'password123');
      await loginAs(page, username, 'password123');

      // 后端按身份分层：普通用户拿到的 ragflow 段应为 null（含 Base URL / 密钥掩码的那段不对他开放）。
      // 注意这不代表检索不可用 —— 普通用户使用 RAGFlow 走的是服务端链路，与本接口无关。
      //
      // 用测试进程直接打接口，而不是监听浏览器响应：页面加载完再回头读
      // `response.json()` 时，Chromium 可能已经回收了响应体
      // （报 `Network.getResponseBody: No resource with given identifier found`）。
      const memberToken = await loginViaApiAs(request, username, 'password123');
      expect(memberToken).not.toBeNull();
      const overview = await (
        await request.get('/api/settings', {
          headers: { Authorization: `Bearer ${memberToken}` },
        })
      ).json();
      expect(overview.ragflow).toBeNull();
      expect(overview.preferences).toBeTruthy();

      await page.goto('/settings');

      const muted = page.locator('.settings-section--muted');
      await expect(muted).toBeVisible();
      await expect(muted.locator('.settings-section-title')).toHaveText(
        'RAGFlow 知识库',
      );

      // 非管理员不应看到系统设置区的任何可操作元素
      await expect(page.locator('.settings-actions')).toHaveCount(0);
      await expect(page.locator('.secret-readonly')).toHaveCount(0);
      await expect(page.locator('.secret-editing')).toHaveCount(0);
      await expect(page.getByTestId('secret-mask')).toHaveCount(0);
      await expect(muted.getByRole('switch')).toHaveCount(0);

      const geom = await muted.evaluate((section) => {
        const desc = section.querySelector('.settings-section-desc');
        if (!desc) return null;
        const sectionRect = section.getBoundingClientRect();
        const descRect = desc.getBoundingClientRect();
        return {
          // 说明文字底部 → 卡片底边 的这段空白
          bottomGap: sectionRect.bottom - descRect.bottom,
          // 卡片左右内边距（作为"正常留白"的基准）
          sidePadding: parseFloat(getComputedStyle(section).paddingLeft),
          descMarginBottom: getComputedStyle(desc).marginBottom,
        };
      });

      expect(geom).not.toBeNull();
      // 用户能看到的那件事：底部留白不应明显大于左右内边距
      expect(geom!.bottomGap).toBeLessThanOrEqual(geom!.sidePadding + 1);
      // 直接原因：说明文字是区块最后一个子元素，它的下边距必须被抵掉
      expect(geom!.descMarginBottom).toBe('0px');
    } finally {
      await deleteTestUsersByPrefix(request, username);
    }
  });
});
