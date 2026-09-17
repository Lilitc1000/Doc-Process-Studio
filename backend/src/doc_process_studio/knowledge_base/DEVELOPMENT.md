# KnowledgeBase 业务域开发文档

## 概述

知识库子系统提供项目级别的文档管理与 RAG 检索能力。

**RAGFlow 是唯一真相源**：应用里的"项目"就是 RAGFlow 的 **dataset**，文件夹与文档全部由
RAGFlow 派生，**本地不保存任何知识库业务数据**（无 kb_* 表、无原文件落盘）。
上传的文件字节直接转给 RAGFlow，由服务端完成解析、切块与向量化。

这样做解决的历史问题：过去"PostgreSQL 一套目录 + RAGFlow 一套目录靠项目名映射对齐"，
改名或未映射就会错位；现在读到什么就是 RAGFlow 里有什么。

## 目录结构

KnowledgeBase 域采用 DDD 四层架构（端口与适配器模式）：

```text
knowledge_base/
├── domain/                      # 领域层：领域异常
│   └── errors.py                # KnowledgeBaseError / ProjectNotFoundError / DocumentNotFoundError / ...
├── application/                 # 应用层：用例编排 + 端口 + DTO
│   ├── ports.py                 # KnowledgeBaseRepository（结构 + 文档 + 检索的唯一端口）
│   ├── dtos/
│   │   └── __init__.py          # KBIndexHit / KBIndexResult
│   └── kb_service.py            # KnowledgeBaseService（用例编排）
├── infrastructure/              # 基础设施层：端口实现 + 依赖装配 + 技术工具
│   ├── ragflow_client.py        # RAGFlow HTTP 客户端（所有读写的唯一出口）
│   ├── ragflow_repository.py    # RagflowKnowledgeBaseRepository（映射 + Redis 缓存）
│   ├── kb_skill.py              # 知识库 RAG 提示词
│   ├── parsing.py               # 文件类型识别（交 RAGFlow 前判断类型/压缩包）
│   ├── parser/                  # 压缩包展开（ZIP/RAR/7z）
│   │   ├── __init__.py
│   │   └── archive.py
│   └── dependencies.py          # 依赖装配（get_ragflow_client / get_kb_repository / get_kb_service）
└── router/                      # 用户接口层：API 端点 + 请求/响应 Schema
    ├── projects.py              # API 路由（依赖注入 KnowledgeBaseService）
    └── schemas/                 # HTTP DTO
        ├── request.py           # 入参 Pydantic 模型
        └── response.py          # 出参 Pydantic 模型
```

### 分层依赖规则

- **domain** 不依赖任何其他层，只包含领域异常定义。
- **application** 只依赖 domain + 端口抽象；允许引用公共配置（如上传大小限制），
  但**不得 import 本模块的 infrastructure**（由 `tests/knowledge_base/unit/test_kb_decoupling.py` 守着）。
- **infrastructure** 实现端口：RAGFlow 调用集中在 `ragflow_client.py`，
  只有 `ragflow_repository.py` 与 `dependencies.py` 可以引用它。
- **router** 通过 `Depends(get_kb_service)` 注入应用服务；本模块**没有数据库事务**，
  写操作的成败以 RAGFlow 返回结果为准。

### 依赖注入

`infrastructure/dependencies.py` 用 `@lru_cache(maxsize=1)` 装配单例：
`RagflowClient` → `RagflowKnowledgeBaseRepository`（带缓存 TTL）→ `KnowledgeBaseService`。
测试时用 `app.dependency_overrides[get_kb_service]` 替换即可。

## 数据映射

| 应用侧概念 | RAGFlow | 备注 |
|---|---|---|
| 项目 `KBProjectResponse.id` | dataset id | `$` 提及里携带的就是它 |
| 文件夹 `KBTreeNodeFolder` | dataset 内的 folder | **只读**：本版本接口无 POST/DELETE |
| 文档 `KBDocumentResponse.id` | dataset 内的 document id | 上传后由 RAGFlow 返回 |

**文件夹是否存在的判定**（无需本地标志位）：
`GET /api/v1/datasets/{id}/documents/folders` 返回 `code=0` 表示有文件夹，
返回 `code=102 "The dataset not own the document folders."` 表示没有——
仓储把它翻译成空列表，调用方只管渲染：有文件夹就是树，没有就是扁平文档列表。

## 缓存与双向一致性

RAGFlow 是**外部真相源**：用户在 RAGFlow 网页端新建 / 删除 dataset 或文档时不会通知
本服务，缓存会让应用与 RAGFlow 短暂不一致。因此策略是：

- **dataset 列表（= 项目清单）永不缓存**。它决定"有哪些项目"，是路由与选择的依据，
  必须每次直连 RAGFlow（`RagflowKnowledgeBaseRepository._datasets()`）。
  这样 RAGFlow 侧的增删在下一次请求即可见。
- **folder / document 列表**可按 `KB_CACHE_TTL_SECONDS` 缓存，**默认 `0`（不缓存）**
  以保证强一致；需要减轻 RAGFlow 压力时可设为 10~60 秒。

| 缓存键 | 内容 | 失效时机 |
|---|---|---|
| `kb:ds:{id}:folders` | 该 dataset 的文件夹 | 上传 / 删除文档 |
| `kb:ds:{id}:documents` | 该 dataset 的文档 | 上传 / 删除文档 |

本服务自己的写操作（建 / 改名 / 删项目、上传 / 删文档）成功后会立即失效对应键；
**Redis 不可用时自动降级为直连 RAGFlow**——`common/infrastructure/cache.py`
会吞掉缓存异常，不让它打断业务。

> 取舍：若把 TTL 调大，RAGFlow 侧的改动最多会延迟 TTL 秒才可见。需要"即时一致"
> 就保持 `KB_CACHE_TTL_SECONDS=0`。

## 分层纪律

结构形状（项目 / 文档 / 树节点）定义在**应用层** `application/dtos/`：
`KBProject`、`KBDocument`、`KBTreeNodeFolder/Document`、`KBProjectSimpleItem`、`KBProjectTree`。

- `application/` 与 `infrastructure/` **只依赖 `application.dtos`**，
  **不得**反向 import `router.schemas`——否则会形成
  `ports -> router -> kb_service -> ports` 的循环导入（曾因此导致单独 import 仓储即报错）。
- `router/schemas/response.py` 只做 API 包装（`KBProjectListResponse`、`KBTreeResponse` 等）
  并把应用层类型以旧名再导出（`KBProjectResponse = KBProject`），API 契约保持不变。
- 服务层返回应用层形状，由路由层包装成响应模型。

## API 路由

所有路由均声明 `response_model`，确保返回数据符合 Pydantic Schema。

| 方法 | 路径 | 说明 | response_model |
|------|------|------|----------------|
| GET | `/knowledge-base/projects` | 列出所有项目（= dataset 列表） | `KBProjectListResponse` |
| POST | `/knowledge-base/projects` | 创建项目（在 RAGFlow 建 dataset） | `KBProjectResponse` |
| GET | `/knowledge-base/projects/{id}` | 获取项目详情 | `KBProjectResponse` |
| PUT | `/knowledge-base/projects/{id}/rename` | 重命名项目 | `KBProjectResponse` |
| DELETE | `/knowledge-base/projects/{id}` | 删除项目（连同 dataset） | 204 |
| GET | `/knowledge-base/projects-simple` | 简要列表（供对话 `$` 选择器使用） | `KBProjectListSimpleResponse` |
| GET | `/knowledge-base/projects/{id}/tree` | 获取项目树（无文件夹时为扁平列表） | `KBTreeResponse` |
| POST | `/knowledge-base/projects/{id}/documents/upload` | 上传文档并触发解析 | `KBDocumentResponse` |
| DELETE | `/knowledge-base/documents/{id}` | 删除文档 | 204 |

> 文件夹写接口（建 / 改名 / 删）已移除——RAGFlow 本版本不支持在 dataset 内新建或删除文件夹。

## RAGFlow 接口对照

| 能力 | 请求 |
|---|---|
| 列出 / 新建 / 改名 / 删除 dataset | `GET|POST|PUT|DELETE /api/v1/datasets` |
| 列出 dataset 内文件夹 | `GET /api/v1/datasets/{id}/documents/folders` |
| 列出 / 上传 / 删除文档 | `GET|POST|DELETE /api/v1/datasets/{id}/documents` |
| 触发解析 | `POST /api/v1/datasets/{id}/chunks` |
| 检索 | `POST /api/v1/retrieval` |

**降级纪律（务必遵守）**：未配置 / `code != 0` / 网络异常一律记日志并返回空容器或
`False`，**绝不抛异常阻断上传、浏览或检索**。

## 相关配置

| 环境变量 | 默认值 | 说明 |
|---|---|---|
| `RAGFLOW_BASE_URL` | — | RAGFlow 服务地址 |
| `RAGFLOW_API_KEY` | — | API Key（生产须走环境变量注入） |
| `RAGFLOW_SIMILARITY_THRESHOLD` | `0.55` | 检索相似度阈值 |
| `RAGFLOW_TIMEOUT_SECONDS` | `15.0` | 常规请求超时 |
| `RAGFLOW_PARSE_TIMEOUT_SECONDS` | `60.0` | 触发服务端解析的超时 |
| `KB_SEARCH_TOP_K` | `6` | 检索返回条数 |
| `KB_CACHE_TTL_SECONDS` | `0` | 文档/目录列表缓存 TTL；`0` = 不缓存（强一致）。项目清单永不缓存 |
| `KB_MAX_UPLOAD_SIZE_BYTES` | 100MB | 上传大小限制 |
| `REDIS_URL` / `REDIS_PASSWORD` | — | 缓存后端；未配置时缓存降级为直连 |

## 上传流程

1. 校验大小（`KB_MAX_UPLOAD_SIZE_BYTES`）与扩展名（仅 pdf/doc/docx/xls/xlsx）。
2. 压缩包先用本地 `parser/archive.py` 展开，再逐成员上传（压缩包本身不落成文档）。
3. `POST /api/v1/datasets/{id}/documents` 上传 → `POST .../chunks` 触发解析。
4. 回读文档对象拿切块数，失效该 dataset 的文件夹 / 文档缓存。

> 解析是异步的：上传刚返回时 `chunk_count` 可能为 0，`is_indexed` 按切块数判断，
> 失败时保持"未索引"状态便于重试，但**不会**阻断上传主流程。

## Skill 集成

- Skill ID 格式：`kb:{dataset_id}`（`$` 提及里携带 dataset id，展示名仍用项目名）。
- 选中后自动注入 `search_knowledge_base` 工具，按 dataset 粒度检索。
- 检索结果字段：`content`（片段）、`source` / `file_name`（来源）、`document_id`、`score`。

上传大小限制：100MB。
