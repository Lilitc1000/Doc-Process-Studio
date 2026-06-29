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
    ├── AiGeneratingModal.vue   # AI 生成进度弹窗（思考动画 + 停止按钮）
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

## v-model 双向绑定规范

所有表单类原子组件（输入框、下拉框、日期选择器等）**必须**支持 `v-model` 双向绑定，确保父组件可以通过 `v-model` 读写组件值。

### 实现要求

1. 声明 `modelValue` prop 接收父组件传入的值
2. 声明 `update:modelValue` emit 在值变化时通知父组件
3. 设置 `inheritAttrs: false`，通过 `v-bind="$attrs"` 将父组件属性透传到原生元素
4. 在原生元素上绑定 `:value="modelValue"` 和 `@input`/`@change` 事件

### 模板

```vue
<template>
  <input
    :value="modelValue"
    v-bind="$attrs"
    @input="
      $emit('update:modelValue', ($event.target as HTMLInputElement).value)
    "
  />
</template>

<script setup lang="ts">
defineOptions({ inheritAttrs: false });

defineProps<{ modelValue?: string }>();

defineEmits<{ (e: 'update:modelValue', value: string): void }>();
</script>
```

### 各组件 v-model 支持情况

| 组件               | v-model 类型 | 说明                                                       |
| ------------------ | ------------ | ---------------------------------------------------------- |
| BaseInput          | `string`     | 文本输入框，`@input` 触发更新                              |
| BaseTextarea       | `string`     | 多行输入框，`@input` 触发更新                              |
| BaseDropdown       | `string`     | 下拉选择器，选择选项时触发更新                             |
| BaseDateTimePicker | `string`     | 日期/时间选择器，确认时触发更新，值为 ISO 格式字符串       |
| PasswordInput      | `string`     | 密码输入框，委托给 BaseInput 实现                          |
| BaseButton         | —            | 纯按钮，无需 v-model                                       |
| BaseFileUpload     | —            | 文件上传，使用 `@select` 事件返回 `File[]`，不适用 v-model |
