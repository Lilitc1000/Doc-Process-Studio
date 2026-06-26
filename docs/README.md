# doc_process_studio

全栈 AI 文档处理工作室，支持文档生成、事故报告管理等功能。

## 技术栈

- **前端**：Vue 3 + Vite + TypeScript + Pinia + Vue Router
- **后端**：Python 3.13 + FastAPI + SQLAlchemy + Alembic
- **数据库**：PostgreSQL + Redis
- **AI**：Ollama（本地 LLM）

## 目录结构

```text
.
├── backend/          # 后端服务
├── frontend/         # 前端应用
└── requirements/     # 需求文档
```

## 快速启动（DevContainer 内）

```bash
# 后端
cd backend && uv sync --group dev && uv run uvicorn doc_process_studio.main:app --reload --host 0.0.0.0 --port 8000

# 前端
cd frontend && npm install && npm run dev -- --host --port 5173
```

## Git 提交规范

项目使用 [Husky](https://typicode.github.io/husky/) + [lint-staged](https://github.com/lint-staged/lint-staged) + [commitlint](https://commitlint.js.org/) 自动检查提交质量。

### 提交信息格式

遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

```
<type>(<scope>): <description>
```

**type 类型**：

| type | 说明 |
|------|------|
| feat | 新功能 |
| fix | Bug 修复 |
| refactor | 重构（不新增功能、不修复 Bug） |
| style | 样式调整（不影响逻辑） |
| test | 测试相关 |
| docs | 文档相关 |
| chore | 构建/工具/杂务 |

**scope 范围**：`frontend`、`backend`、`chat`、`skill`、`incident-report`、`knowledge-base`、`auth`、`infra`

示例：`feat(chat): 增加历史会话功能`

### Pre-commit Hook

每次 `git commit` 自动执行以下检查：

**1. lint-staged（暂存文件级别）**

| 匹配文件 | 执行命令 |
|---------|---------|
| `backend/{src,tests}/**/*.py` | `ruff check --fix`（含未使用 import/变量/参数检测）→ `ruff format` |
| `frontend/{src,tests}/**/*.{ts,vue}` | `eslint --fix`（含 `@typescript-eslint/no-unused-vars`）→ `prettier --write` |
| `frontend/src/**/*.{css,html,json,md}` | `prettier --write` |

**2. 代码质量检查（项目级别，仅在有相关文件变更时运行）**

| 变更文件 | 执行命令 | 检查内容 |
|---------|---------|---------|
| `backend/{src,tests}/**/*.py` | `ruff check --select F,ARG src/ tests/` | 未使用 import（F401）、未使用变量（F841）、未使用函数参数（ARG） |
| `backend/{src,tests}/**/*.py` | `vulture src/` | 死代码检测（仅扫描 src/，测试目录允许有"死"代码） |
| `backend/{src,tests}/**/*.py` | `mypy src/doc_process_studio` | 静态类型检查（仅扫描 src/，测试目录不做类型检查） |
| `frontend/{src,tests}/**/*.{ts,vue}` | `vue-tsc --noEmit` | 未使用变量/参数（`noUnusedLocals`/`noUnusedParameters`）+ 静态类型检查 |
| `frontend/{src,tests}/**/*.{ts,vue}` | `knip` | 未使用导出/依赖检测 |

**3. commitlint（提交信息校验）**

校验提交信息是否符合 Conventional Commits 规范，header 最大长度 100 字符。

### 跳过 Hook（仅紧急情况）

```bash
git commit --no-verify -m "..."
```

## 开发文档索引

| 文档 | 说明 |
|------|------|
| [frontend/README.md](frontend/README.md) | 前端开发指南（目录结构、命名规范、组件分层） |
| [backend/README.md](backend/README.md) | 后端开发指南（目录结构、业务域规则、开发约定） |
| [frontend/tests/DEVELOPMENT.md](frontend/tests/DEVELOPMENT.md) | 前端测试开发指南 |
| [backend/tests/DEVELOPMENT.md](backend/tests/DEVELOPMENT.md) | 后端测试开发指南 |
