# Incident Report 业务域开发指南

## 概述

Incident Report 域负责事故报告的全生命周期管理，包括创建、编辑、审核、关闭、数据分析，以及 AI 生成正文和预览。

## 目录结构

事故报告域采用 DDD（领域驱动设计）四层架构：领域层 / 应用层 / 基础设施层 / 用户接口层。无独立的 models/ 或 schemas/ 顶层目录——ORM 模型归属基础设施层，DTO 按职责分布到各层。

```text
backend/src/doc_process_studio/incident_report/
├── domain/                       # 领域层：纯领域模型与规则，无框架依赖
│   ├── entities/                 # 聚合根/实体
│   │   ├── report.py             # Report 聚合根（状态、行为、事件）
│   │   └── status.py             # ReportStatus 值对象 + 状态机规则
│   ├── events/                   # 领域事件
│   │   └── events.py             # 领域事件类（ReportCreated/Submitted/...）
│   ├── values/                   # 值对象/常量/规则
│   │   ├── constants.py          # 领域常量（生成字段 key、文件路径、选项枚举等）
│   │   ├── errors.py             # 领域异常（DomainError/PermissionDeniedError/...）
│   │   ├── form_schema.py        # 表单 Schema 定义（4 步骤，INCIDENT_REPORT_FORM_SCHEMA）
│   │   ├── form_validation.py    # 表单字段校验规则
│   │   ├── permission.py         # Permission/Role 枚举 + 角色-权限映射 + 角色定义/权限定义常量
│   │   └── status_types.py       # IncidentReportStatus/IncidentSeverity 类型别名 + 校验集合
│   └── __init__.py               # re-export 所有公开名称
├── application/                  # 应用层：用例编排 + DTO + 端口抽象
│   ├── dtos/                     # 应用层数据传输对象（端口返回类型、跨层共享结构）
│   │   ├── form.py               # IncidentFormAnswer/IncidentFormSnapshot
│   │   ├── report.py             # IncidentReportSummary/Detail/AuditLogEntry/CommentEntry/ListResponse
│   │   ├── analytics.py          # IncidentAnalyticsOverview/IncidentAnalyticsTrend
│   │   └── role.py               # IncidentRoleEntry/RoleDefinitionEntry/PermissionEntry + 列表响应
│   ├── services/                 # 用例服务
│   │   ├── report_service.py     # ReportApplicationService（报告用例）
│   │   ├── audit_query_service.py # AuditQueryService（审计日志查询用例）
│   │   ├── comment_service.py    # CommentService（评论用例）
│   │   ├── analytics_service.py  # AnalyticsService（统计分析用例）
│   │   ├── role_service.py       # RoleService（角色管理用例）
│   │   ├── generation_service.py # GenerationService（AI 正文生成用例）
│   │   └── preview_service.py    # PreviewService（预览用例）
│   ├── ports/                    # 出站端口接口
│   │   ├── ports.py              # ReportRepository/PermissionChecker/LLMStreamingPort/...
│   │   ├── analytics_ports.py    # AnalyticsRepository 端口
│   │   └── role_ports.py         # RoleRepository 端口
│   ├── commands.py               # 用例命令对象（CreateReportCommand/...）
│   └── __init__.py               # re-export 所有 DTO、端口和服务
├── infrastructure/               # 基础设施层：端口实现 + ORM + 纯技术工具
│   ├── persistence/              # ORM 模型（数据库映射）
│   │   ├── incident_report_orm.py # IncidentReport + IncidentComment ORM
│   │   ├── incident_report_role.py # RBAC ORM（角色定义、用户-角色、权限定义、角色-权限）
│   │   └── audit_log.py          # IncidentAuditLog ORM
│   ├── repositories/             # 仓储实现
│   │   ├── report_repository.py  # SqlAlchemyReportRepository + SqlUserDirectory + RefNoGenerator
│   │   ├── audit_log_repository.py # SqlAuditLogRepository
│   │   ├── audit_event_sink.py   # SqlAuditEventSink（事件落库）
│   │   ├── comment_repository.py # SqlCommentRepository
│   │   ├── analytics_repository.py # SqlAnalyticsRepository
│   │   ├── role_repository.py    # SqlRoleRepository
│   │   └── orm_mappers.py        # ORM ↔ 领域模型映射
│   ├── adapters/                 # 外部服务适配器
│   │   ├── llm_streaming.py      # OllamaLLMStreaming（LLM 流式调用端口实现）
│   │   ├── trace_recorder.py     # SystemTraceRecorder（追踪记录器端口实现）
│   │   ├── reference_context.py  # SkillReferenceContext（参考文档选择端口实现）
│   │   ├── document_assistant.py # SkillDocumentAssistant（文档助手端口实现）
│   │   └── attachment_store.py   # ChatAttachmentStore（附件存储端口实现）
│   ├── utils/                    # 纯技术工具函数（无业务逻辑，无状态）
│   │   ├── normalization.py      # 文本归一化工具
│   │   ├── report_data.py        # 表单数据 → report_data 转换
│   │   ├── generation.py         # AI 生成提示词构建、payload 回填
│   │   └── preview.py            # DOCX/PDF 渲染、缓存、附件管理
│   ├── permission_checker.py     # RbacPermissionChecker
│   ├── permission_helper.py      # 权限检查辅助函数
│   └── dependencies.py           # FastAPI 依赖装配（get_*_service/get_*_port 工厂）
└── router/                       # 用户接口层：HTTP 端点 + 请求/响应 DTO
    ├── schemas/                  # HTTP DTO（仅用户接口层使用）
    │   ├── common.py             # PaginationParams
    │   ├── request.py            # 入参模型（CreateRequest/UpdateRequest/...）
    │   └── response.py           # 出参模型（re-export application/dtos/，供 router 作为 response_model）
    ├── reports.py                # 报告 CRUD + 状态流转 + 评论 + 生成 + 预览 API
    ├── roles.py                  # 角色管理 API
    ├── analytics.py              # 数据分析 API
    └── dependencies.py           # 权限依赖（require_admin）
```

### 分层依赖规则

- **domain（领域层）** 不依赖任何其他层，只包含纯领域逻辑（entities/events/values 子包，常量、规则、类型定义）
- **application（应用层）** 依赖 domain + 自身端口（ports/）和 DTO（dtos/），不依赖 infrastructure 具体实现和 ORM 模型
- **infrastructure（基础设施层）** 实现 application 定义的端口（repositories/ 仓储实现、adapters/ 外部服务适配器），包含 ORM 模型（persistence/）和纯技术工具函数（utils/）
- **router（用户接口层）** 依赖 application 服务和 DTO，通过 `infrastructure/dependencies.py` 注入；请求/响应模型放在 router/schemas/ 中

### DTO 分层规范

- **application/dtos/** — 应用层数据传输对象，包括端口返回类型、跨层共享结构。端口（ports/）的方法签名使用 dtos/ 中的类型，不返回 ORM 对象
- **router/schemas/request.py** — HTTP 请求入参模型，仅 router 层使用
- **router/schemas/response.py** — HTTP 响应出参模型，re-export application/dtos/ 中的类型供 FastAPI response_model 使用
- **domain/values/** — 领域类型定义（IncidentReportStatus/IncidentSeverity 等 Literal 类型、Permission 枚举等），供 application 和 infrastructure 引用

### 依赖注入

所有应用服务通过 `infrastructure/dependencies.py` 中的工厂函数装配，使用 `@lru_cache(maxsize=1)` 实现单例：

```python
# router 中通过 Depends 注入
@router.get("/reports/{id}")
async def get_report(
    report_id: str,
    user_id: str = Depends(get_current_user_id),
    service: ReportApplicationService = Depends(get_report_application_service),
):
    ...
```

测试时通过 `app.dependency_overrides[get_*_service]` 替换为 mock，无需 patch 模块路径。

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
| GET | `/api/incident-report/users-with-roles` | 非admin用户及角色列表（管理员） |
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

状态机规则集中定义在 `domain/entities/status.py` 中：
- `ReportStatus` 枚举封装所有合法状态
- `STATUS_TRANSITIONS` 定义每个状态允许的下一状态集合
- `ReportStatus.can_transition_to(target)` 提供状态转换校验

聚合根 `domain/entities/report.py` 的 `Report` 类封装所有状态转换行为（submit/approve/reject/assign/close/reopen），每次转换：
1. 校验当前状态是否允许转换（调用 `ReportStatus.can_transition_to`）
2. 更新状态字段
3. 计算副作用字段（如 `submitted_at`/`approved_at`/`closed_at` 等时间戳）
4. 生成对应的领域事件（`ReportSubmitted`/`ReportApproved`/...），事件由 `ReportApplicationService` 通过 `AuditEventSink` 落库为审计日志

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
| 编辑所有报告 | `report:edit_all` | report |
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
| report:edit_all | | | | | ✓ |
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

应用启动时通过 `RoleRepository` 自动执行（见 `main.py`）：
1. `role_repo.seed_rbac_data()` — 初始化角色定义、权限定义和角色-权限映射
2. `role_repo.ensure_admin_role()` — 确保系统管理员拥有事故报告管理员角色

权限定义、角色定义和角色-权限映射作为领域知识定义在 `domain/values/permission.py` 中（`ROLE_DEFINITIONS` / `PERMISSION_DEFINITIONS` / `ROLE_PERMISSIONS`），`SqlRoleRepository.seed_rbac_data()` 读取这些常量写入数据库。

权限检查通过 `PermissionChecker` 端口抽象（`application/ports/`），由 `RbacPermissionChecker` 实现：
- `permissions_of(user_id)` 返回用户拥有的 `Permission` 枚举集合
- `require(user_id, permission)` 校验权限，不足抛 `PermissionDeniedError`

`router/dependencies.py` 中的 `require_admin` 通过 `PermissionChecker` 实现端点级权限守卫。

## 正文生成链路

### 语言策略

AI 生成固定输出英文。系统提示词中明确要求所有输出使用英文，无需语言检测、校验或翻译步骤。生成结果直接用于文档输出。

### API 端点

| 端点 | 说明 |
|------|------|
| `POST /reports/{id}/body/quick-generate` | 快填模式一键生成完整正文 |
| `POST /reports/{id}/body/section-generate` | 分段生成指定正文段落 |
| `POST /reports/{id}/preview` | 生成 PDF/DOCX 预览 |

### 快填生成流程

1. 前端调用 `quick-generate`，传入 model/reranker_model（可选）
2. 后端从 `form_data` 构建 `IncidentFormSnapshot`
3. 调用 AI 模型生成完整正文 JSON（description, timeline, impact, root_cause, follow_up），输出固定为英文
4. `_apply_quick_generation_payload` 将生成结果回填到 form_answers
5. 通过 `update_report_record` 持久化到数据库
6. 返回 `IncidentBodyGenerateResponse`（含 form_answers + trace_id）

### 分段生成流程

1. 前端调用 `section-generate`，传入 section_id（description/timeline/impact/root_cause/follow_up/timeline_item）和可选的 timeline_index
2. 后端构建对应段落的 prompt 和 context
3. 调用 AI 模型生成该段落 JSON，输出固定为英文
4. `_apply_section_payload` 将生成结果回填到对应字段
5. 返回 `IncidentBodyGenerateResponse`

时间线段落支持两种生成方式：
- `timeline`：一次性生成整条时间线（含 `body_timeline` 数组和 `body_affected_date_summary` 时间汇总）
- `timeline_item`：按单条时间线生成，需传入 `timeline_index` 指定目标条目索引，仅更新该条时间线内容

前端时间线区域采用按条生成模式：每条时间线行内有独立的 AI 生成按钮，调用 `timeline_item` + `timeline_index` 生成该条目。时间汇总字段（`body_affected_date_summary`）在时间线区域下方单独展示，可手动编辑或由 `timeline` 整段生成时自动填充。

### 预览流程

1. 前端调用 `preview`，传入 version（可选）
2. 后端从 `form_data` 构建 snapshot → report_data
3. 调用 DOCX 模板生成 DOCX 字节（report_data 已为英文，无需翻译）
4. 通过 LibreOffice 转换为 PDF
5. 返回 `IncidentReportPreviewResponse`（含 pdfBase64 + docxBase64）
6. 预览结果缓存（最多 12 条，LRU）

### 关键数据模型

- `IncidentFormAnswer` — 单个表单步骤的答案（value），定义在 `application/dtos/form.py`
- `IncidentFormSnapshot` — 完整表单快照（form_answers + report_data + trace 信息），定义在 `application/dtos/form.py`
- `IncidentBodyGenerateResponse` — 生成响应（report_id + form_answers + trace_id），定义在 `application/dtos/form.py`

## 审计日志

所有状态变更操作（创建/提交/审核/关闭/重开/删除/指派）通过领域事件驱动记录审计日志：

1. 聚合根 `Report` 在状态转换方法中生成领域事件（如 `ReportCreated`/`ReportSubmitted`/`ReportApproved`/`ReportRejected`/`ReportClosed`/`ReportReopened`/`HandlerAssigned`），事件类定义在 `domain/events/events.py`
2. `ReportApplicationService` 在用例执行后收集聚合根产生的事件
3. 通过 `AuditEventSink` 端口（`SqlAuditEventSink` 实现）将事件批量写入 `incident_audit_logs` 表
4. 每条审计日志包含：
   - `action` — 操作类型（created/submitted/approved/rejected/closed/reopened/deleted/assigned）
   - `actor_id` — 操作人
   - `from_status` / `to_status` — 状态变更
   - `comment` — 操作备注

审计日志查询通过 `AuditQueryService` → `AuditLogRepository` 端口（`SqlAuditLogRepository` 实现）。

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

跨域调用通过 application/ports/ 定义的端口抽象隔离，infrastructure 层提供具体适配实现（adapters/ 和 repositories/）。application 层不直接 import 其他域的 service/ 或 schemas/。

| 端口 | 实现类 | 封装的外部依赖 |
|------|--------|---------------|
| `LLMStreamingPort` | `OllamaLLMStreaming` | `common.infrastructure.ollama.stream_chat_completion` |
| `TraceRecorderPort` | `SystemTraceRecorder` | `system.infrastructure.trace_store.AgentTraceRecorder` |
| `ReferenceContextPort` | `SkillReferenceContext` | `skill.infrastructure.selector` / `skill.infrastructure.registry` |
| `DocumentAssistantPort` | `SkillDocumentAssistant` | `skill.infrastructure.registry.get_skill_interface` |
| `AttachmentStore` | `ChatAttachmentStore` | `chat.infrastructure.attachments` / `chat.application.dtos.attachment` |

其他跨域依赖（不走端口，供 infrastructure/utils/ 直接使用）：
- `chat.application.dtos.attachment` — 附件类型（供 infrastructure/utils/preview.py 使用）
- `chat.infrastructure.attachments` — 附件管理（供 infrastructure/utils/preview.py 使用）
- `common.infrastructure.config` — 配置（含 BACKEND_DIR）
- `common.security.security` — JWT 认证 + 用户 ID 提取

## 开发注意

### 分层规范

- 表单 Schema 定义在 `domain/values/form_schema.py`（4 步骤：basic_info/description/timeline/appendix），通过 `ReportApplicationService.get_form_schema()` 暴露给 router
- 领域常量定义在 `domain/values/constants.py`（生成字段 key、文件路径、选项枚举等）
- 领域类型定义在 `domain/values/status_types.py`（IncidentReportStatus/IncidentSeverity 类型别名 + 校验集合）
- 权限与角色定义在 `domain/values/permission.py`（Permission/Role 枚举 + 角色-权限映射 + 角色定义/权限定义常量）
- 应用层 DTO 定义在 `application/dtos/`：`form.py`（表单快照/生成响应）、`report.py`（报告摘要/详情/列表响应）、`analytics.py`（分析数据）、`role.py`（角色/权限条目）
- HTTP 请求模型定义在 `router/schemas/request.py`，响应模型定义在 `router/schemas/response.py`（re-export application/dtos/）
- ORM 模型定义在 `infrastructure/persistence/`（incident_report_orm.py、incident_report_role.py、audit_log.py）
- 纯技术工具函数放在 `infrastructure/utils/`：`normalization.py`（文本归一化）、`report_data.py`（数据转换）、`generation.py`（提示词构建/payload 回填）、`preview.py`（DOCX/PDF 渲染/缓存）
- 生成脚本在 `skills/incident-report/scripts/generate_incident_report.py`
- 报告数据存储在 PostgreSQL，通过 `infrastructure/repositories/report_repository.py` 的 `SqlAlchemyReportRepository` 访问
- 预览支持 DOCX、PDF 两种格式
- AI 生成固定输出英文，系统提示词中包含 "All output must be in English" 指令
- 快填生成入口：`application/services/generation_service.py` → `GenerationService.quick_generate()`
- 分段生成入口：`application/services/generation_service.py` → `GenerationService.generate_section()`
- 预览入口：`application/services/preview_service.py` → `PreviewService.preview_report()`
- **不要在 `router/` 中写业务逻辑**，所有编排逻辑放 `application/` 层服务
- **领域逻辑（状态转换、副作用字段计算、事件生成）必须封装在 `domain/entities/report.py` 的 `Report` 聚合根中**，应用层只做编排
- **新增用例时**：在 `application/` 创建服务类 + 端口（如需），在 `infrastructure/` 实现端口，在 `infrastructure/dependencies.py` 装配，在 `router/` 通过 `Depends` 注入
- **跨域调用必须通过端口抽象**，application 层不直接 import 其他域的 service/ 或 schemas/；infrastructure 层的 utils/ 和端口实现可引用其他域的 service/ 作为适配

### 权限检查

- 权限检查通过 `PermissionChecker` 端口（`application/ports/`）抽象，由 `RbacPermissionChecker` 实现
- 应用层使用 `checker.require(user_id, Permission.XXX)` 校验权限，不足抛 `PermissionDeniedError`
- `router/dependencies.py` 的 `require_admin` 通过 `PermissionChecker` 实现端点级守卫
- `PermissionDeniedError`（定义在 `domain/values/errors.py`）用于权限不足的场景，与业务校验错误 `ValueError` 区分

### 异常映射

- 领域异常 `DomainError` 及其子类（`PermissionDeniedError`/`ReportNotFoundError`/`InvalidStateTransitionError`/...）定义在 `domain/values/errors.py`
- `router/reports.py` 的 `_handle_domain_error` / `_handle_service_error` 负责将领域异常映射为 HTTP 状态码：
  - `PermissionDeniedError` → 403
  - `ReportNotFoundError` → 404
  - 其他 `DomainError` → 400

### 测试规范

- 单元测试位于 `tests/incident_report/unit/`，测试领域层（聚合根、状态机、权限）和应用层服务
- 集成测试位于 `tests/incident_report/integration/`，通过 FastAPI `TestClient` + `dependency_overrides` 测试端点
- **测试中 mock 应用服务时使用 `app.dependency_overrides[get_*_service] = lambda: fake_service`**，不要 patch 模块路径
- 各接口的权限检查规则：

| 接口 | 权限要求 | 说明 |
|------|----------|------|
| `GET /reports` | `report:view` + 数据过滤 | 无 `report:view_all` 则只返回自己参与的报告 |
| `GET /reports/{id}` | `report:view` + 数据过滤 | 无 `report:view_all` 则只能查看自己参与的报告 |
| `POST /reports` | `report:create` | 创建报告需要报告人权限 |
| `PUT /reports/{id}` | `report:edit_own` / `report:edit_assigned` / `report:edit_all` | 报告人编辑自己的、处理人编辑被指派的、管理员编辑所有 |
| `DELETE /reports/{id}` | `report:delete` | 删除报告需要管理员权限 |
| `POST /reports/{id}/submit` | `report:submit` | 提交审核需要报告人权限 |
| `POST /reports/{id}/approve` | `report:audit` | 审核通过需要审核人权限 |
| `POST /reports/{id}/reject` | `report:audit` | 驳回需要审核人权限 |
| `POST /reports/{id}/assign` | `report:assign` | 分配处理人需要审核人权限 |
| `POST /reports/{id}/close` | `report:close_assigned` | 关闭报告需要处理人权限 |
| `POST /reports/{id}/reopen` | `report:reopen` | 重新打开需要管理员权限 |
| `POST /reports/{id}/body/quick-generate` | 编辑权限（同 PUT） | 生成操作需要报告编辑权限 |
| `POST /reports/{id}/body/section-generate` | 编辑权限（同 PUT） | 分段生成需要报告编辑权限 |
| `POST /reports/{id}/preview` | 查看权限（同 GET） | 预览需要报告查看权限 |
| `GET /reports/{id}/audit-logs` | 查看权限（同 GET） | 审计日志需要报告查看权限 |
| `GET /reports/{id}/comments` | 查看权限（同 GET） | 评论列表需要报告查看权限 |
| `POST /reports/{id}/comments` | `report:view` | 添加评论需要报告查看权限 |
| `GET /analytics/overview` | `analytics:view` | 统计分析需要查看权限 |
| `GET /analytics/trend` | `analytics:view` | 趋势分析需要查看权限 |
- 角色定义、权限定义和角色-权限映射作为领域知识定义在 `domain/values/permission.py`，应用启动时通过 `SqlRoleRepository.seed_rbac_data()` 自动初始化
- `seed_rbac_data()` 支持增量更新：当数据库已有角色数据时，仅添加新增的权限定义和角色-权限映射，不会覆盖现有数据
- 严重级别映射：系统中报告的 severity 字段使用 P0/P1/P2/P3 分级，而 DOCX 文档模板使用 Not Applicable/Minor/Major 三级分类。`normalize_severity_option()` 负责将 P0/P1 映射为 major，P2/P3 映射为 minor，其他值映射为 not_applicable
