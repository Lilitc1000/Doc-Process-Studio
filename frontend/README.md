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
├── router/                     # 路由配置
├── layouts/                    # 布局组件
├── views/                      # 页面级组件（按业务域）
│   ├── auth/
│   ├── home/
│   ├── chat/
│   ├── incident-report/
│   └── settings/
├── components/                 # 全局公共组件
│   ├── base/                   # 原子组件（纯 UI，无业务）
│   └── business/               # 业务组件（跨页面复用）
├── composables/                # 全局组合式函数
├── api/                        # HTTP 请求封装（按业务域）
├── stores/                     # Pinia 全局状态（按业务域）
├── types/                      # 跨组件共享类型
├── utils/                      # 纯工具函数
├── styles/                     # 全局样式
└── assets/                     # 静态资源
```

各目录的详细说明见下方「目录开发文档」。

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

| 层级         | 目录                     | 职责                           | 约束                                 |
| ------------ | ------------------------ | ------------------------------ | ------------------------------------ |
| 布局         | `layouts/`               | 页面骨架                       | 禁止写业务逻辑                       |
| 页面         | `views/`                 | 对应路由，数据获取和页面级状态 | 可组合多个 components                |
| 页面私有组件 | `views/xxx/components/`  | 仅当前页面用                   | 禁止被其他页面导入                   |
| 页面私有逻辑 | `views/xxx/composables/` | 仅当前页面用                   | 禁止被其他页面导入                   |
| 原子组件     | `components/base/`       | 纯 UI，无业务，到处复用        | 禁止依赖 API，props/emit 通信        |
| 业务组件     | `components/business/`   | 跨页面复用，带业务语义         | 可依赖 API 类型，禁止直接调用 API    |
| 全局逻辑     | `composables/`           | 逻辑复用                       | base 级纯逻辑，business 级可调用 API |

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

1. 业务域样式放在 `views/xxx/styles/`，不要在 `styles/` 下新建组件样式文件
2. 公共组件样式优先内联
3. 使用 CSS 变量而非硬编码颜色
4. 不引入第三方 CSS 框架，所有样式手写
5. scoped 样式优先，避免全局污染
6. 基础 UI 元素（按钮、输入框、下拉框等）必须使用 `components/base/` 中的组件

## 开发约定

### 新增接口

1. 先在 `src/api/` 增加请求函数
2. 再在 `src/types/` 补共享响应类型
3. 最后在组件或 composable 中消费

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

现有基础组件不满足需求时，先在 `components/base/` 中扩展，不要在业务组件中直接写原生 HTML 元素。

### 新增工具函数

纯格式化、纯映射、纯解析逻辑，优先放 `src/utils/`，不要放进组件。

## 维护时尽量避免的事

- 不要把 API 请求重新塞回 `.vue`
- 不要把共享类型重新写回组件内部
- 不要把长样式块再塞回 SFC（业务域样式放 `views/xxx/styles/`）
- 不要在消息渲染链路里随意去掉缓存、懒渲染和按需加载
- 不要在类型或 API 层重新引入 camelCase 兼容代码
- 不要把组件局部 UI 状态（如弹窗开关、下拉展开）搬进 Store
- 不要把运行时数据（消息树、流式状态）持久化到 localStorage
- 不要在 `views/xxx/components/` 中的组件被其他页面导入
- 不要在业务组件中直接写原生 `<button>`/`<input>`/`<select>` 再自定义样式

## 目录开发文档

| 目录               | 文档                                                         | 说明                      |
| ------------------ | ------------------------------------------------------------ | ------------------------- |
| `src/api/`         | [api/DEVELOPMENT.md](src/api/DEVELOPMENT.md)                 | HTTP 请求封装、拦截器说明 |
| `src/components/`  | [components/DEVELOPMENT.md](src/components/DEVELOPMENT.md)   | 原子组件与业务组件分层    |
| `src/composables/` | [composables/DEVELOPMENT.md](src/composables/DEVELOPMENT.md) | 全局组合式函数            |
| `src/layouts/`     | [layouts/DEVELOPMENT.md](src/layouts/DEVELOPMENT.md)         | 布局组件                  |
| `src/router/`      | [router/DEVELOPMENT.md](src/router/DEVELOPMENT.md)           | 路由配置与导航守卫        |
| `src/stores/`      | [stores/DEVELOPMENT.md](src/stores/DEVELOPMENT.md)           | Pinia 状态管理            |
| `src/styles/`      | [styles/DEVELOPMENT.md](src/styles/DEVELOPMENT.md)           | 全局样式与过渡动画        |
| `src/types/`       | [types/DEVELOPMENT.md](src/types/DEVELOPMENT.md)             | 共享类型定义              |
| `src/utils/`       | [utils/DEVELOPMENT.md](src/utils/DEVELOPMENT.md)             | 纯工具函数                |

## 业务域开发文档

| 业务域         | 文档路径                                                                             |
| -------------- | ------------------------------------------------------------------------------------ |
| Auth           | [src/views/auth/DEVELOPMENT.md](src/views/auth/DEVELOPMENT.md)                       |
| Chat           | [src/views/chat/DEVELOPMENT.md](src/views/chat/DEVELOPMENT.md)                       |
| IncidentReport | [src/views/incident-report/DEVELOPMENT.md](src/views/incident-report/DEVELOPMENT.md) |
| KnowledgeBase  | [src/views/knowledge-base/DEVELOPMENT.md](src/views/knowledge-base/DEVELOPMENT.md)   |
| Home           | [src/views/home/DEVELOPMENT.md](src/views/home/DEVELOPMENT.md)                       |
| Settings       | [src/views/settings/DEVELOPMENT.md](src/views/settings/DEVELOPMENT.md)               |
