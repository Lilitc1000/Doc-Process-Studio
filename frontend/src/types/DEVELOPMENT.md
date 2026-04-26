# Types 开发指南

跨组件共享 TypeScript 类型定义目录，按业务域组织。

## 目录结构

```text
frontend/src/types/
├── auth/
│   └── auth.ts             # 认证类型（登录、注册、令牌、用户信息）
├── chat/
│   ├── chat.ts             # 消息节点、聊天请求、流式事件
│   └── session.ts          # 历史会话与快照
├── incident-report/
│   └── incident-report.ts  # 事故报告类型
└── common/
    ├── skill.ts            # Skill 选项与 catalog
    └── trace.ts            # 链路回放数据
```

## 设计原则

- 类型定义与业务域一一对应，便于查找和维护
- 跨业务域共享的类型放在 `common/` 目录下
- 前端代码统一使用 **camelCase** 字段名
- 后端接口使用 snake_case，由 `api/request.ts` 中的拦截器自动转换

## 开发注意

- 不要把共享类型重新写回组件内部
- 新增接口时，先在 `src/types/` 补充共享响应类型，再在组件中使用
- 不要在类型层重新引入 camelCase 兼容代码（如 `AliasChoices` 等）
