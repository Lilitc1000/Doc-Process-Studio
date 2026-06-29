# Composables 开发指南

全局组合式函数目录，存放跨页面复用的业务逻辑。按职责分为 `business/`（业务逻辑）和根目录（通用逻辑）。

## 目录结构

```text
frontend/src/composables/
└── business/
    ├── useCatalogLoader.ts   # 加载模型列表和 skill 列表到 appStore
    ├── useCopyToast.ts       # 复制成功提示控制
    └── useTraceModal.ts      # Trace 回放弹窗控制
```

## 设计原则

- **状态持有 vs 逻辑编排**：Store 负责状态持有和基础操作，Composable 负责业务逻辑编排
- **何时抽取 Composable**：
  - 超过一个组件会用
  - 或者虽然只有一个组件在用，但状态和副作用已经明显让组件变重
- **何时使用 Store**：状态需要跨组件共享或需要持久化时，优先放入 Pinia Store

## 开发注意

- Composable 内部调用 `useXxxStore()` 时，调用方必须已初始化 Pinia
- 单元测试中必须先 `setActivePinia(createPinia())` 再使用 composable
- 不要创建无效的 `createMockStore()` 普通对象——它不会被 Pinia 识别
- 纯格式化、纯映射、纯解析逻辑优先放 `src/utils/`，不要放进 composable
