# 事故报告（incident-report）开发说明

## 目录结构

- `IncidentReportView.vue` —— 事故报告页面入口
- `components/IncidentReportWorkspace.vue` —— 表单与预览工作区
- `composables/useIncidentReportSessions.ts` —— 会话管理
- `composables/useIncidentReportForm.ts` —— 表单与快照保存
- `composables/useIncidentReportGeneration.ts` —— AI 生成与预览
- `styles/incident-report-page.css` —— 页面布局样式
- `styles/incident-report-workspace.css` —— 工作区样式

## 命名规范

- 文件名使用 kebab-case（如 `incident-report-page.css`）
- JS 变量 / 函数使用 camelCase（如 `incidentReportStore`）
- Vue 组件定义使用 PascalCase（如 `IncidentReportWorkspace.vue`）
- CSS 类名使用 kebab-case（如 `.incident-report-workspace`）
- API 路径使用 kebab-case（如 `/incident-report/schema`）
