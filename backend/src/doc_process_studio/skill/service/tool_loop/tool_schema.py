from typing import Any

from ..registry import get_skill_interface
from .skill_files import _resolve_search_limit_bounds, compose_scoped_tool_name

def build_skill_tools(skill_id: str) -> list[dict[str, Any]]:
    """构造当前 skill 对模型暴露的全部工具。"""

    if skill_id.startswith("kb:"):
        return _build_kb_skill_tools(skill_id)

    skill_interface = get_skill_interface(skill_id)
    _, max_search_limit = _resolve_search_limit_bounds()
    builtin_tools: list[dict[str, Any]] = [
        {
            "type": "function",
            "function": {
                "name": "list_skill_directory",
                "description": "列出当前 skill 某个目录下的文件和子目录，优先用于发现 SKILL.md、references、scripts、assets。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "relative_path": {
                            "type": "string",
                            "description": "相对于 skill 根目录的路径，默认根目录。",
                        }
                    },
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "read_skill_file",
                "description": "读取 skill 内某个具体文本文件的内容，例如 SKILL.md 或 references 下的说明文件。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "relative_path": {
                            "type": "string",
                            "description": "相对于 skill 根目录的文件路径。",
                        }
                    },
                    "required": ["relative_path"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "search_skill_context",
                "description": "按问题搜索当前 skill 的相关片段，可选限定到特定 source_path。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "检索关键词或自然语言问题。",
                        },
                        "source_path": {
                            "type": "string",
                            "description": "可选。限定搜索的相对路径，如 references/doc-plan-example.yaml。",
                        },
                        "limit": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": max_search_limit,
                            "description": "最多返回多少条结果。",
                        },
                    },
                    "required": ["query"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "read_skill_context",
                "description": "读取指定 chunk 的正文，并将这些 chunk 加入当前会话长期上下文。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "chunk_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 1,
                            "maxItems": 6,
                        }
                    },
                    "required": ["chunk_ids"],
                    "additionalProperties": False,
                },
            },
        },
    ]
    declared_tools: list[dict[str, Any]] = []
    for tool in skill_interface.tools:
        declared_tools.append(
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
        )

    return [*builtin_tools, *declared_tools]


def build_skill_tools_for_skills(skill_ids: list[str]) -> list[dict[str, Any]]:
    """构造多 skill 联合工具集：内置检索工具共享，声明式工具按 skill 名称空间隔离。"""
    _, max_search_limit = _resolve_search_limit_bounds()
    normalized_skill_ids: list[str] = []
    for skill_id in skill_ids:
        normalized_skill_id = skill_id.strip()
        if normalized_skill_id and normalized_skill_id not in normalized_skill_ids:
            normalized_skill_ids.append(normalized_skill_id)

    if not normalized_skill_ids:
        return []

    kb_skill_ids = [sid for sid in normalized_skill_ids if sid.startswith("kb:")]
    regular_skill_ids = [sid for sid in normalized_skill_ids if not sid.startswith("kb:")]

    kb_tools: list[dict[str, Any]] = []
    for kb_sid in kb_skill_ids:
        kb_tools.extend(_build_kb_skill_tools(kb_sid))

    if not regular_skill_ids:
        return kb_tools

    builtin_tools: list[dict[str, Any]] = [
        {
            "type": "function",
            "function": {
                "name": "list_skill_directory",
                "description": "列出指定文档处理方式(skill)目录下的文件和子目录。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "skill_id": {
                            "type": "string",
                            "description": "目标文档处理方式标识；不传时默认当前主处理方式。",
                        },
                        "relative_path": {
                            "type": "string",
                            "description": "相对于 skill 根目录的路径，默认根目录。",
                        },
                    },
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "read_skill_file",
                "description": "读取指定文档处理方式(skill)内某个具体文本文件内容。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "skill_id": {
                            "type": "string",
                            "description": "目标文档处理方式标识；不传时默认当前主处理方式。",
                        },
                        "relative_path": {
                            "type": "string",
                            "description": "相对于 skill 根目录的文件路径。",
                        },
                    },
                    "required": ["relative_path"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "search_skill_context",
                "description": "按问题检索指定文档处理方式(skill)的上下文片段。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "skill_id": {
                            "type": "string",
                            "description": "目标文档处理方式标识；不传时默认当前主处理方式。",
                        },
                        "query": {
                            "type": "string",
                            "description": "检索关键词或自然语言问题。",
                        },
                        "source_path": {
                            "type": "string",
                            "description": "可选。限定搜索的相对路径。",
                        },
                        "limit": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": max_search_limit,
                            "description": "最多返回多少条结果。",
                        },
                    },
                    "required": ["query"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "read_skill_context",
                "description": "读取指定 chunk 正文并加入该 skill 的会话上下文。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "skill_id": {
                            "type": "string",
                            "description": "目标文档处理方式标识；不传时默认当前主处理方式。",
                        },
                        "chunk_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 1,
                            "maxItems": 6,
                        },
                    },
                    "required": ["chunk_ids"],
                    "additionalProperties": False,
                },
            },
        },
    ]

    declared_tools: list[dict[str, Any]] = []
    for skill_id in regular_skill_ids:
        skill_interface = get_skill_interface(skill_id)
        for tool in skill_interface.tools:
            declared_tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": compose_scoped_tool_name(skill_id, tool.name),
                        "description": f"[{skill_interface.display_name}] {tool.description}",
                        "parameters": tool.parameters,
                    },
                }
            )

    return [*kb_tools, *builtin_tools, *declared_tools]


def _build_kb_skill_tools(skill_id: str) -> list[dict[str, Any]]:
    """构造知识库虚拟 Skill 的工具集。"""
    project_name = skill_id[3:] if skill_id.startswith("kb:") else ""
    return [
        {
            "type": "function",
            "function": {
                "name": "search_knowledge_base",
                "description": f"在项目「{project_name}」的知识库中检索与查询相关的文档片段，返回文档内容、文件名、页码、章节等信息。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "检索查询文本",
                        },
                    },
                    "required": ["query"],
                    "additionalProperties": False,
                },
            },
        },
    ]
