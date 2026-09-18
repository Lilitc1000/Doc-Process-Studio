# Settings 模块开发指南

负责「系统级共享设置」与「用户级偏好」两类配置的读写。核心目标：让 RAGFlow 的连接信息与
**密钥以密文落库**，并由管理员在设置页维护，改动**立即生效**、无需重启服务。

## 目录结构

```text
settings/
├── domain/                      # 领域层：值对象、错误、常量
│   ├── errors.py                # SettingsError / InvalidBaseUrlError / InvalidSettingValueError
│   └── values.py                # RagflowConfig、SecretSource、键名与长度约束
├── application/                 # 应用层：用例编排 + 端口定义
│   ├── dtos.py                  # 对外 DTO（**不含任何明文凭据**）
│   ├── ports.py                 # 仓储 / 加解密 / 配置解析 / 连通性自检 端口
│   └── settings_service.py      # SettingsService
├── infrastructure/              # 基础设施层：SQLAlchemy 与 HTTP 实现
│   ├── persistence/models.py    # system_settings / system_secrets / user_settings
│   ├── repositories/            # 三个仓储的 SQLAlchemy 实现
│   ├── ragflow_config_provider.py  # 三级回退 + 缓存失效（本模块的重点）
│   ├── ragflow_probe.py         # 复用 RagflowClient 做连通性自检
│   └── dependencies.py          # 依赖装配（**全部为单例，见下方说明**）
└── router/                      # 用户接口层
    ├── settings.py              # 5 个端点
    └── schemas/                 # 请求 / 响应模型
```

## 三张表的分工（不要合并）

| 表 | 存什么 | 为什么单独拿出来 |
|---|---|---|
| `system_settings` | 系统级**非敏感**配置（`ragflow.base_url` / `ragflow.enabled`，值为 JSON 标量） | — |
| `system_secrets` | 系统级**密文**凭据（`ragflow.api_key`） | 让「敏感值不可能被误序列化进 API 响应」成为**结构保证**，而不是靠"记得排除那个字段"的代码纪律 |
| `user_settings` | 用户级**非敏感**偏好（模型选择），按 `user_id` 隔离，外键级联删除 | — |

## 三级回退链

`SqlRagflowConfigProvider.resolve(scope="system")` 按以下顺序解析：

1. **系统级配置**（`system_settings` + `system_secrets` 解密结果）
2. **环境变量兜底**（`RAGFLOW_BASE_URL` / `RAGFLOW_API_KEY` / `RAGFLOW_ENABLED`）
3. **不可用**（`RagflowConfig.disabled()`，消费方走既有的"返回空容器"降级路径）

两个细节值得强调：

- **密文解不开时不抛异常，而是降级并打 ERROR。** 主密钥被换掉、密文被手工改过都属于
  可恢复的配置问题，不该让整个服务起不来。
- **`enabled` 以库内值为准**：库里写了 `false`，即使 env 里是 `true` 也停用。
  这样"管理员在页面上关掉 RAGFlow"才是真的关掉。

### env 兜底是「按项、随时」生效，不是「启动那一次」

这是最容易被理解错的地方：**兜底是按单个配置项判定的，而且每次缓存过期后重新求值**
（不是只在启动时读一次）。所以准确的语义是「库里有就用库里的，那一项没有才用 env」，
每一项独立：

| 情形 | 结果 |
|---|---|
| 三项都由管理员在页面保存过 | env 的这三个变量**完全不参与**，改它们没有任何效果 |
| 只保存了密钥，没动 Base URL | Base URL 仍来自 env，密钥来自库 |
| 在页面点「清除密钥」 | 库里那行没了 → **回落 env**（若 env 有值），设置页会显示"正在使用环境变量兜底" |

最后一行是刻意的设计而非缺陷：env 兜底存在的意义就是"库还没配时别让功能直接断"。
但要清楚它的代价 —— **只要 env 里还有密钥，「清除」就不是真的关掉**。
想让某一项彻底与 env 脱钩，正确做法是**把 `.env.*` 里那一行删掉**，而不是再写一个
"从 env 播种到库"的机制：播种同样要读 env，等于把同一个值换个地方存，还多出一个
"清除后被重新灌回来"的坑（除非再加标记位）。
本仓库的选择是保留这条回退链，把它的状态**显式暴露**出去 —— `ragflow.base_url_source` /
`ragflow.enabled_source` / `credential.source` 三个字段会如实报告当前值来自 `system` 还是 `env`，
设置页据此给出提示。

## 缓存与「立即生效」

**这是本模块最容易被改坏的地方，改动前先读完这一节。**

`resolve()` 带进程内缓存：`{scope: (过期时间, epoch, 配置)}`，TTL 由
`SYSTEM_SETTINGS_CACHE_TTL_SECONDS` 控制（默认 60s）。写操作（保存 / 清除）后会调用
`invalidate()`，**同进程内立即生效**。

配套的两个约束：

1. **`get_ragflow_config_provider()` 必须是单例**（`@lru_cache`）。
   知识库与事故报告两条链路拿到的必须是**同一个** provider 实例，否则设置页里的
   `invalidate()` 作用不到它们正在用的那份缓存上，"改完立即生效"就落空了。
2. **消费侧不能再用 `@lru_cache` 缓存"客户端实例"。**
   改之前 `knowledge_base/infrastructure/dependencies.py` 的 `get_ragflow_client()` 是
   `@lru_cache(maxsize=1)`，会把第一次构造时的 base_url / api_key 钉死到进程结束，
   管理员改了密钥不重启不生效。现在改成每次请求按当前配置构建 ——
   `RagflowClient` 只是一层参数容器，真正的 `httpx.AsyncClient` 本来就在每次调用时创建，
   所以重复构造的开销可以忽略。

`scope` 参数是**为"用户级密钥"方案预留的扩展位**：一期恒为 `"system"`；
将来若要改成"每个用户各自一把密钥"，只需换一个按 `user_id` 解析的实现，
所有调用方一行都不用改。

## 加密

实现在 `common/security/secret_cipher.py`（AES-256-GCM，`user_id`/键名作 AAD）。
本模块只依赖 `SecretCipher` 这个抽象，不直接 import `cryptography`。

密文格式：`v1:<key_id>:<nonce_b64url>:<ciphertext_b64url>`，自带版本与密钥标识，
支持多主密钥并存（轮换时旧密文仍可解）。

主密钥来源（三层策略）：

| 环境 | 来源 | 开发者要做什么 |
|---|---|---|
| dev（默认） | 从 `JWT_SECRET_KEY` 经 HKDF-SHA256 **确定性派生** + 启动 WARNING | **什么都不用做** |
| dev（想用自己一套密钥） | `.env.dev.local` 覆盖 | 需要的人自己建该文件 |
| prod | `SETTINGS_ENCRYPTION_KEY` 必须显式配置，缺失**启动失败** | 走部署环境 Secret 注入 |

派生是确定性的，所以所有开发从同一份 `.env.dev` 派生出的主密钥一致，
即使共用同一个 dev 数据库也能互相解密，**无需传递密钥文件**。代价是 dev 的加密强度
等于 `JWT_SECRET_KEY` 的强度，而它本身就在 `.env.dev` 里 —— 所以 dev 只做到
"防脱库裸读"，不是强保护。

**能力边界（别误解）**：这是对称加密，服务端必须能解出明文才能调用 RAGFlow。
它防的是"数据库脱库 / 备份泄露后直接读到密钥"，**防不住拿到服务器权限的人**。

## API

| 方法 | 路径 | 权限 | 说明 |
|---|---|---|---|
| GET | `/api/settings` | 登录用户 | 设置页视图；**`ragflow` 段仅管理员可见**，非管理员为 `null` |
| PUT | `/api/settings/preferences` | 登录用户 | 部分更新**自己的**偏好 |
| PUT | `/api/settings/ragflow` | **管理员** | 更新系统级连接信息与密钥 |
| POST | `/api/settings/ragflow/test` | **管理员** | 用**已保存的**配置做连通性自检 |
| DELETE | `/api/settings/ragflow/api-key` | **管理员** | 清除系统级密钥 |

### 读侧分层（`GET /api/settings`）

响应按身份分层：所有人都拿得到 `preferences`，只有管理员拿得到 `ragflow`
（含 Base URL、启用状态、密钥掩码与尾 4 位 `hint`）。非管理员时该字段是 **`null`**
（整段缺失，而不是字段置空 —— 置空会被误读成"未配置"）。

用 `is_admin` 这个**软门禁**（返回布尔）而不是 `require_admin`：普通用户仍要打开设置页
改自己的模型偏好，所以本接口必须返回 200，只是内容少一段。

**这不影响普通用户的 RAGFlow 使用**：他们**用** RAGFlow 检索走的是服务端链路
（`skill/infrastructure/tool_loop/tool_exec.py` 的对话检索、事故报告生成的参考素材），
各自向 `RagflowConfigProvider` 现取配置，与本接口完全无关。
本接口只是"把共享配置拿给页面显示"。

### `apiKey` 的四态语义（最容易做错的地方，已定死）

| 请求里的 `apiKey` | 行为 |
|---|---|
| 字段缺失 | 保持不变 |
| `""` 空串 | 保持不变（避免前端空输入框误清密钥） |
| 非空字符串 | strip 后加密覆盖 |
| 走 DELETE 专用接口 | 清除 |

`baseUrl` 的语义相反：传空串或 `null` 表示"撤销库内覆盖、回落环境变量兜底"——
Base URL 不是敏感值，清空是常见且安全的操作。

实现上靠 `body.model_fields_set` 区分"字段缺失"与"值为空"，别用 `is not None` 代替。

### 权限模型

- user_id 一律取自 JWT，**不接受请求体传入**，从根上堵死越权。
- 系统级端点用 `auth.infrastructure.dependencies.require_admin`（判定 `users.role == 'admin'`），
  越权返回 403。
- **需要按身份调整响应内容**（而不是放行/拦截整个接口）时用同模块的 `is_admin`（返回布尔），
  判定口径与 `require_admin` 完全一致，保证"能看的"和"能改的"不会出现两套标准。
- ⚠️ **不要**用事故报告模块的 `incident_report_user_roles` 来判断这里的权限。
  那是模块级角色（"报告审核人"之类），拿它守全系统共享设置，会把
  "给某人分配审核人"顺带变成"能改全局密钥"。

## 相关配置

| 环境变量 | 默认值 | 说明 |
|---|---|---|
| `SETTINGS_ENCRYPTION_KEY` | — | 加密主密钥（base64 的 32 字节或 64 位 hex）。`ENV=prod` 缺失即启动失败 |
| `SETTINGS_ENCRYPTION_KEY_ID` | `k1` | 主密钥标识，为轮换预留 |
| `SETTINGS_ENCRYPTION_ALLOW_DEV_KDF` | `True` | 非生产环境允许从 `JWT_SECRET_KEY` 派生（生产忽略此开关） |
| `SYSTEM_SETTINGS_CACHE_TTL_SECONDS` | `60` | 系统级配置的进程内缓存秒数；`0` = 每次查库 |

## 开发注意

### 加解密相关

- **接口永不返回明文**，也不要新增"回显明文"的接口。一旦能回显，攻击面就从
  "防脱库"退化成"防不住任何有登录态的人"。眼睛图标只作用于用户**正在输入**的内容。
- 密钥内容永远不进日志。`SystemSecret.__repr__` 已显式覆盖，改 ORM 时别把它删了。
- `hint`（掩码尾串）只在明文长度 ≥ 24 时写入，短密钥一律不存 —— 否则"掩码"本身
  就把大部分内容交代了。

### 改装配时

- 动 `knowledge_base` / `incident_report` 的依赖装配前，先读上面「缓存与立即生效」一节。
- 新增的系统级配置项：非敏感放 `system_settings`（键名 `ragflow.*`），
  敏感放 `system_secrets`，**不要**混到同一张表里靠 flag 区分。

### 测试

```bash
cd backend
uv run pytest -q tests/settings tests/common/unit/test_secret_cipher.py
uv run pytest -q tests/integration_db/test_settings_api_db.py   # 需要真实 PostgreSQL
```

`tests/settings/integration/test_settings_api.py` 刻意让每个文件自包含 fake，
不跨文件共享 —— 与仓库既有测试风格一致，避免依赖 sys.path 的插入方式。
