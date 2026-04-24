from typing import Any

from ....chat.models.attachment import ChatAttachment
from ....chat.schemas.request import ChatStreamRequest
from ....shared.tool_args import parse_tool_arguments
from ....core.config import settings
from ..registry import get_skill_tool_config
from ..context import get_skill_context_chunks_by_ids, search_skill_context_chunks
from .skill_files import (
    SCOPED_TOOL_SEPARATOR,
    compose_scoped_tool_name,
    split_scoped_tool_name,
)
from .tool_status import (
    build_tool_status_start,
    build_tool_status_finish,
)
from .tool_schema import (
    build_skill_tools,
    build_skill_tools_for_skills,
)
from .tool_exec import (
    execute_skill_tool_call,
    execute_scoped_skill_tool_call,
    _coerce_json_file_argument,
    _restructure_doc_plan,
    _try_repair_truncated_json,
)

__all__ = [
    "SCOPED_TOOL_SEPARATOR",
    "build_skill_tools",
    "build_skill_tools_for_skills",
    "build_tool_status_finish",
    "build_tool_status_start",
    "compose_scoped_tool_name",
    "execute_scoped_skill_tool_call",
    "execute_skill_tool_call",
    "split_scoped_tool_name",
]
