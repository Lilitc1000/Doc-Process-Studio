# Frontend 开发指南

本项目是基于 `Vue 3 + Vite + TypeScript` 的单页聊天前端。

这份文档的目标不是介绍通用 Vue 用法，而是说明当前 `frontend` 目录里这套代码是如何组织的、后续应该按什么方式继续维护，避免把这次已经整理好的结构再慢慢堆回单文件大组件。

## 启动与校验

常用命令：

```bash
npm install
npm run dev
npm run build
npm run lint
npm run test
npx -y vue-tsc --noEmit
```

开发时建议至少保证下面 3 项通过：

```bash
npm run lint
npx -y vue-tsc --noEmit
npm run build
```

提交前建议再补一遍：

```bash
npm run test
```

## 目录约定

当前前端目录按“组件 / 类型 / API / 工具 / 样式 / 组合式逻辑”分层：

```text
frontend/
  src/
    api/            # 所有 HTTP 请求封装
    components/     # 页面组件与 UI 组件
    composables/    # 可复用状态逻辑
    styles/         # 全局样式与组件样式
    types/          # 跨组件共享类型
    utils/          # 纯函数、渲染工具、格式化工具
    env.d.ts        # Vue / CSS 模块声明
    main.ts         # 应用入口
    App.vue         # 根组件
  tests/            # Vitest 测试
```

后续新增代码时，优先遵守下面这几个边界：

- `components/` 放界面和交互，不要把大量 API 请求和复杂数据处理继续塞回组件。
- `api/` 只负责请求与响应映射，不负责页面状态。
- `types/` 只放跨文件共享的类型；组件内部临时类型不必硬抽。
- `utils/` 放无状态纯函数，避免依赖 Vue 生命周期。
- `composables/` 放“和页面状态有关，但已经重到不适合继续留在组件里”的逻辑。
- `styles/components/` 放组件对应的样式文件，避免超长 `<style>` 继续堆在 `.vue` 里。

## 当前核心结构

### 1. 组件层

- [ChatLayout.vue](/workspace/frontend/src/components/ChatLayout.vue)
  页面主控组件，负责消息树、版本切换、输入区、历史会话视图编排。
- [ChatMessage.vue](/workspace/frontend/src/components/ChatMessage.vue)
  单条消息渲染，包含编辑态、版本切换区、工具栏、Markdown 渲染入口。
- [ChatInput.vue](/workspace/frontend/src/components/ChatInput.vue)
  底部输入区与文件选择。
- [ChatSidebar.vue](/workspace/frontend/src/components/ChatSidebar.vue)
  左侧历史会话与模型 / skill 选择区域。

### 2. 组合式逻辑

- [useChatSessions.ts](/workspace/frontend/src/composables/useChatSessions.ts)
  历史会话加载、保存、重命名、删除、会话切换后的状态恢复。
- [useChatStreaming.ts](/workspace/frontend/src/composables/useChatStreaming.ts)
  流式生成、停止生成、流式内容回填。
- [useCopyToast.ts](/workspace/frontend/src/composables/useCopyToast.ts)
  顶部复制成功提示。

### 3. 请求层

- [api/client.ts](/workspace/frontend/src/api/client.ts)
  `axios` 实例。
- [api/catalog.ts](/workspace/frontend/src/api/catalog.ts)
  模型列表、skill 列表请求。
- [api/sessions.ts](/workspace/frontend/src/api/sessions.ts)
  历史会话接口。
- [api/chat.ts](/workspace/frontend/src/api/chat.ts)
  聊天流式请求封装。

### 4. 类型层

- [types/chat.ts](/workspace/frontend/src/types/chat.ts)
  消息节点、聊天请求、流式事件等类型。
- [types/session.ts](/workspace/frontend/src/types/session.ts)
  历史会话与快照结构。
- [types/skill.ts](/workspace/frontend/src/types/skill.ts)
  skill 选项与 catalog 结构。

### 5. 工具层

- [utils/render-markdown.ts](/workspace/frontend/src/utils/render-markdown.ts)
  Markdown 渲染、高亮语言按需加载、消息渲染缓存、预热逻辑。
- [utils/chat-stream.ts](/workspace/frontend/src/utils/chat-stream.ts)
  SSE 数据解析。
- [utils/session-groups.ts](/workspace/frontend/src/utils/session-groups.ts)
  历史会话分组。
- [utils/catalog.ts](/workspace/frontend/src/utils/catalog.ts)
  模型和 skill 响应归一化。
- [utils/file.ts](/workspace/frontend/src/utils/file.ts)
  文件大小格式化。
- [utils/ids.ts](/workspace/frontend/src/utils/ids.ts)
  前端会话 ID / 消息 ID 生成。

## TypeScript 配置说明

当前有 4 个 TS 配置文件，这属于正常拆分：

- [tsconfig.base.json](/workspace/frontend/tsconfig.base.json)
  公共编译选项。
- [tsconfig.json](/workspace/frontend/tsconfig.json)
  前端应用默认配置，编辑器主要吃这个。
- [tsconfig.app.json](/workspace/frontend/tsconfig.app.json)
  应用代码入口别名，和当前项目结构保持一致。
- [tsconfig.node.json](/workspace/frontend/tsconfig.node.json)
  给 `vite.config.mts`、`vitest.config.ts` 这类 Node 侧配置文件使用。

如果后续出现“命令行没报错，但编辑器局部红线”的情况，优先检查：

1. 新文件是否落在 `tsconfig.json` / `tsconfig.app.json` 的 `include` 范围内。
2. 是否缺少 `.d.ts` 模块声明。
3. 是否把 Node 配置文件误放进了应用配置里。

## 样式约定

当前样式已经从大部分组件里拆出，放在：

- [base.css](/workspace/frontend/src/styles/base.css)
- [chat-layout.css](/workspace/frontend/src/styles/components/chat-layout.css)
- [chat-message.css](/workspace/frontend/src/styles/components/chat-message.css)
- [chat-input.css](/workspace/frontend/src/styles/components/chat-input.css)
- [chat-sidebar.css](/workspace/frontend/src/styles/components/chat-sidebar.css)

后续样式维护建议：

- 全局变量、页面底色、基础 reset 放 `base.css`
- 组件视觉样式放对应 `styles/components/*.css`
- 不要把几百行样式重新堆回单个 `.vue`
- 如果只是非常局部、非常短的小样式，再考虑留在组件里

## Markdown 渲染与性能优化

当前消息渲染已经做了几层优化，后续维护时不要轻易破坏这条链路：

### 1. 纯文本绕过 Markdown

普通用户纯文本消息不会默认触发 `markdown-it`。

### 2. 懒渲染

需要 Markdown 的消息只有在接近视口时，才真正执行 Markdown 渲染。

### 3. 高亮按需加载

`highlight.js` 使用的是 `core + 常用语言按需注册`，没有整包直接灌进主包。

### 4. 会话级共享缓存

消息渲染缓存以：

```text
cacheScopeId + messageId + role + contentHash
```

作为 key，不同会话不会乱串。

### 5. sessionStorage 短期复用

缓存会同步到 `sessionStorage`，页面刷新后可短期复用。

### 6. 历史会话预热

切换历史会话后，会后台预热当前可见消息的缓存。

### 7. 版本切换预热

当前可见路径上的消息，会额外预热相邻版本，提升上一版 / 下一版切换命中率。

如果后续还要继续优化这一块，优先顺序建议是：

1. 保持现有缓存链路稳定
2. 只扩大“预热范围”而不是推翻渲染结构
3. 真到超长会话明显卡顿时，再考虑消息列表虚拟滚动

## 新功能开发建议

### 新增接口

如果新增后端接口：

1. 先在 `src/api/` 增加请求函数
2. 再在 `src/types/` 补共享响应类型
3. 最后在组件或 composable 中消费

不要在组件里直接散写 `axios.get(...)` / `fetch(...)`。

### 新增共享状态逻辑

如果某段逻辑已经同时满足下面两条，就优先抽 composable：

- 超过一个组件会用
- 或者虽然只有一个组件在用，但状态和副作用已经明显让组件变重

### 新增工具函数

如果是纯格式化、纯映射、纯解析逻辑，优先放 `src/utils/`，不要放进组件。

## 测试约定

当前测试使用：

- `Vitest`
- `@vue/test-utils`
- `happy-dom`

测试目录在 [tests](/workspace/frontend/tests)。

目前已经覆盖的方向包括：

- catalog 映射
- 历史会话分组
- 聊天流事件解析
- `ChatSidebar` 基础交互

后续如果继续补测试，优先补这些高价值点：

1. 历史会话切换
2. 消息版本切换
3. 编辑后重新发送
4. Markdown 缓存 / 预热逻辑
5. 流式输出回填

## 维护时尽量避免的事

- 不要把 API 请求重新塞回 `.vue`
- 不要把共享类型重新写回组件内部
- 不要把长样式块再塞回 SFC
- 不要为了“规范”过早上 Pinia 或更重的状态架构
- 不要在消息渲染链路里随意去掉缓存、懒渲染和按需加载

## 当前建议的维护顺序

如果以后继续整理前端，建议优先级如下：

1. 保持 `ChatLayout.vue` 不再回涨
2. 新逻辑优先落到 `api / utils / composables`
3. 补测试而不是堆更多手工回归
4. 真出现长会话性能瓶颈时，再考虑虚拟滚动

这份 README 应该和当前代码实现保持同步。如果后续目录结构或渲染链路有明显变动，请一起更新这份文档。
