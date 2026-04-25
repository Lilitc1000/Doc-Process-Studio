# Auth 页面开发指南

## 目录结构

frontend/src/views/auth/
├── LoginView.vue # 登录页面
├── RegisterView.vue # 注册页面
└── styles/
├── login-page.css # 登录页样式
└── register-page.css # 注册页样式

frontend/src/components/business/
├── UserAvatar.vue # 用户头像（首字母 + 颜色背景）
├── UserMenuDropdown.vue # 用户菜单下拉（资料、登出）
└── UserProfileModal.vue # 用户资料弹窗（资料编辑 + 修改密码）

frontend/src/stores/auth.ts # 认证状态管理
frontend/src/api/auth.ts # 认证 API 请求
frontend/src/types/auth/auth.ts # 认证类型定义

## API 依赖

| API                    | 方法   | 用途                    |
| ---------------------- | ------ | ----------------------- |
| `/auth/register`       | POST   | 注册新用户              |
| `/auth/login`          | POST   | 登录（form-urlencoded） |
| `/auth/refresh`        | POST   | 刷新令牌                |
| `/auth/me`             | GET    | 获取当前用户信息        |
| `/auth/me`             | PUT    | 更新用户资料            |
| `/auth/password`       | PUT    | 修改密码                |
| `/auth/logout`         | POST   | 登出                    |
| `/auth/users/{userId}` | DELETE | 删除用户账号            |

## 核心交互流程

1. 未认证用户访问受保护路由时，路由守卫重定向到 `/login`
2. 用户在登录页输入用户名密码，调用 `authStore.login()`
3. 登录成功后 access_token 存入内存，refresh_token 持久化到 localStorage
4. 后续 API 请求自动携带 `Authorization: Bearer <access_token>` 请求头
5. access_token 过期（401）时，自动使用 refresh_token 刷新，成功后重试原请求
6. 刷新失败则清除认证状态，跳转到登录页
7. 已认证用户访问 `/login` 或 `/register` 时，路由守卫重定向到首页

## 组件交互约定

- `LoginView.vue` 和 `RegisterView.vue` 是独立页面，不使用 `DefaultLayout`
- 登录/注册页使用 `BaseInput`、`PasswordInput`、`BaseButton` 基础组件
- 登录成功后如有 `redirect` 查询参数，跳转到该地址，否则跳转首页
- 注册成功后跳转到登录页
- `UserMenuDropdown` 挂载在 `AppHeader` 中，点击头像触发
- `UserProfileModal` 包含两个 Tab：资料编辑和修改密码
- 登出按钮在 `UserMenuDropdown` 中，点击后清除认证状态并跳转登录页

## 开发注意

- **登录请求格式**：`loginUser` 使用 `URLSearchParams` + `application/x-www-form-urlencoded`，不是 JSON
- **JWT 自动注入**：`api/request.ts` 的请求拦截器自动注入 `Authorization` 请求头，业务代码无需手动设置
- **401 自动刷新**：响应拦截器检测到 401 时自动刷新令牌并重试，刷新失败则清除认证跳转登录页
- **路由守卫**：`requiresAuth` meta 要求认证，`hideForAuth` meta 对已认证用户隐藏
- **Auth Store 隔离**：单元测试中每个 `beforeEach` 必须调用 `setActivePinia(createPinia())`
- **humps 转换**：`request.ts` 的请求拦截器只对普通对象（`[object Object]`）执行 `decamelizeKeys`，`URLSearchParams` 等非普通对象会被跳过
- **样式文件**：放在 `styles/` 目录下，通过 `<style scoped src="./styles/xxx.css">` 引入
- **不要在业务组件中直接写原生 `<button>`/`<input>`**，应使用 `components/base/` 中的基础组件
- **E2E 测试速率限制**：测试 `beforeAll` 中调用 `POST /api/auth/rate-limit-whitelist` 加入白名单
- **E2E 测试数据标识**：注册用户名使用 `e2e_` 前缀，`afterAll` 中调用 `DELETE /api/auth/users/by-prefix/e2e_` 清理
