# Layouts 开发指南

布局组件目录，控制页面骨架。所有页面通过 `<router-view>` 注入内容。

## 目录结构

```text
frontend/src/layouts/
├── DefaultLayout.vue       # 默认布局：AppHeader + 内容区 + 路由页面切换动画
└── components/
    └── AppHeader.vue       # 全局页头（首页按钮 + 页面标题 + 用户菜单）
```

## DefaultLayout 说明

- 提供全局 `AppHeader`，包含首页按钮、页面标题、用户菜单
- 首页（`/`）不显示 `AppHeader`
- 页面内容通过 `<router-view>` 注入，包裹 `page-switch` 过渡动画
- 支持页面组件通过 `defineExpose` 自定义 header 行为：
  - `onHeaderTitleClick` — 标题点击回调
  - `onGoHome` — 首页按钮回调
  - `isTitleClickable` — 标题是否可点击

## 开发注意

- 布局组件**禁止写业务逻辑**
- 页面组件**不要**再内嵌自己的 `AppHeader`
- 样式内联在 `.vue` 的 `<style scoped>` 中
