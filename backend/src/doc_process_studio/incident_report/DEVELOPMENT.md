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
│   ├── incident_report_role.py # RBAC ORM（角色定义、用户-角色、权限定义、角色-权限）
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
| POST | `/api/incident-report/reports/{id}/body/quick-generate` | 快填 AI 一键生成正文 |
| POST | `/api/incident-report/reports/{id}/body/section-generate` | 分段 AI 生成正文段落 |
| POST | `/api/incident-report/reports/{id}/preview` | 生成 PDF/DOCX 预览 |

### 角色管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/incident-report/roles/me` | 当前用户角色和权限 |
| GET | `/api/incident-report/roles` | 全部角色分配（管理员） |
| POST | `/api/incident-report/roles` | 分配角色（管理员） |
| DELETE | `/api/incident-report/roles/{userId}/{role}` | 撤销角色（管理员） |
| GET | `/api/incident-report/role-definitions` | 角色定义列表（含权限） |
| GET | `/api/incident-report/permissions` | 权限定义列表 |

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

## 权限模型（RBAC）

系统采用 RBAC（基于角色的访问控制）模型，通过 用户 → 角色 → 权限 三层关系实现细粒度权限管理。

### 角色定义

| 角色 | role_key | 说明 |
|------|----------|------|
| 管理员 | `admin` | 所有权限 + 角色分配 + 系统配置 + 数据导出 |
| 审核人 | `verifier` | 审核待审核报告、查看所有报告、分配处理人 |
| 处理人 | `handler` | 查看分配给自己的报告、更新处理进度、关闭报告 |
| 报告人 | `reporter` | 创建报告、编辑自己的草稿/被驳回报告、提交审核 |
| 观察者 | `viewer` | 仅查看报告列表和详情，无操作权限 |

### 权限定义

| 权限 | permission_key | 分类 |
|------|----------------|------|
| 创建报告 | `report:create` | report |
| 编辑自己的报告 | `report:edit_own` | report |
| 提交审核 | `report:submit` | report |
| 查看报告 | `report:view` | report |
| 查看所有报告 | `report:view_all` | report |
| 编辑被指派的报告 | `report:edit_assigned` | report |
| 关闭被指派的报告 | `report:close_assigned` | report |
| 审核报告 | `report:audit` | report |
| 分配处理人 | `report:assign` | report |
| 删除报告 | `report:delete` | report |
| 重新打开报告 | `report:reopen` | report |
| 角色管理 | `role:manage` | role |
| 系统配置 | `system:config` | system |
| 数据导出 | `data:export` | data |
| 查看统计分析 | `analytics:view` | analytics |

### 角色-权限映射

| 权限 | viewer | reporter | handler | verifier | admin |
|------|--------|----------|---------|----------|-------|
| report:view | ✓ | ✓ | ✓ | ✓ | ✓ |
| report:create | | ✓ | | | ✓ |
| report:edit_own | | ✓ | | | ✓ |
| report:submit | | ✓ | | | ✓ |
| report:view_all | | | ✓ | ✓ | ✓ |
| report:edit_assigned | | | ✓ | | ✓ |
| report:close_assigned | | | ✓ | | ✓ |
| report:audit | | | | ✓ | ✓ |
| report:assign | | | | ✓ | ✓ |
| report:delete | | | | | ✓ |
| report:reopen | | | | | ✓ |
| role:manage | | | | | ✓ |
| system:config | | | | | ✓ |
| data:export | | | | | ✓ |
| analytics:view | ✓ | ✓ | ✓ | ✓ | ✓ |

### 数据库表

| 表名 | 说明 |
|------|------|
| `incident_report_role_definitions` | 角色定义（role_key 主键） |
| `incident_report_user_roles` | 用户-角色关联（user_id + role_key 唯一约束） |
| `incident_report_permissions` | 权限定义（permission_key 主键） |
| `incident_report_role_permissions` | 角色-权限关联（role_key + permission_key 复合主键） |

### 初始化

应用启动时自动执行：
1. `seed_rbac_data()` — 初始化角色定义、权限定义和角色-权限映射
2. `ensure_incident_report_admin()` — 确保系统管理员拥有事故报告管理员角色

权限依赖定义在 `router/dependencies.py` 中，通过 `has_permission` / `has_any_permission` 实现权限检查。

## 正文生成链路

### API 端点

| 端点 | 说明 |
|------|------|
| `POST /reports/{id}/body/quick-generate` | 快填模式一键生成完整正文 |
| `POST /reports/{id}/body/section-generate` | 分段生成指定正文段落 |
| `POST /reports/{id}/preview` | 生成 PDF/DOCX 预览 |

### 快填生成流程

1. 前端调用 `quick-generate`，传入 model/reranker_model（可选）
2. 后端从 `form_data` 构建 `IncidentFormSnapshot`
3. 调用 AI 模型生成完整正文 JSON（description, timeline, impact, root_cause, follow_up）
4. `_apply_quick_generation_payload` 将生成结果回填到 form_answers
5. 通过 `update_report_record` 持久化到数据库
6. 返回 `IncidentBodyGenerateResponse`（含 form_answers + trace_id）

### 分段生成流程

1. 前端调用 `section-generate`，传入 section_id（description/timeline/impact/root_cause/follow_up/timeline_item）和可选的 timeline_index
2. 后端构建对应段落的 prompt 和 context
3. 调用 AI 模型生成该段落 JSON
4. `_apply_section_payload` 将生成结果回填到对应字段
5. 返回 `IncidentBodyGenerateResponse`

### 预览流程

1. 前端调用 `preview`，传入 version（可选）
2. 后端从 `form_data` 构建 snapshot → report_data
3. 调用 DOCX 模板生成 DOCX 字节
4. 通过 LibreOffice 转换为 PDF
5. 通过 mammoth 转换为 HTML
6. 返回 `IncidentReportPreviewResponse`（含 html + pdfBase64 + docxBase64）
7. 预览结果缓存（最多 12 条，LRU）

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

## 数据模型

| 表名 | 说明 |
|------|------|
| `incident_reports` | 报告主表（含 form_data JSONB） |
| `incident_audit_logs` | 审计日志 |
| `incident_comments` | 评论 |
| `incident_report_role_definitions` | 角色定义 |
| `incident_report_user_roles` | 用户-角色关联 |
| `incident_report_permissions` | 权限定义 |
| `incident_report_role_permissions` | 角色-权限关联 |

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
- 快填生成入口：`service/generation.py` → `quick_generate_report_body()`
- 分段生成入口：`service/generation.py` → `generate_report_body_section()`
- 预览入口：`service/preview.py` → `preview_report_attachment()`
- `_build_snapshot_from_form_data()` 将 form_data 转换为 IncidentFormSnapshot
- 不要在 `router/` 中写业务逻辑，所有编排逻辑放 `service/`
- `update_report_record` 使用 `_CLEAR_SENTINEL` 标记需要清空的字段（如 reopen 时 `closed_at=None`）
- 角色校验使用 `field_validator` 确保只接受 `VALID_ROLES` 中的值
- 权限检查使用 `has_permission(user_id, permission_key)` 和 `has_any_permission(user_id, permission_set)`
- 角色定义、权限定义和角色-权限映射在应用启动时通过 `seed_rbac_data()` 自动初始化
