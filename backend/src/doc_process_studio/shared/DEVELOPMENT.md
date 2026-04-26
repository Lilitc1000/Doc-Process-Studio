# Shared 开发指南

跨模块共享工具目录。如果某个函数在两个及以上业务模块里重复出现，优先收敛到这里。

## 目录结构

```text
backend/src/doc_process_studio/shared/
├── dtutils.py      # 日期时间工具（utcnow、utcnow_iso）
├── text_utils.py   # 文本/JSON 解析（parse_json_object）
├── tool_args.py    # 工具参数解析与规整
└── error_utils.py  # 错误事件构建
```

## 模块说明

| 模块 | 职责 | 典型使用场景 |
|------|------|-------------|
| `dtutils.py` | UTC 时间获取和格式化 | 所有需要记录时间戳的地方 |
| `text_utils.py` | 从文本中提取 JSON 对象 | LLM 响应解析 |
| `tool_args.py` | Skill 工具参数解析与归一化 | tool_loop 执行前参数处理 |
| `error_utils.py` | 统一错误事件结构构建 | 异常处理和日志记录 |

## 开发注意

- 放入 `shared/` 的函数必须是**纯工具函数**，不依赖业务状态
- 新增共享函数前，确认它确实在两个及以上业务模块中有使用需求
- 不要将与特定业务域强耦合的逻辑放入 `shared/`
- 优先使用 `shared/` 中的现有函数，避免重复实现
