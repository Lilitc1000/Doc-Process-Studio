import re
from typing import Iterable
import json

from ...models.skill.catalog import SkillInterfaceConfig
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

    # 命中阈值：
    # - 显式 skill 已存在时，提高阈值，避免隐式 skill 过度介入。
    # - 无显式 skill 时允许更灵敏一些，支持自动匹配。
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


def _parse_json_object(text: str) -> dict[str, object] | None:
    normalized = text.strip()
    if not normalized:
        return None

    try:
        parsed = json.loads(normalized)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, dict):
        return parsed

    if normalized.startswith("```"):
        normalized = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", normalized)
        normalized = re.sub(r"\s*```$", "", normalized).strip()
        try:
            parsed = json.loads(normalized)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict):
            return parsed

    object_match = re.search(r"\{[\s\S]*\}", normalized)
    if object_match is None:
        return None
    try:
        parsed = json.loads(object_match.group(0))
    except json.JSONDecodeError:
        return None
    if isinstance(parsed, dict):
        return parsed
    return None


def _build_rerank_prompt_payload(
    *,
    user_query: str,
    explicit_skill_ids: list[str],
    candidate_skills: list[dict[str, object]],
    max_implicit_skills: int,
) -> str:
    prompt_payload = {
        "task": (
            "请在候选技能中选择本轮最小必要集合用于隐式调用。"
            "显式技能已固定，不要重复输出显式技能。"
        ),
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
            "reason": "一句话中文说明",
        },
    }
    return json.dumps(prompt_payload, ensure_ascii=False, indent=2)


async def _rerank_implicit_skills_with_model(
    *,
    model: str,
    user_query: str,
    explicit_skill_ids: list[str],
    candidate_skills: list[dict[str, object]],
    max_implicit_skills: int,
) -> list[str] | None:
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
    parsed_object = _parse_json_object(response_text)
    if not isinstance(parsed_object, dict):
        return None

    raw_selected_skill_ids = parsed_object.get("selected_skill_ids")
    if not isinstance(raw_selected_skill_ids, list):
        return []

    selected_skill_ids: list[str] = []
    for raw_skill_id in raw_selected_skill_ids:
        if not isinstance(raw_skill_id, str):
            continue
        normalized_skill_id = raw_skill_id.strip()
        if normalized_skill_id and normalized_skill_id not in selected_skill_ids:
            selected_skill_ids.append(normalized_skill_id)
    return selected_skill_ids[:max_implicit_skills]


def plan_implicit_skill_ids(
    *,
    messages: list[object],
    available_skills: list[SkillInterfaceConfig],
    explicit_skill_ids: list[str],
    system_skill_id: str,
    max_implicit_skills: int = 2,
) -> list[str]:
    """兼容入口：仅词法召回，保留给测试与降级路径。"""
    candidates = build_implicit_skill_candidates(
        messages=messages,
        available_skills=available_skills,
        explicit_skill_ids=explicit_skill_ids,
        system_skill_id=system_skill_id,
        top_k=max_implicit_skills,
    )
    return [skill_id for skill_id, _score in candidates][:max_implicit_skills]


async def plan_implicit_skill_ids_with_model(
    *,
    model: str,
    messages: list[object],
    available_skills: list[SkillInterfaceConfig],
    explicit_skill_ids: list[str],
    system_skill_id: str,
    max_implicit_skills: int = 2,
    top_k_candidates: int = 4,
) -> list[str]:
    """分层规划：词法召回 -> 模型重排 -> 策略裁剪。"""
    candidates = build_implicit_skill_candidates(
        messages=messages,
        available_skills=available_skills,
        explicit_skill_ids=explicit_skill_ids,
        system_skill_id=system_skill_id,
        top_k=top_k_candidates,
    )
    if not candidates:
        return []

    lexical_fallback = [skill_id for skill_id, _score in candidates][:max_implicit_skills]
    user_query = _collect_user_query(messages)
    if not user_query:
        return lexical_fallback

    explicit_set = set(_dedupe_keep_order(explicit_skill_ids))
    candidate_map = {skill.id: skill for skill in available_skills}
    candidate_payload: list[dict[str, object]] = []
    for skill_id, score in candidates:
        skill = candidate_map.get(skill_id)
        if skill is None:
            continue
        candidate_payload.append(
            {
                "skill_id": skill.id,
                "display_name": skill.display_name,
                "short_description": skill.short_description,
                "lexical_score": score,
            }
        )

    reranked_skill_ids = await _rerank_implicit_skills_with_model(
        model=model,
        user_query=user_query,
        explicit_skill_ids=list(explicit_set),
        candidate_skills=candidate_payload,
        max_implicit_skills=max_implicit_skills,
    )
    if reranked_skill_ids is None:
        return lexical_fallback

    candidate_skill_id_set = {skill_id for skill_id, _score in candidates}
    normalized_skill_ids: list[str] = []
    for skill_id in reranked_skill_ids:
        if skill_id in explicit_set:
            continue
        if skill_id == system_skill_id:
            continue
        if skill_id not in candidate_skill_id_set:
            continue
        if skill_id not in normalized_skill_ids:
            normalized_skill_ids.append(skill_id)
    if normalized_skill_ids:
        return normalized_skill_ids[:max_implicit_skills]
    return lexical_fallback
