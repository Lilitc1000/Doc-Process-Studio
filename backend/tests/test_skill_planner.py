import asyncio

from doc_process_studio.models.conversation.stream import ChatMessageInput
from doc_process_studio.models.skill.catalog import SkillInterfaceConfig
from doc_process_studio.services.skill import planner as planner_module
from doc_process_studio.services.skill.planner import (
    plan_implicit_skill_ids,
    plan_implicit_skill_ids_with_model,
)


def _build_skill(
    *,
    skill_id: str,
    display_name: str,
    short_description: str,
) -> SkillInterfaceConfig:
    return SkillInterfaceConfig(
        id=skill_id,
        display_name=display_name,
        short_description=short_description,
        default_prompt=f"${skill_id}",
        tools=[],
    )


def test_plan_implicit_skill_ids_selects_resume_skill() -> None:
    skills = [
        _build_skill(
            skill_id="document-assistant",
            display_name="文档助手",
            short_description="通用文档阅读与问答",
        ),
        _build_skill(
            skill_id="resume-transport-review",
            display_name="交通简历审核",
            short_description="审核候选人简历并判断是否满足交通行业经验要求",
        ),
        _build_skill(
            skill_id="project-architecture-docx",
            display_name="架构文档生成",
            short_description="读取项目并生成系统架构文档",
        ),
    ]

    implicit_skill_ids = plan_implicit_skill_ids(
        messages=[ChatMessageInput(role="user", content="请帮我做一轮简历审核，重点看交通行业经验")],
        available_skills=skills,
        explicit_skill_ids=[],
        system_skill_id="document-assistant",
    )

    assert implicit_skill_ids == ["resume-transport-review"]


def test_plan_implicit_skill_ids_skips_explicit_skills() -> None:
    skills = [
        _build_skill(
            skill_id="document-assistant",
            display_name="文档助手",
            short_description="通用文档阅读与问答",
        ),
        _build_skill(
            skill_id="incident-report",
            display_name="事故报告生成",
            short_description="采集事故信息并生成报告",
        ),
        _build_skill(
            skill_id="project-architecture-docx",
            display_name="架构文档生成",
            short_description="读取项目并生成系统架构文档",
        ),
    ]

    implicit_skill_ids = plan_implicit_skill_ids(
        messages=[
            ChatMessageInput(
                role="user",
                content="按事故报告模板整理后，再补一份架构文档",
            )
        ],
        available_skills=skills,
        explicit_skill_ids=["incident-report"],
        system_skill_id="document-assistant",
    )

    assert "incident-report" not in implicit_skill_ids
    assert "project-architecture-docx" in implicit_skill_ids


def test_plan_implicit_skill_ids_with_model_fallback_to_lexical(monkeypatch) -> None:
    skills = [
        _build_skill(
            skill_id="document-assistant",
            display_name="文档助手",
            short_description="通用文档阅读与问答",
        ),
        _build_skill(
            skill_id="resume-transport-review",
            display_name="交通简历审核",
            short_description="审核候选人简历并判断是否满足交通行业经验要求",
        ),
    ]

    async def fake_post_chat_completion(**_kwargs):
        raise RuntimeError("remote down")

    monkeypatch.setattr(
        planner_module,
        "post_chat_completion",
        fake_post_chat_completion,
    )

    implicit_skill_ids = asyncio.run(
        plan_implicit_skill_ids_with_model(
            model="qwen3-coder-next:latest",
            messages=[ChatMessageInput(role="user", content="请帮我做交通简历审核")],
            available_skills=skills,
            explicit_skill_ids=[],
            system_skill_id="document-assistant",
        )
    )

    assert implicit_skill_ids == ["resume-transport-review"]


def test_plan_implicit_skill_ids_with_model_prefers_rerank_result(monkeypatch) -> None:
    skills = [
        _build_skill(
            skill_id="document-assistant",
            display_name="文档助手",
            short_description="通用文档阅读与问答",
        ),
        _build_skill(
            skill_id="incident-report",
            display_name="事故报告生成",
            short_description="采集事故信息并生成报告",
        ),
        _build_skill(
            skill_id="project-architecture-docx",
            display_name="架构文档生成",
            short_description="读取项目并生成系统架构文档",
        ),
    ]

    async def fake_post_chat_completion(**_kwargs):
        return {
            "message": {
                "role": "assistant",
                "content": '{"selected_skill_ids":["project-architecture-docx"],"reason":"匹配架构文档任务"}',
            }
        }

    monkeypatch.setattr(
        planner_module,
        "post_chat_completion",
        fake_post_chat_completion,
    )

    implicit_skill_ids = asyncio.run(
        plan_implicit_skill_ids_with_model(
            model="qwen3-coder-next:latest",
            messages=[
                ChatMessageInput(
                    role="user",
                    content="请按项目现状整理并输出系统架构文档",
                )
            ],
            available_skills=skills,
            explicit_skill_ids=[],
            system_skill_id="document-assistant",
        )
    )

    assert implicit_skill_ids == ["project-architecture-docx"]
