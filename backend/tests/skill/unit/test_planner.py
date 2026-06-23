import json
from pathlib import Path

from doc_process_studio.chat.schemas.request import ChatMessageInput
from doc_process_studio.skill.schemas.catalog import SkillInterfaceConfig
from doc_process_studio.skill.service import planner as planner_module
from doc_process_studio.skill.service.planner import plan_skill_activation


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


async def test_plan_skill_activation_selects_resume_skill() -> None:
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

    plan = await plan_skill_activation(
        model="qwen3-coder-next:latest",
        messages=[ChatMessageInput(role="user", content="请帮我做一轮简历审核，重点看交通行业经验")],
        available_skills=skills,
        explicit_skill_ids=[],
        missing_explicit_skill_ids=[],
        system_skill_id="document-assistant",
    )

    assert plan.required_skill_ids == []
    assert plan.optional_skill_ids == ["resume-transport-review"]
    assert plan.primary_skill_id == "resume-transport-review"
    assert "document-assistant" in plan.active_skill_ids


async def test_plan_skill_activation_skips_explicit_skills() -> None:
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

    plan = await plan_skill_activation(
        model="qwen3-coder-next:latest",
        messages=[
            ChatMessageInput(
                role="user",
                content="按事故报告模板整理后，再补一份架构文档",
            )
        ],
        available_skills=skills,
        explicit_skill_ids=["incident-report"],
        missing_explicit_skill_ids=[],
        system_skill_id="document-assistant",
    )

    assert plan.required_skill_ids == ["incident-report"]
    assert "incident-report" not in plan.optional_skill_ids
    assert "project-architecture-docx" in plan.optional_skill_ids
    assert plan.primary_skill_id == "incident-report"


async def test_plan_skill_activation_fallback_to_lexical(monkeypatch) -> None:
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

    plan = await plan_skill_activation(
        model="qwen3-coder-next:latest",
        messages=[ChatMessageInput(role="user", content="请帮我做交通简历审核")],
        available_skills=skills,
        explicit_skill_ids=[],
        missing_explicit_skill_ids=[],
        system_skill_id="document-assistant",
    )

    assert plan.optional_skill_ids == ["resume-transport-review"]


async def test_plan_skill_activation_prefers_rerank_result(monkeypatch) -> None:
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
                "content": (
                    '{"selected_skill_ids":["project-architecture-docx"],'
                    '"confidence":0.88,'
                    '"reasons":{"project-architecture-docx":"任务描述明确指向架构文档输出"}}'
                ),
            }
        }

    monkeypatch.setattr(
        planner_module,
        "post_chat_completion",
        fake_post_chat_completion,
    )

    plan = await plan_skill_activation(
        model="qwen3-coder-next:latest",
        messages=[
            ChatMessageInput(
                role="user",
                content="请按项目现状整理并输出系统架构文档",
            )
        ],
        available_skills=skills,
        explicit_skill_ids=[],
        missing_explicit_skill_ids=[],
        system_skill_id="document-assistant",
    )

    assert plan.optional_skill_ids == ["project-architecture-docx"]
    assert plan.confidence == 0.88


_BENCHMARK_SKILLS = [
    SkillInterfaceConfig(
        id="document-assistant",
        display_name="文档处理助手",
        short_description="阅读并整理 PDF/Word/Excel/PPT 等文档",
        default_prompt="doc",
        tools=[],
    ),
    SkillInterfaceConfig(
        id="resume-transport-review",
        display_name="交通简历审核",
        short_description="审核候选人是否具备交通行业经验",
        default_prompt="resume",
        tools=[],
    ),
    SkillInterfaceConfig(
        id="project-architecture-docx",
        display_name="架构文档生成",
        short_description="读取项目并生成架构设计 DOCX",
        default_prompt="arch",
        tools=[],
    ),
    SkillInterfaceConfig(
        id="incident-report",
        display_name="事故报告生成",
        short_description="收集事故信息并生成事故报告文档",
        default_prompt="incident",
        tools=[],
    ),
]


def test_skill_selection_precision_from_benchmark_cases() -> None:
    dataset_path = Path(__file__).resolve().parent / "skill_selection_cases.json"
    cases = json.loads(dataset_path.read_text(encoding="utf-8"))

    matched = 0
    for case in cases:
        query = str(case["query"])
        expected = str(case["expected_primary_skill"])
        candidates = planner_module.build_implicit_skill_candidates(
            messages=[ChatMessageInput(role="user", content=query)],
            available_skills=_BENCHMARK_SKILLS,
            explicit_skill_ids=[],
            system_skill_id="document-assistant",
            top_k=3,
        )
        predicted = candidates[0][0] if candidates else "document-assistant"
        if predicted == expected:
            matched += 1

    precision = matched / len(cases)
    assert precision >= 0.85
