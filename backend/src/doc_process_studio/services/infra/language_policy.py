from typing import Any

from .text_utils import parse_json_object
from .ollama_client import extract_first_message_content, post_chat_completion

LANGUAGE_ZH = "zh"
LANGUAGE_EN = "en"
SUPPORTED_LANGUAGES = {LANGUAGE_ZH, LANGUAGE_EN}


def normalize_language_code(raw: Any) -> str | None:
    if not isinstance(raw, str):
        return None
    normalized = raw.strip().lower()
    if not normalized:
        return None

    if normalized in {"zh", "zh-cn", "zh-hans", "chinese", "中文", "汉语", "简体中文"}:
        return LANGUAGE_ZH
    if normalized in {"en", "en-us", "en-gb", "english", "英文"}:
        return LANGUAGE_EN
    return None


def describe_language(language: str) -> str:
    if normalize_language_code(language) == LANGUAGE_EN:
        return "英文（English）"
    return "中文（简体中文）"


async def detect_language_with_model(
    *,
    model: str,
    context_text: str,
    task_name: str,
) -> tuple[str | None, str]:
    messages = [
        {
            "role": "system",
            "content": (
                "你是语言判定器。"
                "请基于输入上下文判断用户本次任务应使用的输出语言。"
                "只输出 JSON，不要输出解释。"
                'JSON 格式必须是：{"language":"zh|en","reason":"一句话"}。'
            ),
        },
        {
            "role": "user",
            "content": (
                f"task={task_name}\n"
                "请判断本次输出语言。\n"
                f"上下文：\n{context_text}"
            ),
        },
    ]

    try:
        payload = await post_chat_completion(
            model=model,
            messages=messages,
        )
    except Exception as exc:
        return None, f"detect_error:{exc}"

    content = extract_first_message_content(payload)
    parsed = parse_json_object(content)
    if parsed is None:
        return None, "detect_invalid_json"

    language = normalize_language_code(parsed.get("language"))
    reason = str(parsed.get("reason") or "").strip()
    if language is None:
        return None, reason or "detect_unknown_language"
    return language, reason or "detect_ok"


async def verify_text_language_with_model(
    *,
    model: str,
    expected_language: str,
    text: str,
    task_name: str,
) -> tuple[bool | None, str | None, str]:
    normalized_expected = normalize_language_code(expected_language)
    if normalized_expected is None:
        return None, None, "verify_invalid_expected_language"

    messages = [
        {
            "role": "system",
            "content": (
                "你是语言校验器。"
                "请判断给定文本是否与目标语言一致。"
                "只输出 JSON，不要输出解释。"
                'JSON 格式必须是：{"match":true|false,"detected_language":"zh|en|unknown","reason":"一句话"}。'
            ),
        },
        {
            "role": "user",
            "content": (
                f"task={task_name}\n"
                f"expected_language={normalized_expected}\n"
                f"text:\n{text}"
            ),
        },
    ]

    try:
        payload = await post_chat_completion(
            model=model,
            messages=messages,
        )
    except Exception as exc:
        return None, None, f"verify_error:{exc}"

    content = extract_first_message_content(payload)
    parsed = parse_json_object(content)
    if parsed is None:
        return None, None, "verify_invalid_json"

    raw_match = parsed.get("match")
    match: bool | None
    if isinstance(raw_match, bool):
        match = raw_match
    else:
        match = None

    detected_language = normalize_language_code(parsed.get("detected_language"))
    reason = str(parsed.get("reason") or "").strip() or "verify_ok"
    return match, detected_language, reason
