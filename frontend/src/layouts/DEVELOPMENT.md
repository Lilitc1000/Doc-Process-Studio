# Layouts 开发指南

布局组件目录，控制页面骨架。所有页面通过 `<router-view>` 注入内容。

## 目录结构

```text
frontend/src/layouts/
├── DefaultLayout.vue       # 默认布局：浮动 AppHeader + 内容区 + 路由页面切换动画
└── components/
    └── AppHeader.vue       # 全局浮动导航栏（首页模式：仅头像 / 子页面模式：首页按钮 + 标题 + 用户菜单）
```

## DefaultLayout 说明

- 提供全局浮动 `AppHeader`，始终渲染（包括首页）
- `AppHeader` 采用 `position: fixed` 浮动布局，不占据文档流空间
- 子页面内容区通过 `padding-top: 3rem` 为浮动导航栏留出空间
- 首页内容区 `padding-top: 0`，因为首页模式下导航栏仅显示右上角头像，不遮挡内容
- 页面内容通过 `<router-view>` 注入，包裹 `page-switch` 过渡动画
- 支持页面组件通过 `defineExpose` 自定义 header 行为：
  - `onHeaderTitleClick` — 标题点击回调
  - `onGoHome` — 首页按钮回调
  - `isTitleClickable` — 标题是否可点击

## AppHeader 说明

AppHeader 有两种显示模式，由 `pageId` prop 控制：

### 首页模式（`pageId === 'home'`）
- CSS 类：`.app-header--home`
- 仅在右上角显示用户头像/登录按钮
- 整体 `pointer-events: none`，仅头像区域可交互
- 不显示首页按钮和页面标题

### 子页面模式（`pageId !== 'home'`）
- CSS 类：`.app-header--sub`
- 浮动圆角胶囊样式，带毛玻璃效果（`backdrop-filter: blur(16px) saturate(180%)`）
- 左侧：首页按钮（房子图标）+ 可点击/不可点击的页面标题
- 右侧：用户头像下拉菜单 / 登录按钮
- 使用原生 `<button>` 元素，不依赖 `BaseButton` 组件

## 开发注意

- 布局组件**禁止写业务逻辑**
- 页面组件**不要**再内嵌自己的 `AppHeader`
- 样式内联在 `.vue` 的 `<style scoped>` 中
- 修改 AppHeader 高度后，需同步更新 `DefaultLayout.vue` 中 `.app-layout-content` 的 `padding-top` 值
