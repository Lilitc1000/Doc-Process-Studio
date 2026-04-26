# Home 页面开发指南

## 目录结构

```text
frontend/src/views/home/
├── HomeView.vue                 # 首页主组件
└── styles/
    └── home-page.css
```

## 功能说明

首页是用户进入应用后的落地页，展示平台标题和三个功能导航卡片：

- **对话** — 导航到 `/chat`
- **事故报告** — 导航到 `/incident-report`
- **设置** — 导航到 `/settings`

## 布局特点

- 首页不显示 `AppHeader`（`showHeader = computed(() => currentPageId.value !== 'home')`）
- 因此首页断言使用 `.home-title`，不要用 `.app-header`
- 需要操作用户菜单的测试，先导航到 `/chat` 等子页面

## 开发注意

- 导航使用 `useRouter().push()` 实现，不依赖父组件 emit
- 每个导航卡片包含 SVG 图标、标题和描述文字
- 样式文件放在 `styles/` 目录下，通过 `<style scoped src="./styles/xxx.css">` 引入
- 不要在业务组件中直接写原生 `<button>`，应使用 `components/base/` 中的 `BaseButton`
