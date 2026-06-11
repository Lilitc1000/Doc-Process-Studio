# Styles 开发指南

全局样式目录，仅存放 CSS 变量、reset、全局字体和共享过渡动画。业务域样式放在对应 `views/xxx/styles/` 目录下。

## 目录结构

```text
frontend/src/styles/
├── base.css          # 全局 CSS 变量、reset、全局字体
└── transitions.css   # 全局过渡动画（fade / fade-slide-up / page-switch / session-switch）
```

各业务域样式目录：

| 业务域   | 样式目录                        |
| -------- | ------------------------------- |
| 对话     | `views/chat/styles/`            |
| 事故报告 | `views/incident-report/styles/` |
| 知识库   | `views/knowledge-base/styles/`  |

## base.css

定义全局设计 Token，所有组件统一使用：

| 变量                      | 用途     | 示例值    |
| ------------------------- | -------- | --------- |
| `--color-primary`         | 主色     | `#2563eb` |
| `--color-primary-hover`   | 主色悬停 | `#1d4ed8` |
| `--color-primary-light`   | 主色浅底 | `#eff6ff` |
| `--color-primary-lighter` | 主色更浅 | `#dbeafe` |
| `--color-text-primary`    | 主文本   | `#0f172a` |
| `--color-text-secondary`  | 辅助文本 | `#475569` |
| `--color-text-tertiary`   | 占位文本 | `#94a3b8` |
| `--color-border`          | 边框     | `#e2e8f0` |
| `--color-border-hover`    | 边框悬停 | `#cbd5e1` |
| `--color-border-focus`    | 边框聚焦 | `#93c5fd` |
| `--color-bg-primary`      | 主背景   | `#ffffff` |
| `--color-bg-secondary`    | 次背景   | `#f8fafc` |
| `--color-bg-tertiary`     | 三级背景 | `#f1f5f9` |
| `--color-bg-hover`        | 背景悬停 | `#f1f5f9` |
| `--color-bg-page`         | 页面背景 | `#f5f7fa` |
| `--color-success`         | 成功色   | `#16a34a` |
| `--color-warning`         | 警告色   | `#d97706` |
| `--color-danger`          | 危险色   | `#dc2626` |

### 间距变量

所有 `gap`、`padding`、`margin` 必须使用间距变量，禁止硬编码 rem/px 值：

| 变量          | 值        | 用途                           |
| ------------- | --------- | ------------------------------ |
| `--space-2xs` | 0.125rem  | 微间距（图标与文字间隙）       |
| `--space-xs`  | 0.25rem   | 最小间距（紧凑元素间隙）       |
| `--space-sm`  | 0.5rem    | 小间距（按钮组、标签间距）     |
| `--space-md`  | 0.75rem   | 中间距（表单字段、列表项）     |
| `--space-lg`  | 1rem      | 标准间距（卡片内边距、组件间） |
| `--space-xl`  | 1.5rem    | 大间距（区块间、页面内边距）   |
| `--space-2xl` | 2rem      | 超大间距（页面级内边距）       |
| `--space-3xl` | 3rem      | 页面级间距（主内容区间）       |
| `--space-4xl` | 4rem      | 最大间距（页面顶部留白）       |

### 间距使用规则

1. **组件内部间距**（卡片 padding、字段 gap）：优先使用 `--space-md` 或 `--space-lg`
2. **组件之间间距**（卡片之间、区块之间）：使用 `--space-lg` 或 `--space-xl`
3. **页面级间距**（页面内边距、主区块之间）：使用 `--space-xl` 或 `--space-2xl`
4. **紧凑排列**（标签组、按钮组）：使用 `--space-sm` 或 `--space-xs`
5. **禁止**使用不在上述变量中的间距值（如 `0.35rem`、`0.6rem`、`0.84rem` 等）

## transitions.css

所有页面共享的过渡动画：

| 动画名           | 用途                          |
| ---------------- | ----------------------------- |
| `fade`           | 纯淡入淡出（轻提示、遮罩）    |
| `fade-slide-up`  | 淡入 + 上滑（弹窗、下拉菜单） |
| `page-switch`    | 页面路由切换                  |
| `session-switch` | 同页内会话/内容切换           |

## 开发注意

- **不要在 `styles/` 下新建组件样式文件**，业务域样式放在 `views/xxx/styles/`
- 新增页面如需使用过渡动画，优先从上述全局动画中选择
- 只有当现有动画无法满足需求时，才在 `transitions.css` 中扩展新动画
- **禁止**在业务样式文件中重复定义相同的动画类
- 使用 CSS 变量而非硬编码颜色，保持风格统一
- 使用间距变量（`--space-*`）而非硬编码 rem/px 值，保持间距一致
- 不引入第三方 CSS 框架，所有样式手写

## 商用级设计规范

### 排版

1. **字间距调整**：大标题（`--text-2xl` 及以上）使用负字间距（`-0.02em` 至 `-0.01em`）；标签、辅助文本使用正字间距（`0.02em` 至 `0.04em`）
2. **正文行宽**：段落最大宽度限制在 `65ch` 左右，行高使用 `--leading-relaxed`（1.65）以提高可读性
3. **表格数字**：数据密集组件（表格、统计卡片、仪表盘）默认启用 `font-variant-numeric: tabular-nums`，确保数字列对齐
4. **防孤立词**：卡片标题、短标题使用 `text-wrap: balance`；段落正文使用 `text-wrap: pretty`，避免末行孤立词

### 视口与布局

5. **视口单位**：全屏布局使用 `min-height: 100dvh` 而非 `height: 100vh`，防止移动端浏览器地址栏导致的布局跳动
6. **圆角层级**：内部元素（标签、徽章）使用 `--radius-sm`；卡片、面板使用 `--radius-lg`；弹窗、对话框使用 `--radius-xl`；圆形/药丸形使用 `--radius-full`
7. **容器约束**：所有页面内容必须使用 `max-width` 容器（`--container-sm/md/lg/xl`）+ `margin: 0 auto`，防止宽屏下内容铺满

### 交互与状态

8. **悬停反馈**：所有可交互元素必须有 hover 状态变化（背景色偏移、边框色变化或轻微位移）
9. **按压反馈**：按钮 active 状态使用 `transform: scale(0.97)` 模拟物理按压感
10. **过渡时长**：所有交互元素添加 `transition`（200-300ms），禁止零时长即时切换
11. **焦点环**：所有可交互元素必须支持 `:focus-visible` 焦点指示器，这是无障碍要求
12. **加载状态**：优先使用骨架屏而非通用圆形加载指示器
13. **空状态**：空列表/空数据必须展示引导性内容（图标+说明+操作按钮），不允许空白
14. **错误状态**：表单使用内联错误消息，禁止使用 `window.alert()`

### 颜色与阴影

15. **阴影色调**：阴影颜色匹配背景色调。主色相关的组件（主按钮、选中态）使用蓝色调阴影；中性组件使用 Slate 色调阴影
16. **灰色一致性**：全项目统一使用冷灰色（Slate 色系），禁止混用暖灰色
17. **禁止纯黑**：文本色使用 `--color-text-primary`（`#0f172a`），禁止使用 `#000000`

### 语义化 HTML

18. **语义标签**：使用 `<nav>`、`<main>`、`<section>`、`<article>`、`<aside>`、`<header>`、`<footer>` 替代无语义的 `<div>`
19. **图片 alt**：所有有意义图片必须提供描述性 `alt` 文本；装饰性图片使用 `alt=""`
20. **标题层级**：每个页面仅一个 `<h1>`，后续标题按 `<h2>` → `<h3>` 顺序递减，禁止跳级
