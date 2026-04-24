# Settings 页面开发指南

## 目录结构

```text
frontend/src/views/settings/
├── SettingsView.vue             # 设置页面主组件
└── styles/
    └── settings-page.css
```

## API 依赖

| API       | 方法 | 用途             |
| --------- | ---- | ---------------- |
| `/models` | GET  | 获取可用模型列表 |

## 功能说明

设置页面提供 AI 模型配置：

- **聊天模型** — 选择对话使用的模型（`BaseDropdown` 组件）
- **重排序模型** — 选择重排序使用的模型（`BaseDropdown` 组件）

模型列表从 `/api/models` 获取，选择后自动保存到 `appStore`。

## 开发注意

- 使用 `BaseDropdown` 公共组件，不要自己实现下拉框
- 模型选择后通过 `appStore.setSelectedModel()` / `appStore.setSelectedRerankerModel()` 保存
- 不需要自己的 AppHeader，DefaultLayout 已提供
- 样式文件放在 `styles/` 目录下
