"""Skill 域领域异常。"""


class SkillError(Exception):
    """Skill 域异常基类。"""


class SkillNotFoundError(SkillError):
    """Skill 不存在。"""


class SkillToolNotFoundError(SkillError):
    """Skill 工具不存在。"""
