from . import conversation, skill, system

routers = (
    *system.routers,
    *conversation.routers,
    *skill.routers,
)

__all__ = [
    "conversation",
    "routers",
    "skill",
    "system",
]
