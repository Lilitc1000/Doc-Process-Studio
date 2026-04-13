from copy import deepcopy
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from ...models.conversation.stream import ChatInteractionAnswer, ChatStreamRequest
from ...models.skill.interaction import (
    SkillInteractionConfig,
    SkillInteractionState,
    SkillInteractionStep,
)
from .interaction_store import (
    clear_interaction_state,
    load_interaction_state,
    save_interaction_state,
)


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _normalize_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if value is None:
        return ""
    return str(value).strip()


def _set_nested_value(target: dict[str, Any], dotted_path: str, value: Any) -> None:
    keys = [key.strip() for key in dotted_path.split(".") if key.strip()]
    if not keys:
        return

    current = target
    for key in keys[:-1]:
        next_node = current.get(key)
        if not isinstance(next_node, dict):
            next_node = {}
            current[key] = next_node
        current = next_node
    current[keys[-1]] = value


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in override.items():
        if (
            isinstance(value, dict)
            and isinstance(merged.get(key), dict)
        ):
            merged[key] = _deep_merge(merged[key], value)
            continue
        merged[key] = deepcopy(value)
    return merged


def _build_step_payload(
    *,
    config: SkillInteractionConfig,
    state: SkillInteractionState,
) -> dict[str, Any]:
    step = config.steps[state.current_step_index]
    return {
        "sessionId": state.session_id,
        "stepId": step.id,
        "title": step.title,
        "prompt": step.prompt,
        "kind": step.kind,
        "allowCustom": step.allow_custom,
        "required": step.required,
        "placeholder": step.placeholder,
        "currentStep": state.current_step_index + 1,
        "totalSteps": len(config.steps),
        "options": [
            {
                "value": option.value,
                "label": option.label,
                "description": option.description,
            }
            for option in step.options
        ],
    }


def _extract_answer_value(step: SkillInteractionStep, answer: ChatInteractionAnswer) -> Any:
    if step.kind == "text":
        text_value = _normalize_text(answer.custom_value or answer.value)
        if not text_value and step.required:
            raise ValueError("当前步骤需要输入文本内容。")
        return text_value

    if step.kind == "multi_select":
        raw_values = answer.value if isinstance(answer.value, list) else []
        selected_values = [_normalize_text(value) for value in raw_values]
        selected_values = [value for value in selected_values if value]
        if step.allow_custom and answer.custom_value:
            custom_value = _normalize_text(answer.custom_value)
            if custom_value:
                selected_values.append(custom_value)
        if step.required and not selected_values:
            raise ValueError("当前步骤至少需要选择一个选项。")

        declared_values = {option.value for option in step.options}
        if not step.allow_custom:
            invalid_values = [
                value for value in selected_values if value not in declared_values
            ]
            if invalid_values:
                raise ValueError("当前步骤包含无效选项，请重新选择。")
        return selected_values

    single_value = _normalize_text(answer.custom_value or answer.value)
    if step.required and not single_value:
        raise ValueError("当前步骤需要选择一个选项。")
    if not single_value:
        return single_value

    declared_values = {option.value for option in step.options}
    if declared_values and single_value not in declared_values and not step.allow_custom:
        raise ValueError("当前步骤选项无效，请重新选择。")
    return single_value


async def start_or_resume_interaction(
    *,
    request: ChatStreamRequest,
    config: SkillInteractionConfig,
) -> tuple[SkillInteractionState, dict[str, Any]]:
    state = await load_interaction_state(
        request.conversation_id,
        request.skill_id,
        tenant_id=request.tenant_id,
    )
    if (
        state is None
        or state.current_step_index >= len(config.steps)
    ):
        state = SkillInteractionState(
            session_id=uuid4().hex,
            conversation_id=request.conversation_id,
            skill_id=request.skill_id,
            current_step_index=0,
            collected=deepcopy(config.defaults),
        )
    state.updated_at = _utcnow()
    await save_interaction_state(state, tenant_id=request.tenant_id)
    return state, _build_step_payload(config=config, state=state)


async def submit_interaction_answer(
    *,
    request: ChatStreamRequest,
    config: SkillInteractionConfig,
    answer: ChatInteractionAnswer,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    state = await load_interaction_state(
        request.conversation_id,
        request.skill_id,
        tenant_id=request.tenant_id,
    )
    if state is None:
        raise ValueError("当前会话还未开始交互采集，请先发起交互。")

    if answer.session_id and answer.session_id != state.session_id:
        raise ValueError("交互会话已变化，请刷新当前步骤后重试。")

    if state.current_step_index >= len(config.steps):
        await clear_interaction_state(
            request.conversation_id,
            request.skill_id,
            tenant_id=request.tenant_id,
        )
        raise ValueError("当前交互已经完成，请重新发起。")

    current_step = config.steps[state.current_step_index]
    if current_step.id != answer.step_id:
        raise ValueError("提交的步骤与当前待答步骤不一致，请刷新后重试。")

    answer_value = _extract_answer_value(current_step, answer)
    if answer_value != "" or current_step.required:
        _set_nested_value(state.collected, current_step.field_path, answer_value)

    state.current_step_index += 1
    state.updated_at = _utcnow()

    if state.current_step_index < len(config.steps):
        await save_interaction_state(state, tenant_id=request.tenant_id)
        return _build_step_payload(config=config, state=state), None

    completed_payload = _deep_merge(config.defaults, state.collected)
    if answer.use_defaults_for_missing:
        completed_payload["allow_incomplete"] = True

    await clear_interaction_state(
        request.conversation_id,
        request.skill_id,
        tenant_id=request.tenant_id,
    )
    return None, completed_payload
