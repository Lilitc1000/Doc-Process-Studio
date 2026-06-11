# KnowledgeBase 业务域开发文档

## 概述

知识库子系统提供项目级别的文档管理能力，支持文件夹层级结构、多格式文档上传（PDF/Word/Excel/压缩包），以及基于 Qdrant 向量数据库的增量索引与 RAG 检索。

## 目录结构

```text
knowledge_base/
├── __init__.py
├── models/
│   ├── __init__.py
│   └── knowledge_base_orm.py    # KBProject, KBFolder, KBDocument ORM 模型
├── schemas/
│   ├── __init__.py
│   ├── common.py                # KBChunkPayload 等共享类型
│   ├── request.py               # 请求 Pydantic 模型
│   └── response.py              # 响应 Pydantic 模型
├── router/
│   ├── __init__.py
│   └── projects.py              # API 路由（项目/文件夹/文档/更新）
└── service/
    ├── __init__.py
    ├── documents.py             # 文档上传、解析、索引编排
    ├── folders.py               # 文件夹 CRUD 与树形结构构建
    ├── projects.py              # 项目 CRUD
    ├── kb_update.py             # 增量更新知识库（向量化 + 入库）
    ├── kb_skill.py              # 知识库虚拟 Skill 提示词与工具定义
    ├── chunker.py               # 文本分块器
    ├── embedding.py             # Ollama 文本向量化
    ├── qdrant_service.py        # Qdrant 向量操作（upsert/search/delete）
    └── parser/
        ├── __init__.py
        ├── pdf_parser.py        # PDF 解析
        ├── docx_parser.py       # Word 解析
        ├── xlsx_parser.py       # Excel 解析
        └── archive.py           # 压缩包解析（ZIP/RAR/7z）
```

## 核心模型

### KBProject（知识库项目）

- 一级目录，代表一个项目
- 记录文档数量、文件夹数量、更新状态
- `is_updating` 标记当前是否正在更新向量索引

### KBFolder（文件夹）

- 支持多级嵌套（`parent_id` 自引用）
- `path` 字段存储完整路径（如 `项目名/子文件夹`）
- 删除时级联删除子文件夹和关联文档

### KBDocument（文档）

- 支持版本管理（`version` + `is_latest`）
- `content_hash` 用于去重检测
- `is_indexed` 标记是否已写入向量数据库
- `file_type` 区分 pdf/docx/xlsx/archive

## API 路由

所有路由均声明 `response_model` 参数，确保返回数据符合 Pydantic Schema 定义。

| 方法 | 路径 | 说明 | response_model |
|------|------|------|----------------|
| GET | `/knowledge-base/projects` | 列出所有项目 | `KBProjectListResponse` |
| POST | `/knowledge-base/projects` | 创建项目 | `KBProjectResponse` |
| GET | `/knowledge-base/projects/{id}` | 获取项目详情 | `KBProjectResponse` |
| PUT | `/knowledge-base/projects/{id}/rename` | 重命名项目 | `KBProjectResponse` |
| DELETE | `/knowledge-base/projects/{id}` | 删除项目 | `KBMessageResponse` |
| GET | `/knowledge-base/projects-simple` | 简要项目列表（供 $ 选择器使用） | `KBProjectListSimpleResponse` |
| POST | `/knowledge-base/projects/{id}/folders` | 创建文件夹 | `KBFolderResponse` |
| PUT | `/knowledge-base/folders/{id}/rename` | 重命名文件夹 | `KBFolderResponse` |
| DELETE | `/knowledge-base/folders/{id}` | 删除文件夹 | `KBMessageResponse` |
| GET | `/knowledge-base/projects/{id}/tree` | 获取项目树形结构 | `KBTreeResponse` |
| POST | `/knowledge-base/projects/{id}/documents/upload` | 上传文档 | `KBDocumentResponse` |
| DELETE | `/knowledge-base/documents/{id}` | 删除文档 | `KBMessageResponse` |
| POST | `/knowledge-base/projects/{id}/update` | 触发增量更新 | `KBUpdateStatusResponse` |
| GET | `/knowledge-base/projects/{id}/status` | 查询更新状态 | `KBUpdateStatusResponse` |

## 向量数据库

- 使用 Qdrant 作为向量数据库，集合名由 `KB_COLLECTION_NAME` 配置
- 集合在应用启动时通过 `lifespan` 自动创建（如不存在）
- 所有项目共享同一集合，通过 `project_name` 元数据字段过滤
- 向量维度 768，使用 COSINE 距离
- Payload 索引字段：`project_name`、`document_id`、`is_latest`、`file_type`、`content_type`

### KBChunkPayload 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `project_name` | str | 所属项目名 |
| `document_id` | str | 文档 ID |
| `file_name` | str | 原始文件名 |
| `file_path` | str | 文件夹路径 |
| `file_type` | str | 文件类型（pdf/docx/xlsx） |
| `version` | int | 版本号 |
| `is_latest` | bool | 是否最新版 |
| `page_number` | int \| None | 页码（PDF） |
| `section_title` | str \| None | 章节标题 |
| `sheet_name` | str \| None | Sheet 名称（Excel） |
| `content_type` | str | 内容类型：text/table/ocr/mixed |
| `chunk_index` | int | 块内序号 |
| `content` | str | 文本内容 |
| `uploaded_at` | str | 上传时间 |

`content_type` 字段用于区分同一文档中不同类型的内容：
- `text`：普通文本，通过 pdfplumber 提取
- `table`：表格内容，通过 pdfplumber 提取并转换为 Markdown 格式保留行列结构
- `ocr`：扫描图片页面，通过 pypdfium2 渲染图片后由 Tesseract OCR 识别
- `mixed`：混合内容页面，同时包含可提取文本和大图片，合并文本提取与 OCR 结果（图片内容以 `[Image Content]` 标记分隔）

## 增量更新流程

1. 用户点击「更新知识库」
2. 后端将项目标记为 `is_updating=True`
3. 查询所有 `is_indexed=False` 且 `is_latest=True` 的文档
4. 对每个文档：解析 → 分块 → 向量化 → 写入 Qdrant
5. 标记文档为 `is_indexed=True`
6. 更新项目统计信息，标记 `is_updating=False`

## Skill 集成

知识库项目通过虚拟 Skill 机制集成到对话系统：

- Skill ID 格式：`kb:{project_name}`
- 选择知识库项目后，系统自动注入 `search_knowledge_base` 工具
- AI 回答时调用该工具检索相关文档片段，并在回答中标注来源（文件名、页码、章节）

### search_knowledge_base 工具

检索结果中每个 chunk 包含以下字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `content` | str | 文档内容 |
| `source` | str | 来源文档标识（文件路径/文件名） |
| `location` | str | 位置描述（如"第3页, 表格"、"Sheet: 汇总表"） |
| `page_number` | int \| None | 页码（PDF） |
| `section_title` | str \| None | 章节标题 |
| `sheet_name` | str \| None | Sheet 名称（Excel） |
| `file_name` | str | 原始文件名 |
| `file_path` | str | 文件夹路径 |
| `content_type` | str | 内容类型（text/table/ocr/mixed） |
| `score` | float | 相似度分数 |

RAG 提示词要求模型在回答时标注来源，格式为 `[来源: 文档名, 位置信息]`。`source` 和 `location` 字段为预计算的来源标识，方便模型直接引用。

## 文档解析

| 格式 | 解析方式 |
|------|---------|
| PDF | pdfplumber 按页提取文本和表格，扫描页通过 pypdfium2 + Tesseract OCR 识别 |
| Word | python-docx 按段落提取 |
| Excel | openpyxl 按 Sheet 分块 |
| ZIP/RAR/7z | 递归解压后按内部文件类型分别解析 |

### PDF 解析流程

PDF 解析使用 pdfplumber 作为主解析器，pypdf 作为降级方案：

1. **普通文本页**（`content_type=text`）：pdfplumber 提取页面文本
2. **表格页**（`content_type=table`）：pdfplumber 提取表格并转换为 Markdown 格式，同时通过 `page.filter()` 排除表格区域提取非表格文本（标题、说明等），两者合并保留完整页面内容
3. **扫描页**（`content_type=ocr`）：当页面文本长度低于 200 字符且包含大尺寸图片时，判定为扫描页，使用 pypdfium2 渲染为图片后由 Tesseract OCR 识别（支持中文简繁体+英文）
4. **混合内容页**（`content_type=mixed`）：当页面同时有可提取文本（>=200字符）和大尺寸图片时，合并文本提取与 OCR 结果，图片内容以 `[Image Content]` 标记分隔

页面类型判定优先级：表格页 > 扫描页 > 混合页 > 文本页

扫描页判定条件：
- 页面提取文本长度 < 200 字符
- 页面包含尺寸 > 200x200 的图片

混合页判定条件：
- 页面提取文本长度 >= 200 字符
- 页面包含尺寸 > 200x200 的图片

OCR 语言配置：`chi_sim+eng`（简体中文 + 英文）

上传大小限制：100MB（`KB_MAX_UPLOAD_SIZE_BYTES`）。
