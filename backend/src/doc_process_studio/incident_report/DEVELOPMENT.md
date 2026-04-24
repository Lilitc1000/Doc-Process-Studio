# Incident Report 业务域开发指南

## 概述

Incident Report 域负责事故报告的结构化生成，包括表单交互、AI 生成正文、预览和翻译。

## 目录结构

```text
backend/src/doc_process_studio/incident_report/
├── router/
│   └── incident_reports.py  # 事故报告全部 API 端点
├── service/
│   ├── session.py           # 会话 CRUD
│   ├── session_store.py     # Redis 会话存储实例
│   ├── generation.py        # AI 生成正文（一键 / 分段）
│   ├── preview.py           # HTML 预览 + DOCX/PDF 导出
│   ├── translation.py       # 多语言翻译
│   ├── report_data.py       # 表单数据 → report_data 转换
│   └── reference.py         # Skill 参考文档加载
├── models/
│   └── incident_report.py   # 所有 Pydantic 模型
└── schemas/
    ├── request.py           # 入参模型
    ├── response.py          # 出参模型
    └── common.py            # 共享基类
```

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/incident-report/schema` | 获取表单 Schema |
| GET | `/api/incident-report/sessions` | 获取会话列表 |
| POST | `/api/incident-report/sessions` | 创建新会话 |
| GET | `/api/incident-report/sessions/{id}` | 获取会话详情 |
| PUT | `/api/incident-report/sessions/{id}` | 保存会话快照 |
| PATCH | `/api/incident-report/sessions/{id}/title` | 修改会话标题 |
| DELETE | `/api/incident-report/sessions/{id}` | 删除会话 |
| POST | `/api/incident-report/sessions/{id}/body/quick-generate` | 一键生成正文 |
| POST | `/api/incident-report/sessions/{id}/body/section-generate` | 分段生成正文 |
| POST | `/api/incident-report/sessions/{id}/preview` | 预览/导出 |

## 核心流程

1. 前端获取表单 Schema（`GET /schema`），渲染交互式表单
2. 用户填写表单后，前端保存快照（`PUT /sessions/{id}`）
3. 用户点击"一键生成"或"分段生成"，后端调用 Skill 工具
4. Skill 工具执行 `generate_incident_report.py` 脚本，生成 DOCX
5. 前端请求预览（`POST /preview`），后端返回 HTML + 可选 DOCX/PDF
6. 用户可下载最终文档

## 跨域依赖

- `skill.service.tool_loop` — 工具执行循环（子包）
- `skill.service.context` — 上下文检索
- `chat.models.attachment` — 附件类型
- `core.ollama` — Ollama 调用
- `core.config` — 配置（含 BACKEND_DIR）

## 开发注意

- 表单 Schema 来自 `skills/incident-report/agents/openai.yaml`
- 生成脚本在 `skills/incident-report/scripts/generate_incident_report.py`
- 会话数据存储在 Redis，使用 `session_store.py` 中的实例
- 预览支持 HTML、DOCX、PDF 三种格式
- 不要在 `router/` 中写业务逻辑，所有编排逻辑放 `service/`
