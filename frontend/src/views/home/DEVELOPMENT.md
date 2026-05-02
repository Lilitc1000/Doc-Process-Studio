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

- 首页显示 `AppHeader` 的首页模式（`.app-header--home`），仅在右上角显示用户头像
- 首页内容区无 `padding-top`（`app-layout-content--home`），因为浮动头像不遮挡居中内容
- 首页断言使用 `.home-title`，头像断言使用 `.app-header--home .user-avatar`
- 需要操作完整用户菜单的测试，先导航到 `/chat` 等子页面

## 开发注意

- 导航使用 `useRouter().push()` 实现，不依赖父组件 emit
- 每个导航卡片包含 SVG 图标、标题和描述文字
- 样式文件放在 `styles/` 目录下，通过 `<style scoped src="./styles/xxx.css">` 引入
- 不要在业务组件中直接写原生 `<button>`，应使用 `components/base/` 中的 `BaseButton`
