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
│   └── constants.ts        # 事故报告状态与严重级别选项
└── common/
    ├── catalog.ts          # 目录归一化
    ├── avatar-colors.ts    # 头像颜色常量
    ├── file.ts             # 文件大小格式化
    ├── file-type-visuals.ts # 文件类型视觉映射
    ├── ids.ts              # ID 生成
    ├── logger.ts           # 统一日志工具（替代散落的 console.error/warn）
    ├── error.ts            # 错误消息提取
    ├── download.ts         # Blob 下载触发
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

## 日志工具

`common/logger.ts` 提供统一的日志输出接口，替代散落的 `console.error` / `console.warn`：

```ts
import { logger } from '../utils/common/logger';

logger.error('加载模型列表失败', { context: 'useCatalogLoader', error });
logger.warn('请求失败', { context: 'api', status: 404, url: '/api/projects' });
```

- 每条日志自动携带 `timestamp`、`level`
- `context` 字段标识日志来源模块，便于检索
- `error` 字段自动展开 Error 堆栈
- 业务代码中使用 `logger` 替代 `console.error` / `console.warn`
