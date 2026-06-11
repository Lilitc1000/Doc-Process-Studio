# 前端测试开发指南

## 目录结构

测试按业务域组织，每个域内再区分测试类型：

```text
frontend/tests/
├── DEVELOPMENT.md              # 本文档
├── setup.ts                    # Vitest 全局 setup（Pinia 初始化）
├── helpers.ts                  # E2E 共享辅助函数
├── helpers/                    # 测试辅助工具
│   └── composable-setup.ts     # composable 测试的 withSetup 工具
├── auth/                       # 认证域
│   ├── unit/
│   │   └── auth-store.test.ts
│   ├── integration/
│   │   ├── user-avatar.test.ts
│   │   └── password-input.test.ts
│   └── e2e/
│       └── auth.spec.ts
├── chat/                       # 对话域
│   ├── unit/
│   │   ├── session-groups.test.ts
│   │   ├── message-tree.test.ts
│   │   ├── chat-stream.test.ts
│   │   ├── chat-store.test.ts          # Chat Store 完整测试
│   │   ├── app-store.test.ts           # App Store 测试
│   │   └── use-trace-modal.test.ts     # 链路回放 composable 测试
│   ├── integration/
│   │   ├── chat-sidebar.test.ts
│   │   ├── chat-trace-flow.test.ts
│   │   └── chat-attachment-flow.test.ts
│   └── e2e/
│       └── chat.spec.ts
├── incident-report/            # 事故报告域
│   ├── unit/
│   │   ├── report-store.test.ts              # Store 权限/角色测试
│   │   ├── use-report-list.test.ts           # 列表 composable 测试
│   │   ├── use-report-detail.test.ts         # 详情 composable 测试
│   │   ├── use-report-wizard.test.ts         # 创建向导 composable 测试
│   │   ├── use-report-edit.test.ts           # 编辑 composable 测试
│   │   ├── incident-report-types.test.ts     # 类型常量测试
│   │   ├── report-status-badge.test.ts       # 状态徽章组件测试
│   │   └── stats-cards.test.ts               # 统计卡片组件测试
│   ├── integration/
│   │   ├── report-list-view.test.ts      # 列表页集成测试
│   │   ├── report-detail-view.test.ts    # 详情页集成测试
│   │   ├── report-workflow.test.ts       # 状态流转集成测试
│   │   ├── use-report-audit.test.ts      # 审核 composable 测试
│   │   └── use-report-analytics.test.ts  # 分析 composable 测试
│   └── e2e/
│       ├── incident-report-list.spec.ts  # 列表页 E2E
│       ├── incident-report-create.spec.ts # 创建页 E2E
│       ├── incident-report-detail.spec.ts # 详情页 E2E
│       ├── incident-report-edit.spec.ts   # 编辑页 E2E
│       ├── incident-report-audit.spec.ts  # 审核页 E2E
│       └── incident-report-analytics.spec.ts # 统计分析页 E2E
├── settings/                   # 设置域
│   └── e2e/
│       └── settings.spec.ts
├── home/                       # 首页域
│   └── e2e/
│       └── home.spec.ts
├── common/                     # 通用工具域
│   └── unit/
│       ├── catalog.test.ts              # 目录归一化
│       ├── avatar-colors.test.ts        # 头像颜色常量
│       ├── cancel.test.ts               # 请求取消判断
│       ├── error.test.ts                # 错误消息提取
│       ├── file.test.ts                 # 文件大小/类型识别
│       ├── ids.test.ts                  # 客户端 ID 生成
│       ├── render-markdown.test.ts      # Markdown 渲染与缓存
│       ├── download.test.ts             # Blob 下载触发
│       ├── use-copy-toast.test.ts       # 复制提示 composable
│       └── use-catalog-loader.test.ts   # 目录加载 composable
├── knowledge-base/             # 知识库域
│   └── unit/
│       ├── knowledge-base-types.test.ts  # 类型定义测试（KBProject/KBFolder/KBDocument/KBTreeNode）
│       └── knowledge-base-store.test.ts  # Store 测试（项目 CRUD/树形加载/更新状态）
└── app/                        # 全局/跨域
    └── e2e/
        └── navigation.spec.ts
```

### 目录组织原则

- **按业务域划分**：与 `src/views/` 的业务域一一对应（auth、chat、incident-report、settings、home）
- **域内按测试类型划分**：`unit/`（单元测试）、`integration/`（集成测试）、`e2e/`（端到端测试）
- **跨域测试**：放在 `app/` 目录下（如全局导航）
- **通用工具**：放在 `common/` 目录下（如目录归一化）
- **共享辅助**：放在 `tests/` 根目录下（如 `helpers.ts`、`setup.ts`）

## 测试分层

| 层级     | 框架                     | 目录                    | 职责                                  | 依赖                         |
| -------- | ------------------------ | ----------------------- | ------------------------------------- | ---------------------------- |
| 单元测试 | Vitest + happy-dom       | `<domain>/unit/`        | 纯函数、utils、Pinia store            | 无外部依赖，API 用 vi.mock   |
| 集成测试 | Vitest + @vue/test-utils | `<domain>/integration/` | 组件渲染、composable 逻辑、跨模块交互 | API 用 vi.mock，组件用 mount |
| E2E 测试 | Playwright               | `<domain>/e2e/`         | 真实浏览器端到端用户场景              | 需要前后端运行               |

## 运行命令

```bash
# 单元 + 集成测试
npm run test

# E2E 测试（需要后端运行）
npm run test:e2e

# E2E 测试（带 UI）
npm run test:e2e:ui

# 只跑某个域的测试
npx vitest run tests/chat/           # chat 域所有单元+集成测试
npx vitest run tests/auth/unit/      # auth 域的单元测试
npx playwright test tests/chat/e2e/  # chat 域的 E2E 测试
```

---

## 单元测试

### 适用场景

- `src/utils/` 下的纯函数（输入 → 输出，无副作用）
- `src/stores/` 下的 Pinia store（状态管理逻辑）
- 不涉及 DOM 渲染的逻辑

### 编写规范

#### 1. 纯函数测试

直接导入函数，断言输入输出：

```typescript
import { describe, expect, it } from 'vitest';
import { parseStreamEvents } from '../../../src/utils/chat/chat-stream';

describe('parseStreamEvents', () => {
  it('解析单个 SSE 事件', () => {
    const buffer = 'data: {"type":"content","data":"hello"}\n\n';
    const result = parseStreamEvents(buffer);
    expect(result.events).toHaveLength(1);
    expect(result.events[0]).toEqual({ type: 'content', data: 'hello' });
  });

  it('处理不完整事件作为剩余缓冲', () => {
    const buffer =
      'data: {"type":"content","data":"hello"}\n\ndata: {"type":"don';
    const result = parseStreamEvents(buffer);
    expect(result.events).toHaveLength(1);
    expect(result.rest).toBe('data: {"type":"don');
  });
});
```

**要点**：

- 每个测试只测一个行为
- 边界情况必须覆盖（空输入、异常输入、边界值）
- 使用辅助工厂函数构建复杂数据结构

#### 2. Pinia Store 测试

每个 `beforeEach` 中必须重新创建 Pinia 实例，mock API 层：

```typescript
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { useAuthStore } from '../../../src/stores/auth';
import * as authApi from '../../../src/api/auth';

vi.mock('../../../src/api/auth', () => ({
  loginUser: vi.fn(),
  registerUser: vi.fn(),
  refreshToken: vi.fn(),
  logoutUser: vi.fn(),
  getCurrentUser: vi.fn(),
  updateProfile: vi.fn(),
  changePassword: vi.fn(),
}));

describe('useAuthStore', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    setActivePinia(createPinia());
  });

  it('login 成功后设置 token 和用户信息', async () => {
    const store = useAuthStore();
    const mockLogin = authApi.loginUser as ReturnType<typeof vi.fn>;
    const mockGetUser = authApi.getCurrentUser as ReturnType<typeof vi.fn>;

    mockLogin.mockResolvedValue({
      accessToken: 'test_access_token',
      refreshToken: 'test_refresh_token',
      tokenType: 'bearer',
    });
    mockGetUser.mockResolvedValue({
      userId: 'usr_test123',
      username: 'testuser',
      avatarColor: '#4f46e5',
      createdAt: '2026-01-01T00:00:00Z',
    });

    await store.login('testuser', 'password123');

    expect(store.isAuthenticated).toBe(true);
    expect(store.accessToken).toBe('test_access_token');
  });
});
```

**要点**：

- `vi.mock()` 放在 `describe` 顶层，对所有测试生效
- `beforeEach` 中必须 `vi.clearAllMocks()` + `localStorage.clear()` + `setActivePinia(createPinia())`
- 通过 `as ReturnType<typeof vi.fn>` 获取 mock 函数的类型安全引用
- 测试成功路径和失败路径

#### 3. 辅助工厂函数

复杂数据结构使用工厂函数构建：

```typescript
function makeNode(
  id: string,
  role: ChatMessageNode['role'],
  content: string,
  parentId: string | null,
  childIds: string[] = [],
): ChatMessageNode {
  return {
    id,
    role,
    content,
    parentId,
    childIds,
    files: [],
    toolStatuses: [],
    timestamp: new Date(),
  };
}
```

---

## 集成测试

### 适用场景

- 组件渲染和交互（props、events、slots）
- Composable 逻辑（需要 Pinia store 或 API mock）
- 跨模块交互（组件 + store + API）

### 编写规范

#### 1. 基础组件测试

使用 `mount` 挂载组件，通过 `props` 传入数据：

```typescript
import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import UserAvatar from '../../../src/components/business/UserAvatar.vue';

describe('UserAvatar', () => {
  it('显示用户名首字母大写', () => {
    const wrapper = mount(UserAvatar, {
      props: { username: 'admin', color: '#4f46e5', size: 'md' },
    });
    expect(wrapper.text()).toBe('A');
  });

  it('应用正确的尺寸类', () => {
    const sm = mount(UserAvatar, {
      props: { username: 'a', color: '#4f46e5', size: 'sm' },
    });
    expect(sm.find('.user-avatar').classes()).toContain('size-sm');
  });
});
```

**要点**：

- 使用 `props` 传递 prop（不用 `attrs` 传递显式声明的 prop）
- 使用 `wrapper.find()` + CSS 选择器定位元素
- 使用 `wrapper.emitted()` 验证事件

#### 2. Composable 测试

需要 Pinia store 的 composable，在 `beforeEach` 中初始化 Pinia 并 mock API：

```typescript
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { useReportList } from '../../../src/views/incident-report/list/composables/useReportList';

vi.mock('../../../src/api/incident-report', () => ({
  fetchIncidentReportList: vi.fn().mockResolvedValue({ total: 0, items: [] }),
  fetchUserIncidentRoles: vi.fn().mockResolvedValue(['reporter']),
}));

describe('useReportList', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setActivePinia(createPinia());
  });

  it('应正确初始化并返回方法', () => {
    const { loadList, loading } = useReportList();
    expect(loadList).toBeTypeOf('function');
    expect(loading.value).toBe(false);
  });
});
```

**要点**：

- composable 内部调用 `useXxxStore()` 时，必须先 `setActivePinia(createPinia())`
- mock 所有 API 调用，避免真实网络请求
- 不要创建无效的 `createMockStore()` 普通对象——它不会被 Pinia 识别

#### 3. 页面级组件测试

挂载完整页面组件，mock 全部 API 依赖：

```typescript
import { flushPromises, mount } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import ChatPage from '../../../src/views/chat/ChatView.vue';

const streamChatReplyMock = vi.hoisted(() => vi.fn());

vi.mock('../../../src/api/chat-stream', () => ({
  streamChatReply: streamChatReplyMock,
}));

// ... mock 其他 API

describe('chat trace flow', () => {
  it('收到 trace 事件后可打开链路回放详情', async () => {
    streamChatReplyMock.mockImplementation(async (_req, _signal, onEvent) => {
      onEvent({ type: 'trace', phase: 'start', traceId: 'trace-abc-123' });
      onEvent({
        model: 'qwen3:8b',
        message: { role: 'assistant', content: '回复' },
        done: false,
      });
      return { finishReason: 'stop' };
    });

    const wrapper = mount(ChatPage, { attachTo: document.body });
    await flushPromises();

    // 触发交互并断言
    const textarea = wrapper.find('.chat-input textarea');
    await textarea.setValue('测试');
    await textarea.trigger('keydown', { key: 'Enter', shiftKey: false });
    await flushPromises();

    const traceButton = wrapper.find(
      '.chat-message.role-assistant button[title="查看链路"]',
    );
    expect(traceButton.exists()).toBe(true);
  });
});
```

**要点**：

- 使用 `vi.hoisted()` 创建可在 `vi.mock()` 工厂函数中引用的 mock
- 使用 `flushPromises()` 等待 Vue 响应式更新和异步操作
- `attachTo: document.body` 用于需要 Teleport 的组件（如 Modal）
- `afterEach` 中清理 `document.body.innerHTML = ''`

---

## E2E 测试

### 适用场景

- 用户核心流程（注册、登录、导航、创建内容）
- 跨页面交互（首页 → 子页面 → 返回）
- 需要真实后端支持的场景（AI 生成、数据持久化）

### 前置条件

E2E 测试需要后端运行：

```bash
cd backend && env ENV=dev uv run uvicorn doc_process_studio.main:app --host 0.0.0.0 --port 8000
```

Playwright 配置会自动启动 Vite 开发服务器。

### 编写规范

#### 1. 共享辅助函数

所有 E2E 测试共享 `tests/helpers.ts` 中的辅助函数：

```typescript
import {
  getWorkerPrefix,
  loginAsAdmin,
  loginViaApi,
  addRateLimitWhitelist,
  cleanupWorkerData,
} from '../../helpers';
```

| 函数                                                  | 用途                                           |
| ----------------------------------------------------- | ---------------------------------------------- |
| `getWorkerPrefix(workerIndex)`                        | 生成 Worker 隔离的测试数据前缀 `'e2e_w{n}_'`   |
| `loginAsAdmin(page)`                                  | 通过 UI 登录 admin 用户                        |
| `loginViaApi(request)`                                | 通过 API 登录获取 access_token（用于数据清理） |
| `loginViaApiAs(request, user, pw)`                    | 通过 API 以指定用户登录获取 token              |
| `addRateLimitWhitelist(request)`                      | 将测试 IP 加入速率限制白名单                   |
| `cleanupWorkerData(request, prefix)`                  | 清理指定前缀的测试报告和用户                   |
| `createIncidentReportViaApi(request, token, payload)` | 通过 API 创建测试报告                          |
| `deleteIncidentReportViaApi(request, token, id)`      | 通过 API 删除测试报告                          |

#### 2. 测试结构模板

```typescript
import { test, expect } from '@playwright/test';
import {
  getWorkerPrefix,
  loginAsAdmin,
  addRateLimitWhitelist,
  cleanupWorkerData,
} from '../../helpers';

test.describe('功能名称', () => {
  let workerPrefix: string;

  test.beforeAll(async ({ request }, testInfo) => {
    workerPrefix = getWorkerPrefix(testInfo.workerIndex);
    await addRateLimitWhitelist(request);
  });

  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('测试描述', async ({ page }) => {
    await page.goto('/target-page');
    await expect(page.locator('.some-element')).toBeVisible();
  });

  test.afterAll(async ({ request }) => {
    await cleanupWorkerData(request, workerPrefix);
  });
});
```

**要点**：

- `beforeAll` 中必须调用 `addRateLimitWhitelist(request)` 避免并行测试触发速率限制
- `beforeAll` 中使用 `getWorkerPrefix(testInfo.workerIndex)` 生成 Worker 隔离前缀
- `beforeEach` 中登录，确保每个测试从已认证状态开始
- `afterAll` 中使用 `cleanupWorkerData` 清理该 Worker 创建的所有测试数据
- **所有测试数据（标题、用户名等）必须以 `workerPrefix` 为前缀**，确保并行 Worker 之间数据隔离

#### 3. 元素定位策略

优先使用 CSS 类选择器：

```typescript
page.locator('.app-header-title');
page.locator('.chat-sidebar .history-session');
page.locator('.home-card-label', { hasText: '对话' });
page.locator('button', { hasText: /开始/ });
page.locator('input').nth(0);
page.locator('button[type="submit"]');
```

#### 4. 等待策略

```typescript
// 等待导航完成
await expect(page).toHaveURL('/chat');

// 等待 API 响应后再操作
const sessionsResp = page.waitForResponse(
  (resp) => resp.url().includes('/chat-sessions') && resp.status() === 200,
  { timeout: 10_000 },
);
await page.goto('/chat');
await sessionsResp;

// 等待元素可见
await expect(page.locator('.some-element')).toBeVisible({ timeout: 5_000 });
```

#### 5. 依赖外部服务的测试

对依赖 Ollama 的 AI 生成测试，使用 `test.skip()` 优雅降级，并在 `beforeAll` 中检测可用性：

```typescript
let ollamaAvailable = false;
let availableModel = '';

test.beforeAll(async ({ request }, testInfo) => {
  workerPrefix = getWorkerPrefix(testInfo.workerIndex);
  await addRateLimitWhitelist(request);
  try {
    const accessToken = await loginViaApi(request);
    if (accessToken) {
      const resp = await request.get('/api/models', {
        headers: { Authorization: `Bearer ${accessToken}` },
        timeout: 10_000,
      });
      if (resp.ok()) {
        const data = await resp.json();
        const models: { name: string }[] = data.models ?? [];
        const chosen = pickE2EModel(models);
        if (chosen) {
          ollamaAvailable = true;
          availableModel = chosen;
        }
      }
    }
  } catch {
    ollamaAvailable = false;
  }
});

test('AI 生成测试', async ({ page }) => {
  if (!ollamaAvailable) {
    test.skip();
    return;
  }
  // ... 测试逻辑
});
```

**要点**：

- 在 `beforeAll` 中检测 Ollama 可用性，避免每个测试重复检测
- 使用 `pickE2EModel` / `getE2EModel` 智能选择适合 E2E 测试的模型，优先选择小参数通用模型（如 `qwen3:8b`），避免选择编码模型和超大模型导致超时
- 通过 `page.evaluate` 设置 localStorage 中的模型选择，确保前端使用正确的模型
- 真实 AI 测试使用 `test.skip(({ browserName }) => browserName !== 'chromium')` 限制只在 Chromium 运行
- 设置合理的超时时间（`test.setTimeout(300_000)`），AI 生成可能需要较长时间

#### 6. 测试数据清理

| 数据类型 | 标识方式                  | 清理方式                                                          |
| -------- | ------------------------- | ----------------------------------------------------------------- |
| 注册用户 | 用户名 `e2e_w{n}_` 前缀   | `cleanupWorkerData` → `DELETE /api/auth/users/by-prefix/{prefix}` |
| 测试报告 | 标题 `e2e_w{n}_` 前缀     | `cleanupWorkerData` → `deleteReportsByPrefix`                     |
| 聊天会话 | 消息内容 `e2e_w{n}_` 前缀 | `DELETE /api/chat-sessions/by-title-prefix/{prefix}`              |

清理在 `afterAll` 中通过 `cleanupWorkerData(request, workerPrefix)` 统一处理，无需手动逐个删除。

**数据清理最佳实践**：

1. **每个 `describe` 块必须有 `afterAll` 清理**：即使测试中使用了 `try/finally` 逐个清理，`afterAll` 仍需调用 `cleanupWorkerData` 作为兜底
2. **使用 `try/finally` 清理单条数据**：在测试中创建的单条数据，使用 `try/finally` + `deleteIncidentReportViaApi` 立即清理，避免数据残留
3. **`cleanupWorkerData` 作为兜底**：即使单条清理失败，`afterAll` 中的 `cleanupWorkerData` 也会按前缀批量清理
4. **不要使用 `test.describe.configure({ mode: 'serial' })`**：Worker 隔离已解决并发问题，无需串行执行
5. **前端表单输入的数据也必须使用 `workerPrefix` 前缀**：即使只通过 UI 填写未调用 API，表单提交后仍会持久化到数据库。例如 `await titleInput.fill(`${workerPrefix}测试报告`)`，确保 `cleanupWorkerData` 能正确清理

#### 7. Worker 隔离机制

Playwright 默认并行运行测试，多个 Worker 可能同时创建和操作数据。为确保数据隔离：

```typescript
test.describe('功能名称', () => {
  let workerPrefix: string;

  test.beforeAll(async ({ request }, testInfo) => {
    // 每个 Worker 获得独立前缀，如 e2e_w0_、e2e_w1_、e2e_w2_
    workerPrefix = getWorkerPrefix(testInfo.workerIndex);
    await addRateLimitWhitelist(request);
  });

  test('创建测试数据', async ({ request }) => {
    const token = await loginViaApi(request);
    // 所有测试数据使用 workerPrefix 前缀
    const report = await createIncidentReportViaApi(request, token!, {
      title: `${workerPrefix}测试报告`,
    });
    // ...
  });

  test.afterAll(async ({ request }) => {
    // 只清理本 Worker 创建的数据
    await cleanupWorkerData(request, workerPrefix);
  });
});
```

**隔离原则**：

- **前缀隔离**：每个 Worker 的数据使用 `e2e_w{n}_` 前缀，不同 Worker 的数据互不干扰
- **清理隔离**：`afterAll` 只清理本 Worker 前缀的数据，不会误删其他 Worker 的数据
- **RBAC 测试中的用户隔离**：注册的测试用户也使用 `workerPrefix` 前缀（如 `e2e_w0_reporter`），避免用户名冲突

#### 8. 首页特殊注意

首页显示 `AppHeader` 的首页模式（`.app-header--home`），仅在右上角显示用户头像：

- 首页断言使用 `.home-title`，头像断言使用 `.app-header--home .user-avatar`
- 首页模式下不显示首页按钮和页面标题
- 需要操作完整用户菜单的测试，先导航到 `/chat` 等子页面

---

## 新增测试检查清单

### 新增测试文件

- [ ] 文件放在 `tests/<domain>/<type>/` 目录（域与 `src/views/` 对应）
- [ ] 单元测试文件名与源文件对应（如 `auth-store.test.ts` 对应 `auth.ts`）
- [ ] E2E 测试文件名以 `.spec.ts` 结尾
- [ ] 导入路径使用 `../../../src/...`（从 `<domain>/<type>/` 到 `src/`）
- [ ] E2E 辅助函数从 `../../helpers` 导入

### 单元测试

- [ ] 纯函数测试覆盖边界情况
- [ ] Store 测试在 `beforeEach` 中初始化 Pinia
- [ ] API 调用使用 `vi.mock()` mock

### 集成测试

- [ ] 组件测试使用 `props` 传递 prop（不用 `attrs`）
- [ ] Composable 测试初始化 Pinia 并 mock API
- [ ] 页面级测试 mock 全部 API 依赖
- [ ] 使用 `flushPromises()` 等待异步更新

### E2E 测试

- [ ] 使用 `helpers.ts` 中的共享辅助函数
- [ ] `beforeAll` 中调用 `addRateLimitWhitelist`
- [ ] `beforeAll` 中使用 `getWorkerPrefix(testInfo.workerIndex)` 生成 Worker 隔离前缀
- [ ] 测试数据使用 `workerPrefix` 前缀（不是固定的 `e2e_`）
- [ ] `afterAll` 中使用 `cleanupWorkerData(request, workerPrefix)` 清理数据
- [ ] 依赖外部服务的测试使用 `test.skip()` 优雅降级
- [ ] 不要使用 `test.describe.configure({ mode: 'serial' })`，Worker 隔离已解决并发问题
- [ ] 创建单条数据时使用 `try/finally` 立即清理，`afterAll` 作为兜底

---

## E2E 测试覆盖率评估方案

E2E 测试运行在真实浏览器中，无法像单元测试那样通过代码插桩追踪源码行覆盖率。因此采用 **功能覆盖率 + 用户旅程覆盖率** 两个维度评估 E2E 测试充分性。

### 功能覆盖率矩阵

功能覆盖率 = 已测试功能点 / 总功能点。按业务域和页面维度统计：

| 业务域       | 页面/路由                    | 功能点                                             | 测试文件                          | 覆盖状态  |
| ------------ | ---------------------------- | -------------------------------------------------- | --------------------------------- | --------- |
| **认证**     | `/login`                     | 登录成功/失败/重定向                               | auth.spec.ts                      | ✅ 已覆盖 |
|              | `/register`                  | 注册成功/重复用户名/页面渲染                       | auth.spec.ts                      | ✅ 已覆盖 |
|              | 全局                         | 登出/用户信息弹窗/已认证重定向                     | auth.spec.ts                      | ✅ 已覆盖 |
|              | 全局                         | 未认证访问受保护路由重定向                         | auth.spec.ts                      | ✅ 已覆盖 |
| **首页**     | `/`                          | 标题/卡片渲染/导航跳转                             | home.spec.ts                      | ✅ 已覆盖 |
| **对话**     | `/chat`                      | UI渲染/消息发送/AI回复/会话管理                    | chat.spec.ts                      | ✅ 已覆盖 |
| **事故报告** | `/incident-report`           | 列表加载/统计卡片/筛选器/新建跳转/表格/导航        | incident-report-list.spec.ts      | ✅ 已覆盖 |
|              | `/incident-report/create`    | 页面加载/步骤切换/填写标题/步骤指示器/返回导航     | incident-report-create.spec.ts    | ✅ 已覆盖 |
|              | `/incident-report/analytics` | 页面加载/标题返回/统计卡片/返回导航                | incident-report-analytics.spec.ts | ✅ 已覆盖 |
|              | `/incident-report/:id`       | 不存在报告/基本信息/状态徽章/评论/从列表导航       | incident-report-detail.spec.ts    | ✅ 已覆盖 |
|              | `/incident-report/:id/edit`  | 不存在报告/表单渲染/级别下拉框/保存取消/从详情导航 | incident-report-edit.spec.ts      | ✅ 已覆盖 |
|              | `/incident-report/:id/audit` | 审核面板/返回详情/从详情导航                       | incident-report-audit.spec.ts     | ✅ 已覆盖 |
| **设置**     | `/settings`                  | 模型配置/下拉框交互                                | settings.spec.ts                  | ✅ 已覆盖 |
| **全局导航** | 跨页面                       | header首页按钮/往返导航/浏览器前进后退             | navigation.spec.ts                | ✅ 已覆盖 |

### 用户旅程覆盖率

用户旅程覆盖率 = 已覆盖核心用户路径 / 总核心用户路径。

| 旅程编号 | 用户旅程                                      | 覆盖状态 | 测试文件                          |
| -------- | --------------------------------------------- | -------- | --------------------------------- |
| J1       | 未登录 → 登录 → 首页                          | ✅       | auth.spec.ts                      |
| J2       | 未登录 → 注册 → 登录                          | ✅       | auth.spec.ts                      |
| J3       | 登录 → 首页 → 对话 → 发消息 → AI回复          | ✅       | chat.spec.ts                      |
| J4       | 登录 → 首页 → 事故报告列表 → 新建 → 创建页    | ✅       | incident-report-list.spec.ts      |
| J5       | 登录 → 事故报告列表 → 点击报告 → 详情页       | ✅       | incident-report-detail.spec.ts    |
| J6       | 登录 → 详情页 → 编辑页 → 保存                 | ✅       | incident-report-edit.spec.ts      |
| J7       | 登录 → 详情页 → 审核页 → 审核操作             | ✅       | incident-report-audit.spec.ts     |
| J8       | 登录 → 事故报告列表 → 统计分析                | ✅       | incident-report-analytics.spec.ts |
| J9       | 登录 → 设置 → 修改模型                        | ✅       | settings.spec.ts                  |
| J10      | 登录 → 任意页面 → 登出 → 重定向登录页         | ✅       | auth.spec.ts                      |
| J11      | 登录 → 首页 → 子页面 → 返回首页（header按钮） | ✅       | navigation.spec.ts                |
| J12      | 登录 → 浏览器前进/后退导航                    | ✅       | navigation.spec.ts                |

### 覆盖率计算

- **路由覆盖率** = 有 E2E 测试的路由数 / 总路由数 = 11/11 = **100%**
- **功能覆盖率** = 已测试功能点 / 总功能点 = **100%**（每个页面的所有可见功能点均有测试覆盖，包括：页面加载、标题、导航按钮、表单交互、筛选器、表格、统计卡片、步骤指示器、评论区域、审核时间线、状态徽章、加载/空状态等）
- **用户旅程覆盖率** = 已覆盖核心旅程 / 总核心旅程 = 12/12 = **100%**

### 新增 E2E 测试检查清单

- [ ] 新页面路由必须在功能覆盖率矩阵中登记
- [ ] 新用户旅程必须在旅程覆盖率表中登记
- [ ] 每个路由至少有"页面正常加载"测试
- [ ] 涉及动态 ID 的页面（如 `/incident-report/:id`）应从列表页导航进入，不使用硬编码 ID
- [ ] 依赖后端数据的测试使用 `if (await element.isVisible())` 优雅降级
- [ ] 依赖 Ollama 的测试必须在 `beforeAll` 中通过后端 API (`/api/models`) 检测 Ollama 可用性，不可用时 `test.skip()`
- [ ] 不要直接检测 `localhost:11434`（Ollama 可能部署在远程服务器），应通过后端 API 间接检测
- [ ] 所有测试数据使用 `workerPrefix` 前缀，确保 Worker 隔离
- [ ] `afterAll` 中使用 `cleanupWorkerData(request, workerPrefix)` 清理数据

### E2E 测试运行命令

```bash
# 运行所有 E2E 测试（需要前后端服务器同时运行）
npm run test:e2e

# 或使用 npx
npx playwright test

# 运行单个测试文件
npx playwright test tests/chat/e2e/chat.spec.ts

# 运行匹配名称的测试
npx playwright test -g "AI 回复"

# 查看测试报告
npx playwright show-report
```

### 依赖 Ollama 的测试编写规范

部分端到端测试（如聊天 AI 回复、事故报告快填生成）依赖 Ollama 服务。编写此类测试时：

1. **在 `beforeAll` 中检测可用性**：通过后端 `/api/models` API 检测，不要直接访问 Ollama 端口
2. **不可用时优雅跳过**：使用 `test.skip()` 而非 `test.fail()`
3. **设置足够超时**：LLM 响应可能较慢，`test.setTimeout(300_000)` 和 `waitForResponse({ timeout: 180_000 })`
4. **动态获取可用模型**：通过 `/api/models` API 获取远程服务器上实际可用的模型名称，不要硬编码模型名
5. **设置 localStorage 模型选择**：通过 `page.evaluate` 设置 `localStorage` 中的 `selectedModel`，确保前端使用正确的模型
6. **清理测试数据**：`afterAll` 中使用 `cleanupWorkerData(request, workerPrefix)` 清理数据
7. **Mock 测试与真实测试分离**：Mock API 的测试和真实调用 Ollama 的测试放在不同的 `describe` 块中
8. **API 错误时优雅跳过**：Ollama 生成请求返回 4xx/5xx 错误或超时时，使用 `test.skip()` 跳过而非 `throw`，避免因 Ollama 服务器不稳定导致 CI 失败

### 后端事务与数据一致性规范

E2E 测试涉及的后端数据操作需要遵循以下规范：

1. **报告创建与审计日志必须在同一事务中**：`create_report` 函数将 `IncidentReportORM` 和 `IncidentAuditLog` 放在同一个事务中，先 `flush()` 报告记录确保 INSERT 执行，再添加审计日志并 `commit()`
2. **唯一约束冲突需要重试**：`ref_no` 等唯一字段在并发场景下可能冲突，需要 `IntegrityError` 捕获并重试，重试时使用随机值
3. **级联删除在同一个事务中**：删除报告时，先删除评论和审计日志，再删除报告，全部在同一个事务中
4. **前端键名转换**：后端返回的 snake_case 键名会被 HTTP 拦截器转换为 camelCase。但流式接口（如聊天）使用原生 fetch，不经过拦截器，需要在前端手动使用 `humps.decamelize()` 转换
