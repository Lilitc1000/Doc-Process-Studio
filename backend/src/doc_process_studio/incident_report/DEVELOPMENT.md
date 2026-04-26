# Incident Report 业务域开发指南

## 概述

Incident Report 域负责事故报告的全生命周期管理，包括创建、编辑、审核、关闭、数据分析，以及 AI 生成正文、预览和翻译。

## 目录结构

```text
backend/src/doc_process_studio/incident_report/
├── router/
│   ├── reports.py            # 报告 CRUD + 状态流转 + 评论 API
│   ├── roles.py              # 角色管理 API
│   ├── analytics.py          # 数据分析 API
│   └── dependencies.py       # 权限依赖（require_admin, require_verifier_or_admin）
├── service/
│   ├── report.py             # 报告业务逻辑（创建/提交/审核/关闭/重开）
│   ├── report_store.py       # PostgreSQL 报告存储
│   ├── role.py               # 角色 CRUD（get/has/assign/revoke）
│   ├── audit_log.py          # 审计日志记录
│   ├── form_schema.py        # 表单 Schema 定义（4 步骤）
│   ├── form_validation.py    # 服务端表单校验
│   ├── generation.py         # AI 生成正文（一键 / 分段）
│   ├── preview.py            # HTML 预览 + DOCX/PDF 导出
│   ├── translation.py        # 多语言翻译
│   ├── report_data.py        # 表单数据 → report_data 转换
│   └── reference.py          # Skill 参考文档加载
├── models/
│   ├── incident_report_orm.py  # IncidentReport + IncidentComment ORM
│   ├── incident_report_role.py # IncidentReportRole ORM
│   └── audit_log.py            # IncidentAuditLog ORM
└── schemas/
    ├── request.py           # 入参模型
    ├── response.py          # 出参模型
    ├── common.py            # 共享常量 + 数据模型（IncidentFormAnswer, IncidentFormSnapshot 等）
    └── __init__.py
```

## API 端点

### 报告管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/incident-report/reports` | 报告列表（分页/筛选） |
| POST | `/api/incident-report/reports` | 创建报告 |
| GET | `/api/incident-report/reports/schema` | 获取表单 Schema |
| GET | `/api/incident-report/reports/{id}` | 报告详情 |
| PUT | `/api/incident-report/reports/{id}` | 更新报告 |
| DELETE | `/api/incident-report/reports/{id}` | 删除报告 |
| POST | `/api/incident-report/reports/{id}/submit` | 提交审核 |
| POST | `/api/incident-report/reports/{id}/approve` | 批准报告 |
| POST | `/api/incident-report/reports/{id}/reject` | 驳回报告 |
| POST | `/api/incident-report/reports/{id}/assign` | 指派处理人 |
| POST | `/api/incident-report/reports/{id}/close` | 关闭报告 |
| POST | `/api/incident-report/reports/{id}/reopen` | 重新打开 |
| GET | `/api/incident-report/reports/{id}/audit-logs` | 审计日志 |
| GET | `/api/incident-report/reports/{id}/comments` | 评论列表 |
| POST | `/api/incident-report/reports/{id}/comments` | 添加评论 |

### 角色管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/incident-report/roles/me` | 当前用户角色 |
| GET | `/api/incident-report/roles` | 全部角色分配（管理员） |
| POST | `/api/incident-report/roles` | 分配角色（管理员） |
| DELETE | `/api/incident-report/roles/{userId}/{role}` | 撤销角色（管理员） |

### 数据分析

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/incident-report/analytics/overview` | 月度概览统计 |
| GET | `/api/incident-report/analytics/trend` | 趋势数据（按天） |

## 状态机

```text
draft ──submit──→ pending ──approve──→ approved ──start──→ in_progress ──close──→ closed
  ↑                 │                                        │
  │                reject → rejected ──resubmit──→ pending    │
  └──────────────────────────────────────── reopen ──────────┘
```

有效状态：`draft`, `pending`, `approved`, `rejected`, `in_progress`, `closed`

状态转换规则定义在 `schemas/common.py` 的 `STATUS_TRANSITIONS` 中。

## 权限模型

| 角色 | 权限 |
|------|------|
| `reporter` | 创建/编辑/提交自己的报告 |
| `handler` | 处理被指派的报告 |
| `verifier` | 审核报告（批准/驳回） |
| `admin` | 全部权限 + 角色管理 + 删除 |
| `viewer` | 只读查看 |

权限依赖定义在 `router/dependencies.py` 中，通过 FastAPI `Depends` 注入。

## 正文生成链路

1. 快填模式仅输入简述文本，调用 `body/quick-generate`
2. 模型返回 JSON，后端统一回填到完整模式字段
3. 完整模式支持分段生成（description/timeline/impact/root_cause/follow_up/timeline_item）
4. 每次正文生成都会记录 `trace_id` 并落入 `section_trace_ids`
5. 生成结果通过 `report_store.update_report_record` 写回 `incident_reports` 表

### 关键数据模型

- `IncidentFormAnswer` — 单个表单步骤的答案（value + custom_value）
- `IncidentFormSnapshot` — 完整表单快照（form_answers + report_data + trace 信息）
- `IncidentBodyGenerateResponse` — 生成响应（report_id + form_answers + trace_id）

## 审计日志

所有状态变更操作（创建/提交/审核/关闭/重开/删除）都会自动记录审计日志，包含：
- `action` — 操作类型（created/submitted/approved/rejected/closed/reopened/deleted/assigned/migrated）
- `actor_id` — 操作人
- `from_status` / `to_status` — 状态变更
- `comment` — 操作备注

## 数据库迁移

### 新表结构

| 表名 | 说明 |
|------|------|
| `incident_reports` | 报告主表（含 form_data JSONB） |
| `incident_audit_logs` | 审计日志 |
| `incident_comments` | 评论 |
| `incident_report_roles` | 角色分配（复合主键 user_id + role） |

### 旧表迁移

迁移脚本 `b2c3d4e5f6a7_migrate_legacy_sessions.py` 将 `incident_report_sessions` 数据迁移到 `incident_reports`：
- 自动创建 `usr_migrated` 虚拟用户
- `generated` 状态映射为 `approved`
- 审计日志 ID 使用 `md5()` 哈希以适配 `varchar(32)` 限制

## 跨域依赖

- `skill.service.tool_loop` — 工具执行循环
- `skill.service.context` — 上下文检索
- `chat.models.attachment` — 附件类型
- `core.ollama` — Ollama 调用
- `core.config` — 配置（含 BACKEND_DIR）
- `core.security` — JWT 认证 + 用户 ID 提取

## 开发注意

- 表单 Schema 定义在 `service/form_schema.py`（4 步骤：basic_info/description/timeline/appendix）
- 生成脚本在 `skills/incident-report/scripts/generate_incident_report.py`
- 报告数据存储在 PostgreSQL，使用 `report_store.py`
- 预览支持 HTML、DOCX、PDF 三种格式
- 不要在 `router/` 中写业务逻辑，所有编排逻辑放 `service/`
- `update_report_record` 使用 `_CLEAR_SENTINEL` 标记需要清空的字段（如 reopen 时 `closed_at=None`）
- 角色校验使用 `field_validator` 确保只接受 `VALID_ROLES` 中的值
