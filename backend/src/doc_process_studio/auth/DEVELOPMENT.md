# Auth 业务域开发指南

## 概述

Auth 域负责用户认证与账号管理，包括注册、登录、令牌刷新、用户信息管理、密码修改、登出和账号删除。

## 目录结构

backend/src/doc_process_studio/auth/
├── router/
│   └── auth.py             # 认证 API 端点（速率限制逻辑、dev 环境测试端点）
├── service/
│   └── auth.py             # 认证业务逻辑（注册、登录、令牌、密码、删除）
├── models/
│   └── user.py             # SQLAlchemy ORM 模型（User）
└── schemas/
    ├── request.py          # 入参 Pydantic 模型
    └── response.py         # 出参 Pydantic 模型

## API 端点

| 方法   | 路径                                  | 说明                           | 需要认证 | 环境   |
| ------ | ------------------------------------- | ------------------------------ | -------- | ------ |
| POST   | `/api/auth/register`                  | 用户注册                       | 否       | 全部   |
| POST   | `/api/auth/login`                     | 用户登录（form-urlencoded）    | 否       | 全部   |
| POST   | `/api/auth/refresh`                   | 刷新令牌                       | 否       | 全部   |
| GET    | `/api/auth/me`                        | 获取当前用户信息               | 是       | 全部   |
| PUT    | `/api/auth/me`                        | 更新用户资料                   | 是       | 全部   |
| PUT    | `/api/auth/password`                  | 修改密码                       | 是       | 全部   |
| POST   | `/api/auth/logout`                    | 登出（refresh_token 加入黑名单）| 是       | 全部   |
| DELETE  | `/api/auth/users/{user_id}`           | 删除用户账号（仅允许删除自己） | 是       | 全部   |
| DELETE  | `/api/auth/users/by-prefix/{prefix}`  | 按用户名前缀批量删除用户       | 否       | 仅 dev |
| POST   | `/api/auth/rate-limit-whitelist`      | 将调用者 IP 加入速率限制白名单 | 否       | 仅 dev |
| POST   | `/api/auth/ensure-admin`              | 确保管理员用户存在             | 否       | 仅 dev |

## 核心流程

1. 用户通过 `POST /register` 注册账号，密码使用 passlib + bcrypt 哈希存储
2. 通过 `POST /login` 登录，请求体为 `application/x-www-form-urlencoded` 格式（OAuth2PasswordRequestForm），返回 access_token + refresh_token
3. 后续请求携带 `Authorization: Bearer <access_token>` 访问受保护资源
4. access_token 过期后，使用 refresh_token 调用 `POST /refresh` 获取新令牌对
5. 登出时调用 `POST /logout`，refresh_token 的 jti 写入 Redis 黑名单
6. 删除用户时调用 `DELETE /users/{user_id}`，关联的 chat_sessions 和 incident_report_sessions 通过 FK `ON DELETE CASCADE` 自动清理

## 跨域依赖

- `core.security` — JWT 令牌生成/验证、密码哈希/校验、user_id 生成、`get_current_user_id` 依赖（被其他域 router 使用）
- `core.database` — PostgreSQL 异步连接池（async_session_factory）、SQLAlchemy Base
- `core.cache` — Redis 缓存客户端（token 黑名单、skill 缓存等）
- `core.config` — 配置（JWT 密钥、过期时间、管理员账号、环境变量）

## 数据模型

| 表名                         | 说明                                           | 所在模块           |
| ---------------------------- | ---------------------------------------------- | ------------------ |
| `users`                      | 用户表（user_id, username, hashed_password, avatar_color） | auth/models/       |
| `chat_sessions`              | 聊天会话表（FK → users.user_id, ON DELETE CASCADE） | chat/models/       |
| `incident_report_sessions`   | 事故报告会话表                                 | incident_report/models/ |

## 开发注意

- **bcrypt 版本兼容性**：passlib 的 bcrypt 后端与 `bcrypt>=5.0.0` 不兼容，`pyproject.toml` 中已锁定 `bcrypt>=4.0.1,<5.0.0`
- **登录接口格式**：`/api/auth/login` 使用 `OAuth2PasswordRequestForm`，请求体必须是 `application/x-www-form-urlencoded`，不是 JSON
- **JWT 令牌管理**：access_token 有效期 15 分钟，refresh_token 有效期 7 天；登出时 refresh_token 的 jti 写入 Redis 黑名单
- **速率限制**：注册和登录接口共享内存级速率限制（5 次/60 秒/客户端 IP），白名单 IP 不受限制
- **速率限制白名单**：`POST /api/auth/rate-limit-whitelist`（仅 dev 环境）将调用者 IP 加入白名单，E2E 测试应在 `beforeAll` 中调用此接口
- **删除用户**：`DELETE /users/{user_id}` 仅允许删除自己的账号（token 中的 user_id 必须与路径参数一致）
- **测试专用端点**：`DELETE /users/by-prefix/{prefix}`、`POST /rate-limit-whitelist`、`POST /ensure-admin` 仅在 `settings.env == "dev"` 时注册，生产环境不可访问
- **E2E 测试数据标识**：测试创建的用户名统一使用 `e2e_` 前缀，清理时调用 `DELETE /users/by-prefix/e2e_` 批量删除
- **不要在 `router/` 中写业务逻辑**，所有编排逻辑放 `service/`
- **不要在 `models/` 中引入 Pydantic**
- **ORM 模型归属**：每个业务域的 ORM 模型放在自己的 `models/` 目录下，`Base` 定义在 `core/database.py`
- **共享认证依赖**：`get_current_user_id` 定义在 `core/security.py`，其他域 router 通过 `from ...core.security import get_current_user_id` 引用
