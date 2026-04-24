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
- **事故报告** — 导航到 `/incident`
- **设置** — 导航到 `/settings`

## 开发注意

- 导航使用 `useRouter().push()` 实现，不依赖父组件 emit
- 每个导航卡片包含 SVG 图标、标题和描述文字
- 样式文件放在 `styles/` 目录下
