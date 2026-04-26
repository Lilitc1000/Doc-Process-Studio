# Components 开发指南

全局公共组件目录，按职责分为 `base/`（原子组件）和 `business/`（业务组件）两层。所有 UI 元素优先从此目录复用，禁止在业务组件中直接写原生 HTML 元素再自定义样式。

## 目录结构

```text
frontend/src/components/
├── base/                   # 原子组件：纯 UI，无业务语义
│   ├── BaseButton.vue      # 按钮（primary/secondary/danger/ghost + sm/md/lg）
│   ├── BaseDropdown.vue    # 下拉选择器（v-model 双向绑定）
│   ├── BaseModal.vue       # 模态对话框（header/default/footer 插槽）
│   ├── BaseInput.vue       # 文本输入框（label/required/invalid/errorMessage）
│   ├── PasswordInput.vue   # 密码输入框（基于 BaseInput + 可见性切换）
│   ├── BaseTextarea.vue    # 多行输入框（暴露 getTextareaEl()）
│   ├── BaseFileUpload.vue  # 文件上传触发器（slot 自定义 UI）
│   └── BaseDateTimePicker.vue # 日期/时间选择器（datetime/date/time）
└── business/               # 业务组件：跨页面复用，带业务语义
    ├── SessionSidebar.vue      # 会话侧边栏（Chat/Incident 共用）
    ├── FloatingToast.vue       # 顶部提示浮层
    ├── TraceReplayModal.vue    # Trace 回放弹窗
    ├── UserAvatar.vue          # 用户头像（首字母 + 颜色背景）
    ├── UserMenuDropdown.vue    # 用户菜单下拉
    └── UserProfileModal.vue    # 用户资料弹窗
```

## 分层规则

| 层级     | 目录        | 职责                    | 约束                                                           |
| -------- | ----------- | ----------------------- | -------------------------------------------------------------- |
| 原子组件 | `base/`     | 纯 UI，无业务，到处复用 | 禁止依赖 API，通过 props/emit 通信                             |
| 业务组件 | `business/` | 跨页面复用，带业务语义  | 可依赖特定 API 类型，但禁止直接调用 API（通过 props 传入数据） |

## 新增组件规范

### 原子组件（base/）

1. 必须是无状态或仅依赖 props 的纯展示组件
2. 样式内联在 `.vue` 的 `<style scoped>` 中，保证自包含
3. 当样式体量较大时，可拆到同目录并通过 `src` 引入
4. 必须暴露清晰的 props 接口和事件

### 业务组件（business/）

1. 优先内联样式；复杂样式可同目录 `src` 引入
2. 数据通过 props 传入，禁止直接调用 API
3. 若涉及多个业务域的通用逻辑，考虑抽为 composable

## 开发注意

- 按钮、输入框、下拉框、文件上传、日期选择、弹窗等基础 UI 元素必须使用 `base/` 中的组件
- 不要在业务组件中直接写原生 `<button>`/`<input>`/`<select>`/`<textarea>` 再自定义样式
- 现有基础组件不满足需求时，先在 `base/` 中扩展或新增
