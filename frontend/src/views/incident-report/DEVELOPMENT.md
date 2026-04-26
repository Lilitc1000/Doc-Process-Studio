# Incident Report 页面开发指南

## 目录结构

```text
frontend/src/views/incident-report/
├── list/                          # 报告列表页
│   ├── IncidentReportListView.vue
│   ├── composables/
│   │   └── useReportList.ts
│   ├── components/
│   │   ├── ReportListStats.vue
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
├── edit/                          # 编辑报告页
│   ├── IncidentReportEditView.vue
│   ├── composables/
│   │   └── useReportEdit.ts
│   └── styles/
├── audit/                         # 审核报告页
│   ├── IncidentReportAuditView.vue
│   ├── composables/
│   │   └── useReportAudit.ts
│   ├── components/
│   │   └── AuditActionPanel.vue
│   └── styles/
├── analytics/                     # 数据分析页
│   ├── IncidentReportAnalyticsView.vue
│   ├── composables/
│   │   └── useReportAnalytics.ts
│   ├── components/
│   │   ├── StatsCards.vue
│   │   ├── DistributionChart.vue
│   │   └── TrendChart.vue
│   └── styles/
├── components/                    # 共享组件
│   ├── ReportStatusBadge.vue
│   ├── SchemaFormRenderer.vue
│   ├── RichTextEditor.vue
│   └── TimelineEditor.vue
├── composables/                   # 共享 composables
│   └── useIncidentReportRoles.ts
└── styles/
    └── incident-report-mobile.css
```

## Store 状态说明

`useIncidentReportStore`（不持久化）：

- 报告列表状态（`reportList`, `reportListTotal`, `reportListPage`, `reportListPageSize`, `reportListLoading`）
- 当前报告（`activeReport`）
- 用户角色（`userIncidentRoles`）
- 分析数据（`analyticsOverview`）
- 表单定义（`incidentReportSchema`）
- 生成状态（`isIncidentReportGenerating`, `generationState`, `generationTask`）
- 预览状态（`incidentReportPreviewHtml`, `incidentReportPreviewPdfBase64`, `incidentReportPreviewLoading`）

### 计算属性

| 属性                | 说明                            |
| ------------------- | ------------------------------- |
| `isAdmin`           | 是否管理员                      |
| `isVerifier`        | 是否审核人                      |
| `isHandler`         | 是否处理人                      |
| `isReporter`        | 是否报告人                      |
| `canCreateReport`   | 是否可创建报告                  |
| `canAudit`          | 是否可审核（verifier 或 admin） |
| `canManageSettings` | 是否可管理设置（admin）         |

## 路由结构

| 路径                         | 组件                        | 说明     |
| ---------------------------- | --------------------------- | -------- |
| `/incident-report`           | IncidentReportListView      | 报告列表 |
| `/incident-report/create`    | IncidentReportCreateView    | 创建报告 |
| `/incident-report/analytics` | IncidentReportAnalyticsView | 数据分析 |
| `/incident-report/:id`       | IncidentReportDetailView    | 报告详情 |
| `/incident-report/:id/edit`  | IncidentReportEditView      | 编辑报告 |
| `/incident-report/:id/audit` | IncidentReportAuditView     | 审核报告 |

路由守卫：旧 32+ 字符 hex session ID 自动重定向到列表页。

## API 依赖

| API                                        | 方法            | 用途                  |
| ------------------------------------------ | --------------- | --------------------- |
| `/incident-report/reports`                 | GET             | 报告列表（分页/筛选） |
| `/incident-report/reports`                 | POST            | 创建报告              |
| `/incident-report/reports/schema`          | GET             | 获取表单 Schema       |
| `/incident-report/reports/{id}`            | GET             | 报告详情              |
| `/incident-report/reports/{id}`            | PUT             | 更新报告              |
| `/incident-report/reports/{id}`            | DELETE          | 删除报告              |
| `/incident-report/reports/{id}/submit`     | POST            | 提交审核              |
| `/incident-report/reports/{id}/approve`    | POST            | 批准                  |
| `/incident-report/reports/{id}/reject`     | POST            | 驳回                  |
| `/incident-report/reports/{id}/assign`     | POST            | 指派处理人            |
| `/incident-report/reports/{id}/close`      | POST            | 关闭                  |
| `/incident-report/reports/{id}/reopen`     | POST            | 重新打开              |
| `/incident-report/reports/{id}/audit-logs` | GET             | 审计日志              |
| `/incident-report/reports/{id}/comments`   | GET/POST        | 评论                  |
| `/incident-report/roles/me`                | GET             | 当前用户角色          |
| `/incident-report/roles`                   | GET/POST/DELETE | 角色管理              |
| `/incident-report/analytics/overview`      | GET             | 月度概览              |
| `/incident-report/analytics/trend`         | GET             | 趋势数据              |

## 核心交互流程

1. 列表页展示报告列表，支持状态/严重级别/关键词筛选
2. 创建页使用 5 步向导（基本信息 → 事故描述 → 时间线 → 附录 → 确认提交）
3. 详情页展示报告内容、审计时间线、评论
4. 审核页供审核人批准/驳回报告
5. 分析页展示月度统计、分布图、趋势图

## 类型定义

核心类型定义在 `types/incident-report/incident-report.ts`：

| 类型                        | 说明                                                           |
| --------------------------- | -------------------------------------------------------------- |
| `IncidentReportStatus`      | 状态枚举（draft/pending/approved/rejected/in_progress/closed） |
| `IncidentSeverity`          | 严重级别（P0/P1/P2/P3）                                        |
| `IncidentReportSummaryItem` | 列表项                                                         |
| `IncidentReportDetailItem`  | 详情项                                                         |
| `IncidentAuditLogEntry`     | 审计日志条目                                                   |
| `IncidentCommentEntry`      | 评论条目                                                       |
| `IncidentAnalyticsOverview` | 分析概览                                                       |
| `IncidentAnalyticsTrend`    | 趋势数据                                                       |

## 开发注意

- 文件名使用 kebab-case（如 `incident-report-mobile.css`）
- JS 变量 / 函数使用 camelCase（如 `incidentReportStore`）
- Vue 组件定义使用 PascalCase（如 `IncidentReportListView.vue`）
- CSS 类名使用 kebab-case（如 `.incident-report-list-view`）
- 样式文件放在 `styles/` 目录下，通过 `<style scoped src="./styles/xxx.css">` 引入
- 不要在业务组件中直接写原生 `<button>`/`<input>`，应使用 `components/base/` 中的基础组件
- 状态徽章组件 `ReportStatusBadge` 使用 `status.replace(/_/g, '-')` 生成 CSS 类名
- Schema 表单渲染器 `SchemaFormRenderer` 根据 `form_schema.py` 返回的 Schema 动态渲染表单
