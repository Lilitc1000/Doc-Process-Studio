# Frontend 开发指南

基于 Vue 3 + Vite + TypeScript + Pinia + Vue Router 的单页应用。

## 启动与校验

```bash
npm install
npm run dev
```

### 测试

```bash
npm run test          # 单元 + 集成测试
npm run test:e2e      # E2E 测试（需要后端运行）
npm run test:e2e:ui   # E2E 测试（带 UI）
```

详细测试开发指南见 [tests/DEVELOPMENT.md](tests/DEVELOPMENT.md)。

### 代码质量检查

```bash
npm run lint          # ESLint 语法与代码规范检查（含自动修复）
npm run build         # 构建检查（含 vue-tsc 类型检查）
npx knip --no-progress  # 未使用代码检测（导出的函数、类型、依赖等）
```

| 检查项 | 工具 | 说明 |
|--------|------|------|
| 语法与规范 | ESLint | 代码风格、未使用变量/参数等 |
| 类型检查 | vue-tsc | TypeScript 类型校验（集成在 `npm run build` 中） |
| 未使用代码 | [knip](https://github.com/webpro-nl/knip) | 导出但未被引用的函数、类型、依赖；配置文件为 `knip.json`，已集成到 pre-commit |

## 目录结构

```text
frontend/src/
├── main.ts                     # 应用入口
├── App.vue                     # 根组件
├── shared/                     # 底层：纯技术/UI基础设施
│   ├── ui/                     # 纯原子组件 (Button, Input)
│   ├── components/             # 跨模块复用业务组件 (UserAvatar, SessionSidebar)
│   ├── composables/            # 全局通用 Hooks (useCopyToast, useCatalogLoader)
│   ├── api/                    # 全局 HTTP 请求封装 (request, catalog, trace)
│   ├── stores/                 # 全局状态 (app store)
│   ├── types/                  # 全局共享类型 (auth, skill, chat, session)
│   ├── utils/                  # 纯工具函数 (ids, error, render-markdown)
│   ├── directives/             # 全局指令 (safe-html)
│   └── views/                  # 全局页面 (NotFoundView)
├── modules/                    # 核心：高内聚业务域
│   ├── auth/                   # 认证域 (store + api + views + types)
│   ├── chat/                   # 聊天域 (store + api + views + utils + types)
│   ├── incident-report/        # 事故报告域 (store + api + views + types)
│   ├── knowledge-base/         # 知识库域 (store + api + views + types)
│   ├── settings/               # 设置域 (views + types)
│   └── home/                   # 首页域 (views)
├── layouts/                    # 布局组件
├── router/                     # 路由配置（引入 modules 的页面）
├── styles/                     # 全局样式
└── assets/                     # 静态资源
```

每个业务模块（`modules/xxx/`）都是自包含的，拥有独立的 api、store、views、types、utils，模块间通过桶文件 `index.ts` 对外暴露公共 API。

### 路径别名

| 别名       | 指向             | 用途                   |
| ---------- | ---------------- | ---------------------- |
| `@shared`  | `src/shared`     | 全局共享基础设施       |
| `@modules` | `src/modules`    | 业务域模块             |

模块内部使用相对路径引用，跨模块引用使用别名或桶文件。

## 命名规范

| 使用场景           | 风格       | 示例                            |
| ------------------ | ---------- | ------------------------------- |
| JS 变量 / 函数     | camelCase  | `incidentReportStore`           |
| Vue 组件定义       | PascalCase | `IncidentReportWorkspace.vue`   |
| 模板中的组件名     | kebab-case | `<incident-report-workspace />` |
| 模板中的 prop 绑定 | kebab-case | `:is-generating="..."`          |
| 自定义事件名       | kebab-case | `@quick-generate-body="..."`    |
| CSS 类名 / ID      | kebab-case | `.incident-report-workspace`    |
| 文件名             | kebab-case | `incident-report-page.css`      |
| API 路径           | kebab-case | `/incident-report/sessions`     |

前端代码统一使用 **camelCase**，后端接口使用 snake_case，由 `api/request.ts` 中的拦截器自动转换。

## 组件分层规则

| 层级         | 目录                              | 职责                           | 约束                                 |
| ------------ | --------------------------------- | ------------------------------ | ------------------------------------ |
| 布局         | `layouts/`                        | 页面骨架                       | 禁止写业务逻辑                       |
| 页面         | `modules/xxx/views/`              | 对应路由，数据获取和页面级状态 | 可组合多个 components                |
| 页面私有组件 | `modules/xxx/views/components/`   | 仅当前模块用                   | 禁止被其他模块导入                   |
| 页面私有逻辑 | `modules/xxx/views/composables/`  | 仅当前模块用                   | 禁止被其他模块导入                   |
| 原子组件     | `shared/ui/`                      | 纯 UI，无业务，到处复用        | 禁止依赖 API，props/emit 通信        |
| 业务组件     | `shared/components/`              | 跨模块复用，带业务语义         | 可依赖 API 类型，禁止直接调用 API    |
| 全局逻辑     | `shared/composables/`             | 逻辑复用                       | 纯逻辑或可调用全局 API               |

## 样式规范

### 样式归属

| 组件类型     | 样式位置                   | 说明                         |
| ------------ | -------------------------- | ---------------------------- |
| 公共基础组件 | 内联 `<style scoped>`      | 组件自包含                   |
| 业务公共组件 | 优先内联；复杂时同目录引入 | 保证可复用                   |
| 布局组件     | 内联 `<style scoped>`      | 同上                         |
| 页面级组件   | `views/xxx/styles/`        | 业务域样式集中管理           |
| 全局样式     | `styles/base.css`          | 仅 CSS 变量、reset、全局字体 |

### 样式约束

1. 业务域样式放在 `modules/xxx/views/styles/`，不要在 `styles/` 下新建组件样式文件
2. 公共组件样式优先内联
3. 使用 CSS 变量而非硬编码颜色
4. 不引入第三方 CSS 框架，所有样式手写
5. scoped 样式优先，避免全局污染
6. 基础 UI 元素（按钮、输入框、下拉框等）必须使用 `shared/ui/` 中的组件

## 开发约定

### 新增接口

1. 在所属业务模块 `modules/xxx/api/` 增加请求函数（全局接口放 `shared/api/`）
2. 在模块 `modules/xxx/types/` 补响应类型（全局类型放 `shared/types/`）
3. 在模块桶文件 `modules/xxx/index.ts` 中导出公共 API
4. 最后在组件或 composable 中消费

不要在组件里直接散写 `axios.get(...)` / `fetch(...)`。

### 新增共享状态逻辑

- 超过一个组件会用，或状态已让组件变重 → 优先抽 composable
- 需要跨组件共享或持久化 → 优先放入 Pinia Store

### 新增 UI 元素

| UI 元素       | 应使用               |
| ------------- | -------------------- |
| 按钮          | `BaseButton`         |
| 输入框        | `BaseInput`          |
| 多行输入      | `BaseTextarea`       |
| 下拉选择      | `BaseDropdown`       |
| 文件上传      | `BaseFileUpload`     |
| 日期/时间选择 | `BaseDateTimePicker` |
| 弹窗/对话框   | `BaseModal`          |

现有基础组件不满足需求时，先在 `shared/ui/` 中扩展，不要在业务组件中直接写原生 HTML 元素。

### 新增工具函数

纯格式化、纯映射、纯解析逻辑，优先放 `shared/utils/`（模块专用放 `modules/xxx/utils/`），不要放进组件。

## 维护时尽量避免的事

- 不要把 API 请求重新塞回 `.vue`
- 不要把共享类型重新写回组件内部
- 不要把长样式块再塞回 SFC（业务域样式放 `modules/xxx/views/styles/`）
- 不要在消息渲染链路里随意去掉缓存、懒渲染和按需加载
- 不要在类型或 API 层重新引入 camelCase 兼容代码
- 不要把组件局部 UI 状态（如弹窗开关、下拉展开）搬进 Store
- 不要把运行时数据（消息树、流式状态）持久化到 localStorage
- 不要在 `modules/xxx/views/components/` 中的组件被其他模块导入
- 不要在业务组件中直接写原生 `<button>`/`<input>`/`<select>` 再自定义样式

## 目录开发文档

| 目录                  | 文档                                                          | 说明                      |
| --------------------- | ------------------------------------------------------------- | ------------------------- |
| `shared/api/`         | [api/DEVELOPMENT.md](src/shared/api/DEVELOPMENT.md)           | HTTP 请求封装、拦截器说明 |
| `shared/ui/`          | [ui/DEVELOPMENT.md](src/shared/ui/DEVELOPMENT.md)             | 原子组件与业务组件分层    |
| `shared/composables/` | [composables/DEVELOPMENT.md](src/shared/composables/DEVELOPMENT.md) | 全局组合式函数       |
| `layouts/`            | [layouts/DEVELOPMENT.md](src/layouts/DEVELOPMENT.md)          | 布局组件                  |
| `router/`             | [router/DEVELOPMENT.md](src/router/DEVELOPMENT.md)            | 路由配置与导航守卫        |
| `shared/stores/`      | [stores/DEVELOPMENT.md](src/shared/stores/DEVELOPMENT.md)     | Pinia 状态管理            |
| `styles/`             | [styles/DEVELOPMENT.md](src/styles/DEVELOPMENT.md)            | 全局样式与过渡动画        |
| `shared/types/`       | [types/DEVELOPMENT.md](src/shared/types/DEVELOPMENT.md)       | 共享类型定义              |
| `shared/utils/`       | [utils/DEVELOPMENT.md](src/shared/utils/DEVELOPMENT.md)       | 纯工具函数                |

## 业务域开发文档

| 业务域         | 文档路径                                                                           |
| -------------- | ---------------------------------------------------------------------------------- |
| Auth           | [auth/DEVELOPMENT.md](src/modules/auth/DEVELOPMENT.md)                             |
| Chat           | [chat/DEVELOPMENT.md](src/modules/chat/DEVELOPMENT.md)                             |
| IncidentReport | [incident-report/DEVELOPMENT.md](src/modules/incident-report/DEVELOPMENT.md)       |
| KnowledgeBase  | [knowledge-base/DEVELOPMENT.md](src/modules/knowledge-base/DEVELOPMENT.md)         |
| Home           | [home/DEVELOPMENT.md](src/modules/home/DEVELOPMENT.md)                             |
| Settings       | [settings/DEVELOPMENT.md](src/modules/settings/DEVELOPMENT.md)                     |
