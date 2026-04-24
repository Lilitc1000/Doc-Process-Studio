import asyncio
import hashlib
from collections import OrderedDict
from copy import deepcopy
from typing import Any

try:
    from deep_translator import GoogleTranslator
except ImportError:
    GoogleTranslator = None

from .constants import _CJK_CHAR_PATTERN, _TRANSLATION_SKIP_KEYS
from .normalization import normalize_text

_TRANSLATION_CACHE_MAX_ENTRIES = 4096
_TRANSLATION_CACHE: OrderedDict[str, str] = OrderedDict()
_TRANSLATION_ENGINE_NAME = "python-google-translator"


def stable_payload_hash(payload: Any) -> str:
    import json
    try:
        normalized = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except Exception:
        normalized = repr(payload)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def translation_cache_key(*, model_name: str, source_text: str) -> str:
    source_hash = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    return f"{model_name}:{source_hash}"


def translation_cache_get(key: str) -> str | None:
    cached = _TRANSLATION_CACHE.get(key)
    if cached is None:
        return None
    _TRANSLATION_CACHE.move_to_end(key)
    return cached


def translation_cache_set(*, key: str, value: str) -> None:
    _TRANSLATION_CACHE[key] = value
    _TRANSLATION_CACHE.move_to_end(key)
    while len(_TRANSLATION_CACHE) > _TRANSLATION_CACHE_MAX_ENTRIES:
        _TRANSLATION_CACHE.popitem(last=False)


def _should_skip_translation(path: list[str], value: str) -> bool:
    if not path:
        return False
    key = path[-1]
    if key in _TRANSLATION_SKIP_KEYS:
        return True
    lowered = value.lower()
    if lowered.startswith("data:image"):
        return True
    return False


def _collect_translation_targets(
    payload: Any,
    *,
    path: list[str],
    targets: dict[str, str],
) -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            _collect_translation_targets(value, path=[*path, key], targets=targets)
        return
    if isinstance(payload, list):
        for index, value in enumerate(payload):
            _collect_translation_targets(value, path=[*path, str(index)], targets=targets)
        return
    if not isinstance(payload, str):
        return

    normalized = normalize_text(payload)
    if not normalized:
        return
    if _should_skip_translation(path, normalized):
        return
    if not _CJK_CHAR_PATTERN.search(normalized):
        return
    targets[".".join(path)] = normalized


def _set_nested_string_value(payload: Any, path_key: str, value: str) -> bool:
    path = [part for part in path_key.split(".") if part]
    if not path:
        return False

    current = payload
    for index, part in enumerate(path):
        is_last = index == len(path) - 1
        if isinstance(current, list):
            if not part.isdigit():
                return False
            item_index = int(part)
            if item_index < 0 or item_index >= len(current):
                return False
            if is_last:
                current[item_index] = value
                return True
            current = current[item_index]
            continue
        if isinstance(current, dict):
            if part not in current:
                return False
            if is_last:
                current[part] = value
                return True
            current = current[part]
            continue
        return False
    return False


async def _translate_batch_via_google(
    source_texts: list[str],
) -> list[str]:
    try:
        translator = GoogleTranslator(source="auto", target="en")
        translated_batch = await asyncio.to_thread(
            translator.translate_batch,
            source_texts,
        )
        if isinstance(translated_batch, list) and len(translated_batch) == len(source_texts):
            return [
                normalize_text(item) if isinstance(item, str) else ""
                for item in translated_batch
            ]
    except Exception:
        pass

    results: list[str] = []
    for source_text in source_texts:
        try:
            translator = GoogleTranslator(source="auto", target="en")
            translated_value = normalize_text(
                await asyncio.to_thread(translator.translate, source_text)
            )
            results.append(translated_value)
        except Exception:
            results.append("")
    return results


async def translate_report_data_to_english(
    *,
    report_data: dict[str, Any],
) -> dict[str, Any]:
    if GoogleTranslator is None:
        return report_data

    targets: dict[str, str] = {}
    _collect_translation_targets(report_data, path=[], targets=targets)
    if not targets:
        return report_data

    translations: dict[str, str] = {}
    pending_targets: dict[str, str] = {}
    for path_key, source_text in targets.items():
        cache_key = translation_cache_key(
            model_name=_TRANSLATION_ENGINE_NAME,
            source_text=source_text,
        )
        cached_text = translation_cache_get(cache_key)
        if cached_text:
            translations[path_key] = cached_text
        else:
            pending_targets[path_key] = source_text

    if pending_targets:
        pending_items = list(pending_targets.items())
        chunk_size = 48
        chunks: list[list[tuple[str, str]]] = []
        for start in range(0, len(pending_items), chunk_size):
            chunks.append(pending_items[start : start + chunk_size])

        batch_results = await asyncio.gather(
            *(
                _translate_batch_via_google(
                    [text for _, text in chunk_items]
                )
                for chunk_items in chunks
            )
        )

        for chunk_items, translated_texts in zip(chunks, batch_results):
            for (path_key, source_text), translated_text in zip(
                chunk_items,
                translated_texts,
                strict=False,
            ):
                if not translated_text:
                    continue
                translations[path_key] = translated_text
                translation_cache_set(
                    key=translation_cache_key(
                        model_name=_TRANSLATION_ENGINE_NAME,
                        source_text=source_text,
                    ),
                    value=translated_text,
                )

    if not translations:
        return report_data

    translated = deepcopy(report_data)
    for path_key, original in targets.items():
        translated_text = normalize_text(translations.get(path_key))
        if not translated_text:
            continue
        if translated_text == original:
            continue
        _set_nested_string_value(translated, path_key, translated_text)
    return translated
