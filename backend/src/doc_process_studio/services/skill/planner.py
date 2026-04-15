import json
import re
from typing import Any, Iterable

from ...models.skill.catalog import SkillInterfaceConfig
from ...models.skill.runtime import SkillPlanDecision, SkillPlannerCandidate
from ..infra.dtutils import parse_json_object, utcnow
from ..infra.ollama_client import extract_first_message_content, post_chat_completion

_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9._-]+|[\u4e00-\u9fff]{2,}")
_SPLIT_PATTERN = re.compile(r"[\s,，。；;、:：()（）\[\]{}<>!！?？/\\|+\-]+")
_CJK_SEQUENCE_PATTERN = re.compile(r"[\u4e00-\u9fff]{2,}")


def _collect_user_query(messages: list[object]) -> str:
    user_contents: list[str] = []
    for message in messages:
        role = getattr(message, "role", None)
        if role != "user":
            continue
        content = str(getattr(message, "content", "") or "").strip()
        if content:
            user_contents.append(content)

    if not user_contents:
        return ""
    return "\n".join(user_contents[-3:]).strip()


def _tokenize_text(text: str) -> set[str]:
    normalized = text.lower().strip()
    if not normalized:
        return set()
    return {
        token.strip()
        for token in _TOKEN_PATTERN.findall(normalized)
        if len(token.strip()) >= 2
    }


def _split_keywords(text: str) -> set[str]:
    normalized = text.lower().strip()
    if not normalized:
        return set()
    return {
        token.strip()
        for token in _SPLIT_PATTERN.split(normalized)
        if len(token.strip()) >= 2
    }


def _build_cjk_ngrams(text: str) -> set[str]:
    ngrams: set[str] = set()
    for matched in _CJK_SEQUENCE_PATTERN.findall(text):
        sequence = matched.strip()
        if len(sequence) < 2:
            continue
        ngrams.add(sequence)
        max_window = min(6, len(sequence))
        for window_size in range(2, max_window + 1):
            for start_index in range(0, len(sequence) - window_size + 1):
                ngram = sequence[start_index : start_index + window_size]
                if len(ngram) >= 2:
                    ngrams.add(ngram)
    return ngrams


def _collect_skill_keywords(skill: SkillInterfaceConfig) -> set[str]:
    keywords: set[str] = set()
    keywords.update(_split_keywords(skill.id))
    keywords.update(_tokenize_text(skill.display_name))
    keywords.update(_tokenize_text(skill.short_description))
    keywords.update(_build_cjk_ngrams(skill.display_name))
    keywords.update(_build_cjk_ngrams(skill.short_description))
    return {keyword for keyword in keywords if len(keyword) >= 2}


def _score_skill_match(
    *,
    user_query: str,
    user_tokens: set[str],
    skill: SkillInterfaceConfig,
) -> int:
    query_lower = user_query.lower()
    score = 0

    skill_id_lower = skill.id.lower()
    display_name_lower = skill.display_name.lower()
    if skill_id_lower and skill_id_lower in query_lower:
        score += 100
    if display_name_lower and display_name_lower in query_lower:
        score += 80

    skill_keywords = _collect_skill_keywords(skill)
    keyword_hits = 0
    for keyword in skill_keywords:
        if keyword in user_tokens or keyword in query_lower:
            keyword_hits += 1

    score += keyword_hits * 6
    return score


def _dedupe_keep_order(items: Iterable[str]) -> list[str]:
    results: list[str] = []
    for item in items:
        normalized = item.strip()
        if normalized and normalized not in results:
            results.append(normalized)
    return results


def build_implicit_skill_candidates(
    *,
    messages: list[object],
    available_skills: list[SkillInterfaceConfig],
    explicit_skill_ids: list[str],
    system_skill_id: str,
    top_k: int = 4,
) -> list[tuple[str, int]]:
    """第一层：词法召回。返回按分数降序的候选 skill 列表。"""
    user_query = _collect_user_query(messages)
    if not user_query:
        return []

    explicit_set = set(_dedupe_keep_order(explicit_skill_ids))
    user_tokens = _tokenize_text(user_query)

    scored_skills: list[tuple[int, str]] = []
    for skill in available_skills:
        if skill.id == system_skill_id:
            continue
        if skill.id in explicit_set:
            continue

        score = _score_skill_match(
            user_query=user_query,
            user_tokens=user_tokens,
            skill=skill,
        )
        if score <= 0:
            continue
        scored_skills.append((score, skill.id))

    scored_skills.sort(key=lambda item: item[0], reverse=True)
    if not scored_skills:
        return []

    threshold = 12 if explicit_set else 8
    candidates = [
        skill_id
        for score, skill_id in scored_skills
        if score >= threshold
    ]
    ranked_candidates: list[tuple[str, int]] = []
    for score, skill_id in scored_skills:
        if skill_id in candidates:
            ranked_candidates.append((skill_id, score))
        if len(ranked_candidates) >= top_k:
            break
    return ranked_candidates


def _build_rerank_prompt_payload(
    *,
    user_query: str,
    explicit_skill_ids: list[str],
    candidate_skills: list[dict[str, Any]],
    max_implicit_skills: int,
) -> str:
    prompt_payload = {
        "task": "请从候选技能里选择本轮最小必要隐式集合。",
        "user_query": user_query,
        "explicit_skill_ids": explicit_skill_ids,
        "candidate_skills": candidate_skills,
        "constraints": {
            "max_implicit_skills": max_implicit_skills,
            "only_from_candidates": True,
            "prefer_minimal_set": True,
        },
        "output_json_schema": {
            "selected_skill_ids": ["候选中的skill_id"],
            "confidence": 0.0,
            "reasons": {"skill_id": "一句话理由"},
        },
    }
    return json.dumps(prompt_payload, ensure_ascii=False, indent=2)


def _parse_rerank_result(payload: dict[str, Any]) -> tuple[list[str], float | None, dict[str, str]]:
    raw_selected_skill_ids = payload.get("selected_skill_ids")
    selected_skill_ids: list[str] = []
    if isinstance(raw_selected_skill_ids, list):
        for raw_skill_id in raw_selected_skill_ids:
            if not isinstance(raw_skill_id, str):
                continue
            normalized_skill_id = raw_skill_id.strip()
            if normalized_skill_id and normalized_skill_id not in selected_skill_ids:
                selected_skill_ids.append(normalized_skill_id)

    raw_confidence = payload.get("confidence")
    confidence: float | None = None
    if isinstance(raw_confidence, (int, float)):
        confidence = float(raw_confidence)
        confidence = max(0.0, min(1.0, confidence))

    reasons: dict[str, str] = {}
    raw_reasons = payload.get("reasons")
    if isinstance(raw_reasons, dict):
        for skill_id, reason in raw_reasons.items():
            if not isinstance(skill_id, str):
                continue
            if not isinstance(reason, str):
                continue
            normalized_skill_id = skill_id.strip()
            normalized_reason = reason.strip()
            if normalized_skill_id and normalized_reason:
                reasons[normalized_skill_id] = normalized_reason

    return selected_skill_ids, confidence, reasons


async def _rerank_implicit_skills_with_model(
    *,
    model: str,
    user_query: str,
    explicit_skill_ids: list[str],
    candidate_skills: list[dict[str, Any]],
    max_implicit_skills: int,
) -> tuple[list[str], float | None, dict[str, str]] | None:
    """第二层：模型重排。失败时返回 None，由上层回退到词法结果。"""
    system_prompt = (
        "你是技能规划器。"
        "你只能在候选技能中挑选隐式技能。"
        "输出必须是 JSON 对象，不要输出其它文字。"
    )
    user_prompt = _build_rerank_prompt_payload(
        user_query=user_query,
        explicit_skill_ids=explicit_skill_ids,
        candidate_skills=candidate_skills,
        max_implicit_skills=max_implicit_skills,
    )

    try:
        response_payload = await post_chat_completion(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
    except Exception:
        return None

    response_text = extract_first_message_content(response_payload)
    parsed_object = parse_json_object(response_text)
    if not isinstance(parsed_object, dict):
        return None

    selected_skill_ids, confidence, reasons = _parse_rerank_result(parsed_object)
    return selected_skill_ids[:max_implicit_skills], confidence, reasons


def _build_active_skill_ids(
    *,
    available_skill_ids: list[str],
    required_skill_ids: list[str],
    optional_skill_ids: list[str],
    system_skill_id: str,
) -> tuple[list[str], str]:
    has_system_skill = system_skill_id in available_skill_ids
    active_skill_ids: list[str] = []

    if required_skill_ids:
        primary_skill_id = required_skill_ids[0]
    elif optional_skill_ids:
        primary_skill_id = optional_skill_ids[0]
    elif has_system_skill:
        primary_skill_id = system_skill_id
    else:
        primary_skill_id = next(iter(available_skill_ids), system_skill_id)

    active_skill_ids.append(primary_skill_id)
    if has_system_skill and system_skill_id not in active_skill_ids:
        active_skill_ids.append(system_skill_id)

    for skill_id in required_skill_ids:
        if skill_id not in active_skill_ids:
            active_skill_ids.append(skill_id)

    for skill_id in optional_skill_ids:
        if skill_id not in active_skill_ids:
            active_skill_ids.append(skill_id)

    return active_skill_ids, primary_skill_id


async def plan_skill_activation(
    *,
    model: str,
    messages: list[object],
    available_skills: list[SkillInterfaceConfig],
    explicit_skill_ids: list[str],
    missing_explicit_skill_ids: list[str],
    system_skill_id: str,
    max_implicit_skills: int = 2,
    top_k_candidates: int = 4,
    min_confidence: float = 0.35,
) -> SkillPlanDecision:
    """分层混合规划：显式强约束 + 词法召回 + 模型重排 + 策略门控。"""
    available_skill_ids = [skill.id for skill in available_skills]
    required_skill_ids = [
        skill_id for skill_id in _dedupe_keep_order(explicit_skill_ids) if skill_id in available_skill_ids
    ]

    lexical_candidates = build_implicit_skill_candidates(
        messages=messages,
        available_skills=available_skills,
        explicit_skill_ids=required_skill_ids,
        system_skill_id=system_skill_id,
        top_k=top_k_candidates,
    )
    lexical_fallback_skill_ids = [
        skill_id for skill_id, _score in lexical_candidates
    ][:max_implicit_skills]

    candidate_map = {skill.id: skill for skill in available_skills}
    rerank_payload_candidates: list[dict[str, Any]] = []
    for skill_id, score in lexical_candidates:
        skill = candidate_map.get(skill_id)
        if skill is None:
            continue
        rerank_payload_candidates.append(
            {
                "skill_id": skill.id,
                "display_name": skill.display_name,
                "short_description": skill.short_description,
                "lexical_score": score,
            }
        )

    user_query = _collect_user_query(messages)
    rerank_output: tuple[list[str], float | None, dict[str, str]] | None = None
    if user_query and rerank_payload_candidates:
        rerank_output = await _rerank_implicit_skills_with_model(
            model=model,
            user_query=user_query,
            explicit_skill_ids=required_skill_ids,
            candidate_skills=rerank_payload_candidates,
            max_implicit_skills=max_implicit_skills,
        )

    optional_skill_ids: list[str] = []
    confidence: float | None = None
    reasons: dict[str, str] = {}
    if rerank_output is None:
        optional_skill_ids = lexical_fallback_skill_ids
        for skill_id, score in lexical_candidates:
            if skill_id in optional_skill_ids:
                reasons[skill_id] = f"词法召回分数 {score}"
    else:
        reranked_skill_ids, confidence, rerank_reasons = rerank_output
        candidate_skill_id_set = {skill_id for skill_id, _score in lexical_candidates}
        for skill_id in reranked_skill_ids:
            if skill_id in required_skill_ids:
                continue
            if skill_id == system_skill_id:
                continue
            if skill_id not in candidate_skill_id_set:
                continue
            if skill_id not in optional_skill_ids:
                optional_skill_ids.append(skill_id)
            if skill_id in rerank_reasons:
                reasons[skill_id] = rerank_reasons[skill_id]

        if confidence is not None and confidence < min_confidence:
            optional_skill_ids = []
            reasons["planner"] = (
                f"模型重排置信度 {confidence:.2f} 低于阈值 {min_confidence:.2f}，"
                "已禁用隐式技能自动追加。"
            )

        if not optional_skill_ids:
            optional_skill_ids = lexical_fallback_skill_ids
            if not reasons:
                for skill_id, score in lexical_candidates:
                    if skill_id in optional_skill_ids:
                        reasons[skill_id] = f"词法召回分数 {score}"

    optional_skill_ids = optional_skill_ids[:max_implicit_skills]
    active_skill_ids, primary_skill_id = _build_active_skill_ids(
        available_skill_ids=available_skill_ids,
        required_skill_ids=required_skill_ids,
        optional_skill_ids=optional_skill_ids,
        system_skill_id=system_skill_id,
    )

    candidates: list[SkillPlannerCandidate] = []
    for skill_id in required_skill_ids:
        candidates.append(
            SkillPlannerCandidate(
                skill_id=skill_id,
                source="explicit",
                selected=True,
                reason="用户显式选择或显式提及。",
            )
        )

    for skill_id, score in lexical_candidates:
        source = "implicit_rerank" if rerank_output is not None else "implicit_lexical"
        candidates.append(
            SkillPlannerCandidate(
                skill_id=skill_id,
                source=source,
                selected=skill_id in optional_skill_ids,
                lexical_score=score,
                confidence=confidence,
                reason=reasons.get(skill_id),
            )
        )

    if system_skill_id in active_skill_ids:
        candidates.append(
            SkillPlannerCandidate(
                skill_id=system_skill_id,
                source="system",
                selected=True,
                reason="系统级技能始终启用。",
            )
        )

    return SkillPlanDecision(
        planner_model=model,
        required_skill_ids=required_skill_ids,
        optional_skill_ids=optional_skill_ids,
        missing_explicit_skill_ids=_dedupe_keep_order(missing_explicit_skill_ids),
        active_skill_ids=active_skill_ids,
        primary_skill_id=primary_skill_id,
        confidence=confidence,
        reasons=reasons,
        candidates=candidates,
        created_at=utcnow(),
    )
