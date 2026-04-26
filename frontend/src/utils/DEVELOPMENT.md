# Utils 开发指南

纯工具函数目录，按业务域组织。存放纯格式化、纯映射、纯解析逻辑，无副作用，不依赖 Vue 响应式系统。

## 目录结构

```text
frontend/src/utils/
├── chat/
│   ├── chat-stream.ts      # SSE 缓冲区解析
│   ├── message-tree.ts     # 消息树纯函数
│   └── session-groups.ts   # 会话按日期分组
├── incident-report/
│   ├── date-normalization.ts # 日期/时间归一化
│   └── constants.ts        # 事故报告常量与归一化函数
└── common/
    ├── catalog.ts          # 目录归一化
    ├── avatar-colors.ts    # 头像颜色常量
    ├── file.ts             # 文件大小格式化
    ├── file-type-visuals.ts # 文件类型视觉映射
    ├── ids.ts              # ID 生成
    └── render-markdown.ts  # Markdown 渲染引擎
```

## 设计原则

- **纯函数**：给定相同输入，永远返回相同输出，无副作用
- **不依赖 Vue**：不调用 `ref()`、`computed()` 等 Vue API
- **不调用 API**：不发起 HTTP 请求
- **按业务域组织**：与 `views/`、`types/`、`api/` 保持一致

## 开发注意

- 纯格式化、纯映射、纯解析逻辑优先放 `src/utils/`，不要放进组件或 composable
- 单元测试中直接导入函数，断言输入输出，无需 mock
- 每个测试只测一个行为，边界情况必须覆盖
