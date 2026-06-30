# 后端测试开发指南

## 目录结构

测试按业务域组织，每个域内再区分测试类型：

```text
backend/tests/
├── DEVELOPMENT.md              # 本文档
├── conftest.py                 # 全局 autouse fixture（Redis/PostgreSQL/速率限制重置、auth_headers）
├── auth/                       # 认证域
│   ├── unit/
│   │   └── test_security.py
│   └── integration/
│       └── test_auth_api.py
├── chat/                       # 对话域
│   ├── unit/
│   │   ├── test_streaming.py
│   │   ├── test_sessions.py
│   │   └── test_file_context.py
│   └── integration/
│       ├── test_chat_sessions_api.py
│       ├── test_chat_stream_api.py
│       ├── test_chat_stream_skill_type_filter.py
│       └── test_chat_attachments_api.py
├── incident_report/            # 事故报告域
│   ├── conftest.py             # 域级 fixture（isolated FastAPI app + TestClient）
│   ├── unit/
│   │   ├── test_report_aggregate.py        # 报告聚合根（状态流转 + 权限 + 事件）
│   │   ├── test_report_store.py            # ORM→Schema 映射 + _CLEAR_SENTINEL
│   │   ├── test_report_store_extended.py   # DB 操作（create/load/update/delete/list/comment）
│   │   ├── test_report_data.py             # 表单数据读写工具函数（infrastructure/utils/report_data）
│   │   ├── test_role_service.py            # 角色管理（基础）
│   │   ├── test_form_schema.py             # 表单 Schema 结构（domain/values/form_schema）
│   │   ├── test_generation.py              # 正文生成（prompt 构建 + payload 应用，infrastructure/utils/generation）
│   │   ├── test_generation_extended.py     # 正文生成（reference/report_data 直通）
│   │   ├── test_normalization.py           # 文本归一化（日期/时间/状态/严重级别，infrastructure/utils/normalization）
│   │   ├── test_preview.py                 # 预览缓存与文件名构建（infrastructure/utils/preview）
│   │   ├── test_preview_extended.py        # 预览转换（PDF/附件加载）
│   │   ├── test_reference.py               # 参考资料提取与启发式选择（infrastructure/adapters/reference_context）
│   │   ├── test_constants.py               # 常量定义（domain/values/constants）
│   │   └── test_schemas_common.py          # 公共 Schema（状态/角色/表单快照）
│   ├── integration/
│   │   ├── test_reports_api.py      # 报告 API（CRUD + 状态流转 + 权限）
│   │   ├── test_reports_workflow.py # 工作流 API（状态转换 + 审计日志 + 评论）
│   │   ├── test_roles_api.py        # 角色 API（权限控制）
│   │   └── test_analytics_api.py    # 分析 API（概览 + 趋势）
│   └── contract/               # Skill 契约测试
│       ├── test_tool_chain_contract.py
│       └── test_script_contract.py
├── skill/                      # 技能域
│   ├── conftest.py             # 域级共享 fixture
│   ├── unit/
│   │   ├── test_registry.py               # 技能注册（基础）
│   │   ├── test_registry_extended.py      # 技能注册（YAML/Markdown 解析 + 接口查询）
│   │   ├── test_selector.py               # 技能选择
│   │   ├── test_planner.py                # 技能规划
│   │   ├── test_tool_loop.py              # 工具循环
│   │   ├── test_tool_schema.py            # 工具 Schema 构建
│   │   ├── test_tool_exec.py              # 工具执行（文本归一化/JSON 解析）
│   │   ├── test_tool_status.py            # 工具状态（标签/路径）
│   │   ├── test_tool_status_extended.py   # 工具状态（开始/完成/复用/声明式工具）
│   │   ├── test_tool_args_extended.py     # 工具参数解析
│   │   ├── test_skill_files.py            # 技能文件操作
│   │   ├── test_context.py                # 上下文检索（向量/重排）
│   │   ├── test_context_packer_extended.py # 层级记忆压缩与上下文预算
│   │   ├── test_conversation_store.py     # 会话存储
│   │   └── test_conversation_store_extended.py # 会话存储（扩展）
│   └── integration/
│       ├── test_skills_api.py
│       └── test_skills_runtime_api.py
├── system/                     # 系统域（执行器、特性开关、链路追踪）
│   ├── unit/
│   │   ├── test_executor.py
│   │   ├── test_feature_flags.py
│   │   ├── test_error_detail.py
│   │   └── test_trace_store.py
│   └── integration/
│       ├── test_agent_trace_api.py
│       └── test_models_api.py
├── core/                       # 核心基础设施域
    └── unit/
        ├── test_settings.py
        ├── test_request_guard.py
        └── test_model_context.py
└── knowledge_base/            # 知识库域
    ├── unit/
    │   ├── test_kb_service.py               # 分块器、文件类型检测、Skill 工具 Schema、内容哈希
    │   └── test_kb_skill_integration.py     # kb: skill 动态加载流程（prompt/工具/目录行/规划）
    └── integration/
        ├── test_kb_api.py                   # API 端点认证守卫测试
        └── test_kb_skill_integration.py     # kb: skill 解析与上下文构建集成测试
```

### 目录组织原则

- **按业务域划分**：与 `src/doc_process_studio/` 的业务域一一对应（auth、chat、incident_report、skill、system、core、knowledge_base）
- **域内按测试类型划分**：`unit/`（单元测试）、`integration/`（集成测试）、`contract/`（契约测试）
- **域级 fixture**：同一域内多个测试文件共享的 fixture 放在 `<domain>/conftest.py`
- **全局 fixture**：放在 `tests/conftest.py`

### 业务域与源码对应关系

| 测试域 | 源码目录 | 说明 |
|--------|----------|------|
| `auth/` | `doc_process_studio/auth/` | 认证（JWT、密码哈希、用户管理） |
| `chat/` | `doc_process_studio/chat/` | 对话（流式、会话、附件、文件上下文） |
| `incident_report/` | `doc_process_studio/incident_report/` | 事故报告（报告 CRUD、状态流转、角色管理、审计日志、正文生成、数据分析） |
| `skill/` | `doc_process_studio/skill/` | 技能系统（注册、选择、规划、工具循环、会话存储） |
| `system/` | `doc_process_studio/system/` | 系统服务（执行器、特性开关、错误详情、链路追踪、模型管理） |
| `core/` | `doc_process_studio/common/` | 共享内核（配置、请求防护、模型上下文、安全、缓存、数据库） |
| `knowledge_base/` | `doc_process_studio/knowledge_base/` | 知识库（项目/文件夹/文档管理、分块、向量化、Skill 集成） |

## 测试分层

| 层级 | 目录 | 职责 | 依赖 |
|------|------|------|------|
| 单元测试 | `<domain>/unit/` | 纯逻辑函数、service 层方法 | monkeypatch 替换外部依赖 |
| 集成测试 | `<domain>/integration/` | API 端点 HTTP 测试 | FastAPI TestClient + monkeypatch |
| 契约测试 | `<domain>/contract/` | Skill 工具链端到端验证 | 真实文件系统（tmp_path） |

**注意**：后端测试不包含 E2E 测试。需要启动完整后端服务并通过真实 HTTP 调用验证的端到端流程测试属于前端 E2E 测试范畴，应在前端项目中编写。

## 运行命令

```bash
cd backend

# 全量测试
env ENV=dev uv run --no-sync pytest -q -p no:cacheprovider

# 只跑某个域的测试
env ENV=dev uv run --no-sync pytest tests/auth/ -q
env ENV=dev uv run --no-sync pytest tests/chat/unit/ -q
env ENV=dev uv run --no-sync pytest tests/incident_report/contract/ -q

# 只跑某个文件
env ENV=dev uv run --no-sync pytest tests/auth/unit/test_security.py -q

# 语法与代码规范检查
env ENV=dev uv run --no-sync ruff check src/doc_process_studio

# 自动格式化代码
env ENV=dev uv run --no-sync ruff format src/doc_process_studio

# 类型检查
env ENV=dev uv run --no-sync mypy src/doc_process_studio
```

---

## 全局 Fixture

`tests/conftest.py` 提供以下 autouse fixture，每个测试后自动执行：

| Fixture | 作用 |
|---------|------|
| `_reset_cache_client` | 清空 Redis 客户端和连接池，防止缓存状态泄漏 |
| `_dispose_async_engine` | 异步 fixture，调用 `await engine.dispose()` 释放异步连接池，防止连接泄漏 |
| `_reset_rate_limiter` | 清空速率限制窗口和白名单，防止限制状态泄漏 |

以及手动使用的 fixture：

| Fixture | 作用 |
|---------|------|
| `auth_headers` | 返回包含有效 JWT 的 `Authorization` 请求头，用于需要认证的 API 测试 |

---

## 单元测试

### 适用场景

- `common/security/security.py` 中的 JWT、密码哈希等纯逻辑
- `service/` 层的业务逻辑（使用 monkeypatch 替换外部依赖）
- `utils/` 下的纯函数
- 模块级别的状态管理（如速率限制、特性开关）

### 编写规范

#### 1. 纯逻辑测试

直接导入函数，断言输入输出：

```python
from doc_process_studio.common.security.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_token,
)


def test_password_hash_and_verify():
    hashed = hash_password("secret123")
    assert verify_password("secret123", hashed) is True
    assert verify_password("wrong", hashed) is False


def test_jwt_create_and_decode():
    token = create_access_token(user_id="usr_abc", username="admin")
    payload = decode_token(token)
    assert payload["sub"] == "usr_abc"
    assert payload["username"] == "admin"
```

**要点**：
- 不需要 mock，直接测试纯函数
- 覆盖正常路径和异常路径

#### 2. Service 层测试（monkeypatch 模式）

使用 `monkeypatch` 替换模块级引用，避免真实 I/O。异步函数直接使用 `async def test_` 编写，pytest-asyncio 会自动识别并执行：

```python
import session_module
from doc_process_studio.chat.service.db_session_store import (
    delete_chat_session,
)


async def test_delete_chat_session_also_cleans_traces(monkeypatch):
    deleted_session_ids = []
    deleted_trace_ids = []

    async def _fake_delete(session_id, db):
        deleted_session_ids.append(session_id)

    async def _fake_delete_traces(session_id, db):
        deleted_trace_ids.append(session_id)

    monkeypatch.setattr(session_module, "delete_chat_session", _fake_delete)
    monkeypatch.setattr(session_module, "delete_agent_traces_by_conversation_id", _fake_delete_traces)

    await delete_chat_session("sess-1", db=None)

    assert "sess-1" in deleted_session_ids
    assert "sess-1" in deleted_trace_ids
```

**要点**：
- 使用 `import xxx as xxx_module` 导入目标模块，便于 monkeypatch 模块级引用
- 在测试函数内定义 `async def _fake_xxx()` 作为替换函数
- 异步测试函数使用 `async def test_` 声明，pytest-asyncio（`asyncio_mode = "auto"`）自动识别并运行
- `monkeypatch` 是 pytest 内置 fixture，每个测试后自动还原

#### 3. 复杂 Service 测试（_FakeRecorder 模式）

对于需要捕获多次副作用的场景，使用 recorder 类：

```python
class _FakeRecorder:
    def __init__(self):
        self.calls = []

    async def record(self, trace_id, payload, db):
        self.calls.append({"trace_id": trace_id, "payload": payload})


async def test_generation_records_trace(monkeypatch):
    recorder = _FakeRecorder()
    monkeypatch.setattr(generation_module, "record_agent_trace", recorder.record)
    monkeypatch.setattr(generation_module, "stream_chat_completion", fake_stream)

    await quick_generate_body(session_id="s1", model="m1", db=None)

    assert len(recorder.calls) == 1
    assert recorder.calls[0]["trace_id"] == "trace-123"
```

#### 4. 辅助函数构建测试数据

复杂数据结构使用辅助函数构建：

```python
def _build_detail(**overrides):
    defaults = {
        "id": "rep-1",
        "title": "测试报告",
        "status": "draft",
        "reporter_id": "usr_test",
    }
    defaults.update(overrides)
    return IncidentReportDetail(**defaults)
```

#### 5. 重置模块级状态

对于有模块级全局状态的模块（如速率限制器），测试后需要手动重置：

```python
def _reset_guard_state():
    from doc_process_studio.common.middleware.request_guard import _rate_windows, _semaphores
    _rate_windows.clear()
    _semaphores.clear()


def test_rate_limit_rejects(monkeypatch):
    _reset_guard_state()
    # ... 测试逻辑
```

---

## 集成测试

### 适用场景

- API 端点的 HTTP 请求/响应测试
- 认证、权限、状态码验证
- 请求参数校验和错误处理

### 编写规范

#### 1. 基本 API 测试

使用 `TestClient` 发送 HTTP 请求：

```python
from fastapi.testclient import TestClient
from doc_process_studio import main as main_module


def test_register_success(client, monkeypatch):
    async def _fake_create(user, db):
        return {"user_id": "usr_new", "username": user.username}

    monkeypatch.setattr(auth_service_module, "create_user", _fake_create)

    resp = client.post("/api/auth/register", json={
        "username": "newuser",
        "password": "password123",
    })

    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "newuser"
```

#### 1b. Isolated FastAPI App 模式（避免 lifespan 触发 DB 连接）

对于涉及数据库连接的模块（如 incident_report），使用 isolated FastAPI app 避免 `Event loop is closed` 错误：

```python
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from doc_process_studio.common.security.security import create_access_token
from doc_process_studio.incident_report.router.reports import router as reports_router
from doc_process_studio.incident_report.router.dependencies import require_admin


def _create_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(reports_router)
    return app


def _auth_headers(user_id: str = "usr_test") -> dict:
    token = create_access_token(user_id, "testuser")
    return {"Authorization": f"Bearer {token}"}


def test_delete_requires_admin():
    app = _create_test_app()

    async def _reject():
        raise HTTPException(status_code=403, detail="需要管理员权限")

    app.dependency_overrides[require_admin] = _reject

    client = TestClient(app)
    resp = client.delete("/api/incident-report/reports/test-id", headers=_auth_headers())
    assert resp.status_code == 403
```

**要点**：
- 不使用 `main_module.app`，而是手动组装 isolated FastAPI app（不含 lifespan）
- 权限控制使用 `app.dependency_overrides` 替换，而非 patch service 层
- service 层函数使用 `unittest.mock.patch` 在 router 模块层级替换

#### 2. 需要认证的 API 测试

使用 `auth_headers` fixture：

```python
def test_get_current_user(client, auth_headers):
    resp = client.get("/api/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "testuser"
```

#### 2b. 桩服务类（继承应用服务契约）

集成测试中需要替换应用服务时，桩类**必须继承对应的应用服务契约**（`application/contracts.py`），确保方法签名与业务接口同步。

**契约类位置**：各域 `application/contracts.py`，与 `ports.py` 并列。

```python
from doc_process_studio.chat.application.contracts import SessionServiceContract

class _FakeSessionService(SessionServiceContract):
    """测试用 SessionService 桩，绕过真实端口依赖。"""

    async def list_sessions(self, user_id: str) -> ChatSessionListResponse:
        _ = user_id  # 未使用的参数用 _ = 标记，避免 ARG 规则报错
        return ChatSessionListResponse(sessions=[...])

    async def save_session(
        self,
        *,
        session_id: str,
        user_id: str,
        title: str,
        title_source_messages: list[str],
        snapshot: ChatSessionSnapshot,
    ) -> ChatSessionSummary:
        _ = (user_id, title, title_source_messages, snapshot)
        assert session_id == "conversation-1"
        return _build_summary("conversation-1", "文档总结")

    # 测试中不使用的方法用 raise NotImplementedError 实现
    async def rename_session(self, session_id: str, user_id: str, title: str) -> ChatSessionSummary:
        _ = (session_id, user_id, title)
        raise NotImplementedError
    ...
```

**要点**：
- 继承契约类后，**运行时实例化桩类会自动检测未实现的抽象方法**（ABC 机制），确保桩类与业务接口同步
- 业务接口变更时（增删方法、修改签名），桩类必须在编译/运行时同步更新
- 未使用的参数用 `_ = param` 标记（保持原参数名，不破坏关键字参数调用）
- 测试中不使用的方法用 `raise NotImplementedError` 实现

#### 3. 流式 API 测试

对 SSE 流式端点，使用 `TestClient` 的 `stream_with_context`：

```python
def test_chat_stream_with_tool_calls(client, auth_headers, monkeypatch):
    monkeypatch.setattr(chat_stream_module, "stream_chat_reply", fake_stream)

    with client.stream("POST", "/api/chat/stream", json={...}, headers=auth_headers) as resp:
        assert resp.status_code == 200
        events = []
        for line in resp.iter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))
        assert any(e.get("type") == "attachment" for e in events)
```

#### 4. 文件系统测试

使用 `tmp_path` fixture：

```python
def test_upload_dedup(client, auth_headers, monkeypatch, tmp_path):
    monkeypatch.setattr(settings_module, "ATTACHMENT_DIR", str(tmp_path))

    test_file = tmp_path / "test.txt"
    test_file.write_text("hello")

    # ... 测试逻辑
```

---

## 契约测试

### 适用场景

- 验证 Skill 工具链能正确生成输出文件
- 验证 Skill 脚本的归一化逻辑

### 编写规范

```python
def test_tool_chain_generates_docx(tmp_path, monkeypatch):
    monkeypatch.setattr(settings_module, "ATTACHMENT_DIR", str(tmp_path))

    result = execute_tool_chain(form_data=sample_data)

    docx_path = tmp_path / result["attachment_id"] / "report.docx"
    assert docx_path.exists()

    doc = Document(str(docx_path))
    assert "事故报告" in doc.paragraphs[0].text
```

---

## 域级 Fixture

当同一业务域内多个测试文件共享构造数据的逻辑时，提取为域级 `conftest.py`：

```python
# tests/skill/conftest.py
import pytest
from doc_process_studio.skill.schemas.catalog import SkillCatalogEntry


@pytest.fixture
def build_skill():
    def _build(**overrides):
        defaults = {
            "id": "test-skill",
            "display_name": "Test Skill",
            "skill_type": "chat",
        }
        defaults.update(overrides)
        return SkillCatalogEntry(**defaults)
    return _build
```

**提取规则**：如果构造数据的逻辑在 2 个以上测试文件中重复出现，应提取为域级 fixture。

---

## 新增测试检查清单

### 新增测试文件

- [ ] 文件放在 `tests/<domain>/<type>/` 目录（域与 `src/doc_process_studio/` 对应）
- [ ] 文件名以 `test_` 开头
- [ ] 新目录需要添加 `__init__.py`

### 新增单元测试

- [ ] 外部依赖使用 `monkeypatch` 替换
- [ ] 异步函数使用 `async def test_` 声明，pytest-asyncio 自动识别运行
- [ ] 模块级引用使用 `import xxx as xxx_module` 导入以便 monkeypatch
- [ ] 有模块级全局状态的，测试后手动重置

### 新增集成测试

- [ ] 使用 `TestClient` 发送 HTTP 请求
- [ ] 需要认证的测试使用 `auth_headers` fixture
- [ ] service 层使用 `monkeypatch` 替换，避免依赖真实数据库
- [ ] Pydantic 响应模型字段使用 snake_case
- [ ] 桩服务类继承对应的应用服务契约（`application/contracts.py`），未使用的方法用 `raise NotImplementedError` 实现

### 新增契约测试

- [ ] 使用 `tmp_path` 管理临时文件
- [ ] 验证生成文件的内容和格式

### 新增 Fixture

- [ ] 全局 fixture 放在 `tests/conftest.py`（autouse 用于状态重置）
- [ ] 域级 fixture 放在 `tests/<domain>/conftest.py`
- [ ] 构造数据逻辑在 2+ 文件中重复时才提取为 fixture
