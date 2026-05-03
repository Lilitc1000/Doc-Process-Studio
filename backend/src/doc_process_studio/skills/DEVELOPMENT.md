# Skills 开发指南

Skill 定义目录，存放所有可扩展的 AI Skill。每个 Skill 是一个独立的文件夹，包含配置、提示词、参考文档和可选的工具定义。

## 目录结构

```text
backend/src/doc_process_studio/skills/
├── document-assistant/         # 文档助手 Skill
├── incident-report/            # 事故报告 Skill
├── project-architecture-docx/  # 项目架构文档生成 Skill
└── resume-transport-review/    # 简历运输审核 Skill
```

## Skill 最小结构

每个 Skill 至少应包含：

```text
skills/<skill-id>/
├── agents/
│   └── config.yaml         # Skill 配置（模型、提示词、参数）
└── interface/
    └── display_name        # 显示名称
    └── default_prompt      # 默认提示词
```

## 可选扩展

| 文件/目录 | 用途 |
|----------|------|
| `references/` | 大体量参考资料 |
| `tools.json` | 声明可执行工具 |
| `scripts/` | 工具执行脚本 |

## Skill 类型

- `chat` — 可在聊天通道中使用和规划的 Skill
- `workspace_incident` — 工作区类型 Skill（如事故报告），不在聊天候选中显示
- `system` — 系统级 Skill（如 `document-assistant`），不直接暴露给用户

## 开发注意

- 新增 Skill 时在此目录下创建新文件夹
- Skill ID 使用 kebab-case 命名
- 工具脚本执行有资源限制（CPU 时间、内存、输出大小），配置在 `core/config.py`
- 不要在 Skill 目录中存放敏感信息或密钥
- `scripts/` 中的 Python 脚本需要完整的类型注解，mypy 检查覆盖此目录
- python-docx 的 `Document` 是工厂函数，类型注解中使用 `from docx.document import Document as DocumentType`
