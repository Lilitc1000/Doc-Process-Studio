# Settings 页面开发指南

## 目录结构

```text
frontend/src/modules/settings/
├── index.ts                     # 模块桶文件（store / api / types）
├── api/settings.ts              # 设置相关接口
├── store/user-settings.ts       # 设置 store（**刻意不做 persist**）
├── types/settings.ts            # 类型定义
└── views/
    ├── SettingsView.vue         # 设置页面主组件
    └── styles/settings-page.css
```

## 功能说明

设置页分两层，权限不同：

| 分区               | 谁能看           | 内容                                                             |
| ------------------ | ---------------- | ---------------------------------------------------------------- |
| **个人设置**       | 任何登录用户     | 生成模型、重排序模型 —— 按用户保存在服务端                       |
| **RAGFlow 知识库** | **仅全局管理员** | Base URL、API 密钥（掩码展示）、启用开关、测试连接 —— 全系统共享 |

非管理员看到的是同一分区的说明块（`.settings-section--muted`），而非空白：
让用户知道"这项存在但归管理员管"，比直接隐藏更好排障。

## 权限判定

用 `useAuthStore().isGlobalAdmin`（来自 `GET /api/auth/me` 的 `role` 字段）。

> ⚠️ **不要**用 `useIncidentReportStore().isAdmin`。那个是**事故报告模块级**角色
> （`incident_report_user_roles`），只在该模块内生效。用错会让"给某人分配报告审核人"
> 顺带变成"能改全局密钥"。为降低误用风险，全局那个特意命名为 `isGlobalAdmin`。

## Store 说明

`useUserSettingsStore`（**不持久化**）：

| 字段                             | 说明                                                    |
| -------------------------------- | ------------------------------------------------------- |
| `preferences`                    | 当前用户的偏好（`models.selected` / `models.reranker`） |
| `ragflow`                        | 系统设置视图（含凭据掩码，**无明文**）                  |
| `loading` / `saving` / `testing` | 三种进行中状态                                          |
| `loadError` / `lastTestResult`   | 加载失败提示 / 最近一次连通性自检结果                   |

**为什么不做 `persist`**：

1. 真相源在后端（`user_settings` / `system_*` 表），本地缓存只会制造"改了没生效"的困惑；
2. 即便接口永不返回明文，把凭据相关信息写进 localStorage 也是没必要的暴露面。

模型选择仍然写回 `useAppStore.selectedModel` —— 那是**运行期状态**（聊天、报告生成都要读），
本 store 只负责"从服务端取/存"。对应地，`shared/stores/app.ts` 的 `persist.pick`
已移除这两个字段：继续写 localStorage 会让同一浏览器下多个账号共用一份模型选择，
而且改了服务端也不生效 —— 典型的双真相源。

## 密钥字段的交互状态

后端**永不返回明文**，所以没有"回显已保存密钥"这件事。完整状态如下：

| 状态                         | 表现                                                                                                               |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| 未配置                       | 固定掩码 `••••••••` + 「未配置」灰标                                                                               |
| 已配置                       | `••••••••` + 尾 4 位 + 「已配置」绿标 + 最后更新时间                                                               |
| 编辑中                       | 点「修改」→ 输入框**清空**（不回填掩码）且 `type=password`，右侧 👁 眼睛图标（复用 `shared/ui/PasswordInput.vue`） |
| 点眼睛                       | 切换**当前输入内容**的明文 / 密文                                                                                  |
| 取消                         | 回到只读掩码态                                                                                                     |
| 校验失败                     | Base URL 协议/主机非法 → `.field-error` 行内提示 + 保存按钮禁用                                                    |
| 测试中 / 测试成功 / 测试失败 | 按钮 loading；结果通过 `settings-hint` 展示后端返回的具体原因（401 / DNS / 超时各不相同）                          |
| 保存中                       | 保存按钮文案变「保存中…」并禁用                                                                                    |
| 保存成功                     | 回到只读态显示新掩码 + 「已保存，立即生效。」                                                                      |
| 清除密钥                     | `BaseConfirmDialog` 二次确认后调 DELETE                                                                            |
| 全局兜底生效                 | 黄色提示条「当前未配置系统级密钥，正在使用环境变量中的兜底密钥。」                                                 |

## API 依赖

| API                     | 方法   | 路径                        | 权限     |
| ----------------------- | ------ | --------------------------- | -------- |
| `fetchSettings`         | GET    | `/settings`                 | 登录用户 |
| `updateUserPreferences` | PUT    | `/settings/preferences`     | 登录用户 |
| `updateRagflowSettings` | PUT    | `/settings/ragflow`         | 管理员   |
| `testRagflowConnection` | POST   | `/settings/ragflow/test`    | 管理员   |
| `clearRagflowApiKey`    | DELETE | `/settings/ragflow/api-key` | 管理员   |

后端一律 snake_case，camelCase 只存在于前端（`shared/api/request` 的 humps 拦截器负责转换）。

### `apiKey` 的四态语义（改这部分前务必先读）

| 传值                    | 行为                                           |
| ----------------------- | ---------------------------------------------- |
| 字段不传                | 保持不变                                       |
| `''` 空串               | **保持不变**（防止一个空输入框把线上密钥清掉） |
| 非空字符串              | 覆盖                                           |
| 调 `clearRagflowApiKey` | 清除                                           |

保存时只提交**用户这次真正改动**的字段；若一个字段都没变，前端直接提示
「没有检测到改动。」而不发请求。

## 开发注意

- 使用 `BaseDropdown` / `BaseInput` / `BaseSwitch` / `PasswordInput` 等公共组件，
  不要在业务组件里写原生控件再自定义样式。
- 样式统一放 `views/styles/settings-page.css`，通过 `<style scoped src="./styles/xxx.css">` 引入。
- **e2e 不要点「保存」和「清除密钥」**：这两个动作会改写全系统共享配置，
  在真实环境跑测试不应产生这种副作用。保存 / 清除的行为由后端集成测试覆盖
  （`backend/tests/settings/`）。
- e2e 里凡是断言服务端回填的值，都先在 `beforeEach` 等一个"已加载"信号
  （如 Base URL 非空），否则会读到挂载瞬间的初始值而假失败。
- 不要自己的 AppHeader，`DefaultLayout` 已提供。
