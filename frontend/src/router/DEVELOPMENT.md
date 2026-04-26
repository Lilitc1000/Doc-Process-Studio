# Router 开发指南

前端路由配置，使用 Vue Router 4 管理页面导航和认证守卫。

## 目录结构

```text
frontend/src/router/
└── index.ts                # 路由定义 + 导航守卫
```

## 路由表

| 路由路径           | 组件                     | 说明         | 需要认证 |
| ------------------ | ------------------------ | ------------ | -------- |
| `/login`           | `LoginView.vue`          | 登录页面     | 否       |
| `/register`        | `RegisterView.vue`       | 注册页面     | 否       |
| `/`                | `HomeView.vue`           | 主页         | 是       |
| `/chat`            | `ChatView.vue`           | 对话页面     | 是       |
| `/incident-report` | `IncidentReportView.vue` | 事故报告页面 | 是       |
| `/settings`        | `SettingsView.vue`       | 设置页面     | 是       |

所有受保护路由共用 `DefaultLayout` 布局。

## 导航守卫逻辑

1. 若未认证但存在 refresh_token，自动尝试刷新 access_token
2. 若已认证但缺少用户信息，自动获取用户资料
3. `requiresAuth` 路由未认证时重定向到登录页（带 `redirect` 查询参数）
4. `hideForAuth` 路由对已认证用户重定向到首页

## 开发注意

- 新增页面路由在此文件中注册
- 通过 `meta` 标记认证需求，不要硬编码守卫逻辑
- 懒加载页面组件：`() => import('../views/xxx/XxxView.vue')`
