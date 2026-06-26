"""文档助手端口实现。

封装 skill.infrastructure.registry 的跨域调用。
"""

import logging

from ...application.ports import DocumentAssistantPort
from ...domain.values.constants import SYSTEM_DOCUMENT_SKILL_ID
from ..utils.normalization import normalize_text

logger = logging.getLogger(__name__)


class SkillDocumentAssistant(DocumentAssistantPort):
    """基于 skill.infrastructure.registry 的文档助手。"""

    def get_default_prompt(self) -> str:
        from ....skill.infrastructure.registry import get_skill_interface

        try:
            return normalize_text(get_skill_interface(SYSTEM_DOCUMENT_SKILL_ID).default_prompt)
        except Exception:
            logger.debug("Failed to resolve document assistant prompt for skill_id=%s", SYSTEM_DOCUMENT_SKILL_ID)
            return ""
