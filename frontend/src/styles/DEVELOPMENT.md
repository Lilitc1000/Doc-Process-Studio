# Styles 开发指南

全局样式目录，仅存放 CSS 变量、reset、全局字体和共享过渡动画。业务域样式放在对应 `views/xxx/styles/` 目录下。

## 目录结构

```text
frontend/src/styles/
├── base.css          # 全局 CSS 变量、reset、全局字体
└── transitions.css   # 全局过渡动画（fade / fade-slide-up / page-switch / session-switch）
```

## base.css

定义全局设计 Token，所有组件统一使用：

| 变量                     | 用途     | 示例值    |
| ------------------------ | -------- | --------- |
| `--color-primary`        | 主色     | `#4f46e5` |
| `--color-primary-hover`  | 主色悬停 | `#4338ca` |
| `--color-text-primary`   | 主文本   | `#1f2937` |
| `--color-text-secondary` | 辅助文本 | `#6b7280` |
| `--color-text-tertiary`  | 占位文本 | `#9ca3af` |
| `--color-border`         | 边框     | `#d1d5db` |
| `--color-border-hover`   | 边框悬停 | `#9ca3af` |
| `--color-bg-hover`       | 背景悬停 | `#f3f4f6` |
| `--color-bg-disabled`    | 禁用背景 | `#f9fafb` |

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
- 不引入第三方 CSS 框架，所有样式手写
