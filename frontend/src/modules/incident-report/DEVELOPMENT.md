# Incident Report 页面开发指南

## 目录结构

```text
frontend/src/views/incident-report/
├── list/                          # 报告列表页
│   ├── IncidentReportListView.vue
│   ├── composables/
│   │   └── useReportList.ts
│   ├── components/
│   │   ├── ReportListFilters.vue
│   │   ├── ReportListTable.vue
│   │   └── ReportListBulkActions.vue
│   └── styles/
├── detail/                        # 报告详情页
│   ├── IncidentReportDetailView.vue
│   ├── composables/
│   │   └── useReportDetail.ts
│   ├── components/
│   │   ├── ReportDetailHeader.vue
│   │   ├── ReportDetailSidebar.vue
│   │   ├── ReportDetailContent.vue
│   │   ├── ReportAuditTimeline.vue
│   │   └── ReportComments.vue
│   └── styles/
├── create/                        # 创建报告页（向导式）
│   ├── IncidentReportCreateView.vue
│   ├── composables/
│   │   └── useReportWizard.ts
│   ├── components/
│   │   └── ReportWizardSteps.vue
│   └── styles/
├── edit/                          # 编辑报告页（向导式，5步）
│   ├── IncidentReportEditView.vue
│   └── composables/
│       └── useReportEditWizard.ts
├── analytics/                     # 数据分析页
│   ├── IncidentReportAnalyticsView.vue
│   ├── composables/
│   │   └── useReportAnalytics.ts
│   ├── components/
│   │   ├── StatsCards.vue
│   │   ├── DistributionChart.vue
│   │   └── TrendChart.vue
│   └── styles/
├── roles/                         # 角色权限管理页
│   └── RoleManagementView.vue
├── components/                    # 共享组件
│   ├── ReportStatusBadge.vue
│   ├── SchemaFormRenderer.vue
│   ├── RichTextEditor.vue
│   └── TimelineEditor.vue
├── composables/                   # 共享 composables
│   ├── useReportGeneration.ts     # AI 生成共享逻辑（快填、分段生成、预览、结果应用）
│   └── useReportForm.ts           # 表单工具函数（severityOptions/statusOptions 从 constants.ts 导入，defaultFormAnswers/buildFormPayload/validateTimelineTimeOrder 独立导出）
└── styles/
    └── incident-report-mobile.css
```

## Store 状态说明

`useIncidentReportStore`（不持久化）：

- 报告列表状态（`reportList`, `reportListTotal`, `reportListPage`, `reportListPageSize`, `reportListLoading`）
- 当前报告（`activeReport`）
- 用户角色（`userIncidentRoles`）
- 用户权限（`userIncidentPermissions`）
- 分析数据（`analyticsOverview`）
- 生成状态（`isIncidentReportGenerating`, `generationState`, `generationTask`）

### 计算属性

| 属性                | 说明                                  |
| ------------------- | ------------------------------------- |
| `isAdmin`           | 是否管理员                            |
| `isVerifier`        | 是否审核人                            |
| `isHandler`         | 是否处理人                            |
| `isReporter`        | 是否报告人                            |
| `canCreateReport`   | 是否可创建报告（report:create）       |
| `canAudit`          | 是否可审核（report:audit）            |
| `canManageSettings` | 是否可管理设置（role:manage）         |
| `canDeleteReport`   | 是否可删除报告（report:delete）       |
| `canEditAllReport`  | 是否可编辑所有报告（report:edit_all） |
| `canReopenReport`   | 是否可重开报告（report:reopen）       |

### 权限方法

| 方法                     | 说明                         |
| ------------------------ | ---------------------------- |
| `hasPermission(p)`       | 检查用户是否拥有指定权限     |
| `hasAnyPermission(...p)` | 检查用户是否拥有任一指定权限 |

## 路由结构

| 路径                         | 组件                        | 说明         |
| ---------------------------- | --------------------------- | ------------ |
| `/incident-report`           | IncidentReportListView      | 报告列表     |
| `/incident-report/create`    | IncidentReportCreateView    | 创建报告     |
| `/incident-report/analytics` | IncidentReportAnalyticsView | 数据分析     |
| `/incident-report/roles`     | RoleManagementView          | 角色权限管理 |
| `/incident-report/:id`       | IncidentReportDetailView    | 报告详情     |
| `/incident-report/:id/edit`  | IncidentReportEditView      | 编辑报告     |

路由守卫：旧 32+ 字符 hex session ID 自动重定向到列表页。

审核功能在报告详情页通过弹窗实现，点击"审核"按钮弹出审核对话框（含审核意见输入和通过/驳回操作），审核后自动刷新页面状态。

详情页操作按钮根据报告状态和用户权限动态显示：

- **提交审核**：`draft`/`rejected` 状态 + `report:submit` 权限，弹出 `BaseConfirmDialog` 确认
- **审核**：`pending` 状态 + `report:audit` 权限，弹出审核对话框（含 `BaseTextarea` + 通过/驳回），二次确认使用 `BaseConfirmDialog`
- **分配处理人**：`approved`/`in_progress` 状态 + `report:assign` 权限，弹出分配对话框（含 `BaseDropdown` 选择处理人），二次确认使用 `BaseConfirmDialog`
- **关闭**：`in_progress` 状态 + `report:close_assigned` 权限，弹出 `BaseConfirmDialog` 确认
- **重新打开**：`closed` 状态 + `report:reopen` 权限，弹出 `BaseConfirmDialog` 确认

所有操作完成后自动刷新审核记录（通过 `refreshLogs` 方法），无需手动刷新页面。

编辑报告页面最后一步同时提供"保存"和"提交审核"按钮，提交审核会先保存再调用提交接口。

## API 依赖

| API                                                   | 方法            | 用途                   |
| ----------------------------------------------------- | --------------- | ---------------------- |
| `/incident-report/reports`                            | GET             | 报告列表（分页/筛选）  |
| `/incident-report/reports`                            | POST            | 创建报告               |
| `/incident-report/reports/{id}`                       | GET             | 报告详情               |
| `/incident-report/reports/{id}`                       | PUT             | 更新报告               |
| `/incident-report/reports/{id}`                       | DELETE          | 删除报告               |
| `/incident-report/reports/{id}/submit`                | POST            | 提交审核               |
| `/incident-report/reports/{id}/approve`               | POST            | 批准                   |
| `/incident-report/reports/{id}/reject`                | POST            | 驳回                   |
| `/incident-report/reports/{id}/assign`                | POST            | 指派处理人             |
| `/incident-report/reports/{id}/close`                 | POST            | 关闭                   |
| `/incident-report/reports/{id}/reopen`                | POST            | 重新打开               |
| `/incident-report/reports/{id}/audit-logs`            | GET             | 审计日志               |
| `/incident-report/reports/{id}/comments`              | GET/POST        | 评论                   |
| `/incident-report/reports/{id}/body/quick-generate`   | POST            | 快填 AI 一键生成正文   |
| `/incident-report/reports/{id}/body/section-generate` | POST            | 分段 AI 生成正文段落   |
| `/incident-report/reports/{id}/preview`               | POST            | 生成 PDF/DOCX 预览     |
| `/incident-report/roles/me`                           | GET             | 当前用户角色和权限     |
| `/incident-report/roles`                              | GET/POST/DELETE | 角色管理               |
| `/incident-report/users-with-roles`                   | GET             | 全部用户及角色列表     |
| `/incident-report/role-definitions`                   | GET             | 角色定义列表（含权限） |
| `/incident-report/permissions`                        | GET             | 权限定义列表           |
| `/incident-report/analytics/overview`                 | GET             | 全量概览               |
| `/incident-report/analytics/trend`                    | GET             | 新建报告趋势           |

## 创建页 5 步向导

创建页使用 5 步向导流程，每步对应一个表单区域：

| 步骤 | key        | 标签              | 说明                                                                     |
| ---- | ---------- | ----------------- | ------------------------------------------------------------------------ |
| 0    | cover      | 首页 / Cover      | SECTION A（故障记录）、SECTION B（维修与验证）、SECTION C（结案与签署）  |
| 1    | quick_fill | 快填 / Quick Fill | 可跳过；填写简述后可一键 AI 生成完整正文                                 |
| 2    | body       | AI 正文 / Body    | 事故简述、时间线、影响范围、根因分析、后续动作；可逐段 AI 生成或手动编辑 |
| 3    | appendix   | 附录 / Appendix   | 附录文本输入                                                             |
| 4    | preview    | 预览 / Preview    | 生成 PDF 预览，支持 PDF 浏览器查看和 DOCX 下载                           |

### 向导核心逻辑

向导逻辑封装在 `create/composables/useReportWizard.ts` 中：

| 方法                    | 说明                                                 |
| ----------------------- | ---------------------------------------------------- |
| `saveAsDraft`           | 保存草稿（首次创建，后续更新）                       |
| `createAndSubmit`       | 创建并提交审核                                       |
| `quickGenerate`         | 调用快填 AI 生成 API，自动填充正文字段并跳转到步骤 2 |
| `generateSection`       | 调用分段 AI 生成 API，生成指定正文段落               |
| `generatePreview`       | 调用预览 API，生成 PDF/DOCX 预览                     |
| `applyGenerationResult` | 将 AI 生成结果合并到 formAnswers                     |

### AI 生成流程

1. 步骤 1（快填）：用户填写事故简述 → 点击「一键生成正文」→ 调用 `quickGenerate` → 结果自动填充到步骤 2 各字段 → 自动跳转到步骤 2
2. 步骤 2（正文）：每个正文段落旁有「AI 生成」按钮 → 调用 `generateSection` → 结果填充到对应字段
3. 步骤 4（预览）：点击「生成预览」→ 调用 `generatePreview` → 返回 HTML/PDF/DOCX → 支持 PDF 浏览器查看和 DOCX 下载

### 表单数据结构

- `formData`：报告元数据（title, severity, system, siteId, faultDate）
- `formAnswers`：表单字段键值对，前缀区分区域：
  - `manual_*` — 首页 SECTION A-C 字段
  - `quick_*` — 快填字段
  - `body_*` — 正文字段
  - `appendix_*` — 附录字段
- `quickTimelineItems` / `bodyTimelineItems`：时间线数组，通过 watch 同步到 formAnswers

## 编辑页 5 步向导

编辑页使用 5 步向导流程（与创建页完全一致）：

| 步骤 | key        | 标签              | 说明                                                                     |
| ---- | ---------- | ----------------- | ------------------------------------------------------------------------ |
| 0    | cover      | 首页 / Cover      | SECTION A（故障记录）、SECTION B（维修与验证）、SECTION C（结案与签署）  |
| 1    | quick_fill | 快填 / Quick Fill | 填写事故简述后一键 AI 生成完整正文，可跳过                               |
| 2    | body       | AI 正文 / Body    | 事故简述、时间线、影响范围、根因分析、后续动作；可逐段 AI 生成或手动编辑 |
| 3    | appendix   | 附录 / Appendix   | 附录文本输入                                                             |
| 4    | preview    | 预览 / Preview    | 生成 PDF 预览，支持 PDF 浏览器查看和 DOCX 下载                           |

### 编辑向导核心逻辑

向导逻辑封装在 `edit/composables/useReportEditWizard.ts` 中，AI 生成相关逻辑复用自共享 composable `composables/useReportGeneration.ts`：

| 方法                    | 说明                                   |
| ----------------------- | -------------------------------------- |
| `load`                  | 加载报告详情并填充表单                 |
| `save`                  | 保存报告更新                           |
| `quickGenerate`         | 调用快填 AI 生成 API，一键生成完整正文 |
| `generateSection`       | 调用分段 AI 生成 API，生成指定正文段落 |
| `generatePreview`       | 调用预览 API，生成 PDF/DOCX 预览       |
| `applyGenerationResult` | 将 AI 生成结果合并到 formAnswers       |

### 编辑页与创建页的差异

- 编辑页与创建页使用相同的 5 步向导流程，均包含快填步骤
- 编辑页加载时自动填充已有数据
- 编辑页底部操作栏为「取消」和「保存」，而非创建页的「保存草稿」和「提交报告」
- 编辑页样式复用创建页的 CSS（`create/styles/incident-report-create.css`）
- AI 生成相关逻辑（quickGenerate、generateSection、generatePreview、applyGenerationResult）提取到共享 composable `composables/useReportGeneration.ts`，创建页和编辑页共同复用

## 类型定义

核心类型定义在 `types/incident-report/incident-report.ts`：

| 类型                            | 说明                                                           |
| ------------------------------- | -------------------------------------------------------------- |
| `IncidentReportStatus`          | 状态枚举（draft/pending/approved/rejected/in_progress/closed） |
| `IncidentSeverity`              | 严重级别（P0/P1/P2/P3）                                        |
| `IncidentReportPreviewResponse` | 预览响应（HTML + PDF Base64 + DOCX Base64）                    |
| `IncidentBodyGenerateResponse`  | AI 生成响应（reportId + formAnswers + traceId + sectionId）    |
| `IncidentReportSummaryItem`     | 列表项                                                         |
| `IncidentReportDetailItem`      | 详情项                                                         |
| `IncidentAuditLogEntry`         | 审计日志条目                                                   |
| `IncidentCommentEntry`          | 评论条目                                                       |
| `IncidentAnalyticsOverview`     | 分析概览                                                       |
| `IncidentAnalyticsTrend`        | 趋势数据                                                       |
| `IncidentUserRolesResponse`     | 用户角色和权限响应                                             |
| `IncidentRoleEntry`             | 角色分配条目                                                   |

## 开发注意

- 文件名使用 kebab-case（如 `incident-report-mobile.css`）
- JS 变量 / 函数使用 camelCase（如 `incidentReportStore`）
- Vue 组件定义使用 PascalCase（如 `IncidentReportListView.vue`）
- CSS 类名使用 kebab-case（如 `.incident-report-list-view`）
- 样式文件放在 `styles/` 目录下，通过 `<style scoped src="./styles/xxx.css">` 引入
- 不要在业务组件中直接写原生 `<button>`/`<input>`，应使用 `components/base/` 中的基础组件
- 状态徽章组件 `ReportStatusBadge` 使用 `status.replace(/_/g, '-')` 生成 CSS 类名
- Schema 表单渲染器 `SchemaFormRenderer` 根据 `form_schema.py` 返回的 Schema 动态渲染表单
