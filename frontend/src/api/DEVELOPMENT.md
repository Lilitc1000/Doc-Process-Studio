# API 层开发指南

前端 HTTP 请求统一封装层。按业务域组织文件，所有网络请求必须经由此层，禁止在组件中直接调用 `axios` 或 `fetch`。

## 目录结构

```text
frontend/src/api/
├── request.ts          # Axios 实例配置（拦截器、JWT、错误处理）
├── auth.ts             # 认证接口
├── catalog.ts          # 模型列表、skill 列表
├── chat-stream.ts      # 聊天流式请求（原生 fetch + SSE）
├── chat-sessions.ts    # 聊天会话 CRUD
├── chat-attachments.ts # 附件下载
├── incident-report.ts  # 事故报告接口
├── knowledge-base.ts   # 知识库接口（项目/文件夹/文档/树形/更新）
└── trace.ts            # 链路回放接口
```

## request.ts 拦截器说明

### 请求拦截器

- 自动注入 `Authorization: Bearer <access_token>` 请求头
- 将 `config.data` 和 `config.params` 中的 camelCase 字段自动转换为 snake_case（仅对纯对象生效，`URLSearchParams` 会被跳过）

### 响应拦截器

- 将 `response.data` 中的 snake_case 字段自动转换为 camelCase
- 遇到 401 时自动尝试使用 refresh_token 刷新 access_token，成功后重试原请求
- 刷新失败则清除认证状态并跳转到登录页

## chat-stream.ts 特殊说明

聊天流式请求使用原生 `fetch` 而非 Axios，以支持 SSE `ReadableStream`：

- 不经过 `request.ts` 的 Axios 拦截器，需手动处理 JWT 注入
- 返回事件流，由调用方通过回调函数逐事件处理

## 开发注意

- `api/` 只负责请求与响应映射，不负责页面状态管理
- 新增接口时，先在此目录增加请求函数，再在 `src/types/` 补充共享响应类型
- 不要在组件里直接散写 `axios.get(...)` / `fetch(...)`
- 登录接口使用 `URLSearchParams` + `application/x-www-form-urlencoded`，不会被 humps 转换
