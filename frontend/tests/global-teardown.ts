import { request as newRequestContext } from '@playwright/test';

// 本文件只在 Node 环境执行，但测试用 tsconfig 未引入 @types/node，这里做最小声明
declare const process: { env: Record<string, string | undefined> };

import { cleanupWorkerData, getWorkerPrefix } from './helpers';

/**
 * E2E 全局兜底清理。
 *
 * 各 spec 的 afterAll 会清理自己造的数据，但进程被中断、用例超时被强杀时
 * afterAll 不一定执行，数据库里就会留下 e2e_w* 前缀的脏数据。
 * 这里在整轮测试结束后按 worker 前缀再扫一遍，保证「跑完 E2E 不留残留」。
 */
const BASE_URL = process.env.E2E_BASE_URL ?? 'http://localhost:5173';
const MAX_WORKERS = Number(process.env.E2E_MAX_WORKERS ?? 8);

export default async function globalTeardown() {
  const context = await newRequestContext.newContext({ baseURL: BASE_URL });
  try {
    for (let index = 0; index < MAX_WORKERS; index += 1) {
      await cleanupWorkerData(context, getWorkerPrefix(index));
    }
  } catch (error) {
    console.warn('[global-teardown] 清理 E2E 残留数据失败：', error);
  } finally {
    await context.dispose();
  }
}
