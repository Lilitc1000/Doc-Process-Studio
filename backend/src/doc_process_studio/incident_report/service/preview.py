import asyncio
import base64
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
from collections import OrderedDict
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    from deep_translator import GoogleTranslator
except ImportError:
    GoogleTranslator = None

from ...chat.models.attachment import ChatAttachment
from ..schemas.response import IncidentReportPreviewResponse
from ...chat.service.attachments import resolve_attachment_path, save_generated_attachment
from .constants import INCIDENT_REPORT_DOCX_MIME_TYPE, INCIDENT_REPORT_SCRIPT_PATH
from .normalization import normalize_text

_PREVIEW_RESULT_CACHE_MAX_ENTRIES = 12
_PREVIEW_RESULT_CACHE: OrderedDict[str, IncidentReportPreviewResponse] = OrderedDict()

_TRANSLATION_ENGINE_NAME = "python-google-translator"
_TRANSLATION_CACHE_MAX_ENTRIES = 4096
_TRANSLATION_CACHE: OrderedDict[str, str] = OrderedDict()

_CJK_CHAR_PATTERN = re.compile(r"[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF\u3000-\u303F]")

_TRANSLATION_SKIP_KEYS = {
    "reference_no",
    "fault_date",
    "fault_time",
    "arrival_datetime",
    "clearance_datetime",
    "contractor_date",
    "closeout_date",
    "start_time",
    "detection_time",
    "resolution_time",
    "total_duration",
    "time",
    "date",
    "data_url",
    "download_url",
    "attachment_id",
    "mime_type",
    "size_label",
    "version",
    "generated_at",
}

_incident_generator_module: Any | None = None


def is_docx_attachment(attachment: Any) -> bool:
    attachment_name = str(getattr(attachment, "name", "")).strip().lower()
    attachment_mime = str(getattr(attachment, "mime_type", "")).strip().lower()
    return attachment_name.endswith(".docx") and (
        attachment_mime == INCIDENT_REPORT_DOCX_MIME_TYPE
    )


def load_incident_generator_module() -> Any:
    global _incident_generator_module
    if _incident_generator_module is not None:
        return _incident_generator_module
    if not INCIDENT_REPORT_SCRIPT_PATH.is_file():
        raise RuntimeError("未找到事故报告脚本，无法生成预览。")
    spec = importlib.util.spec_from_file_location(
        "incident_report_generator_module",
        INCIDENT_REPORT_SCRIPT_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("加载事故报告脚本失败。")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _incident_generator_module = module
    return module


def render_docx_bytes_from_report_data(report_data: dict[str, Any]) -> bytes:
    module = load_incident_generator_module()
    normalized = module.normalize_incident_data(report_data)
    generator = module.FaultLogFormGenerator()
    document = generator.generate_form(normalized)
    output = io.BytesIO()
    document.save(output)
    return output.getvalue()


def save_docx_bytes_as_generated_attachment(
    *,
    docx_bytes: bytes,
    conversation_id: str,
    output_name: str,
) -> ChatAttachment:
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as temp_file:
        temp_file.write(docx_bytes)
        temp_path = Path(temp_file.name)
    try:
        return save_generated_attachment(
            source_path=temp_path,
            conversation_id=conversation_id,
            skill_id="incident-report",
            output_name=output_name,
            mime_type=INCIDENT_REPORT_DOCX_MIME_TYPE,
        )
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except Exception:
            pass


def convert_docx_bytes_to_pdf_bytes(docx_bytes: bytes) -> bytes:
    libreoffice_bin = shutil.which("libreoffice") or shutil.which("soffice")
    if not libreoffice_bin:
        raise RuntimeError("未检测到 LibreOffice，无法生成 PDF 预览。")

    with tempfile.TemporaryDirectory(prefix="incident-preview-") as temp_dir:
        temp_path = Path(temp_dir)
        docx_path = temp_path / "incident-preview.docx"
        pdf_path = temp_path / "incident-preview.pdf"
        user_profile_dir = temp_path / "lo_profile"
        user_profile_dir.mkdir(exist_ok=True)
        docx_path.write_bytes(docx_bytes)

        command = [
            libreoffice_bin,
            "--headless",
            "--norestore",
            "--nologo",
            f"-env:UserInstallation=file://{user_profile_dir}",
            "--convert-to",
            "pdf:writer_pdf_Export",
            "--outdir",
            str(temp_path),
            str(docx_path),
        ]
        env = {
            **os.environ,
            "SAL_DISABLE_OPENGL": "1",
            "SAL_DISABLE_CAIROCANVAS": "1",
        }
        process = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=60,
            env=env,
        )
        if process.returncode != 0 or not pdf_path.is_file():
            stderr_text = process.stderr.decode("utf-8", errors="ignore").strip()
            stdout_text = process.stdout.decode("utf-8", errors="ignore").strip()
            detail = stderr_text or stdout_text or "unknown error"
            raise RuntimeError(f"DOCX 转 PDF 失败：{detail}")
        return pdf_path.read_bytes()


def load_docx_bytes_from_attachment(attachment_id: str) -> bytes:
    metadata, attachment_path, is_expired = resolve_attachment_path(attachment_id)
    if is_expired:
        raise RuntimeError("预览附件已过期，请重新生成。")
    if metadata is None or attachment_path is None:
        raise RuntimeError("未找到可预览的附件。")
    if not is_docx_attachment(metadata):
        raise RuntimeError("仅支持预览 DOCX 附件。")
    return attachment_path.read_bytes()


def _stable_payload_hash(payload: Any) -> str:
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


def _translation_cache_key(*, model_name: str, source_text: str) -> str:
    source_hash = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    return f"{model_name}:{source_hash}"


def _translation_cache_get(key: str) -> str | None:
    cached = _TRANSLATION_CACHE.get(key)
    if cached is None:
        return None
    _TRANSLATION_CACHE.move_to_end(key)
    return cached


def _translation_cache_set(*, key: str, value: str) -> None:
    _TRANSLATION_CACHE[key] = value
    _TRANSLATION_CACHE.move_to_end(key)
    while len(_TRANSLATION_CACHE) > _TRANSLATION_CACHE_MAX_ENTRIES:
        _TRANSLATION_CACHE.popitem(last=False)


def preview_cache_get(cache_key: str) -> IncidentReportPreviewResponse | None:
    cached = _PREVIEW_RESULT_CACHE.get(cache_key)
    if cached is None:
        return None
    _PREVIEW_RESULT_CACHE.move_to_end(cache_key)
    return cached.model_copy(deep=True)


def preview_cache_set(
    *, cache_key: str, payload: IncidentReportPreviewResponse
) -> None:
    _PREVIEW_RESULT_CACHE[cache_key] = payload.model_copy(deep=True)
    _PREVIEW_RESULT_CACHE.move_to_end(cache_key)
    while len(_PREVIEW_RESULT_CACHE) > _PREVIEW_RESULT_CACHE_MAX_ENTRIES:
        _PREVIEW_RESULT_CACHE.popitem(last=False)


def preview_template_token() -> str:
    try:
        return str(INCIDENT_REPORT_SCRIPT_PATH.stat().st_mtime_ns)
    except Exception:
        return "unknown"


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
        cache_key = _translation_cache_key(
            model_name=_TRANSLATION_ENGINE_NAME,
            source_text=source_text,
        )
        cached_text = _translation_cache_get(cache_key)
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
                _translation_cache_set(
                    key=_translation_cache_key(
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


def _build_output_name(*, report_title: str, report_id: str, suffix: str) -> str:
    normalized_title = report_title.strip().replace(" ", "-").replace("/", "-")
    if not normalized_title:
        normalized_title = f"incident-report-{report_id[:8]}"
    return f"{normalized_title}{suffix}"


def build_initial_output_name(*, report_title: str, report_id: str) -> str:
    return _build_output_name(report_title=report_title, report_id=report_id, suffix="-V1.docx")


def build_preview_output_name(*, report_title: str, report_id: str) -> str:
    return _build_output_name(report_title=report_title, report_id=report_id, suffix="-preview.docx")


async def preview_report_attachment(
    *,
    report_id: str,
    version: int | None = None,
    model: str | None = None,
    reranker_model: str | None = None,
) -> IncidentReportPreviewResponse:
    from .report_store import load_report_orm
    from .report_data import build_report_data_from_snapshot
    from .generation import _build_snapshot_from_form_data

    record = await load_report_orm(report_id)
    if record is None:
        raise ValueError(f"报告 {report_id} 不存在。")

    snapshot = _build_snapshot_from_form_data(record.form_data)
    report_data, missing = build_report_data_from_snapshot(
        snapshot,
        strict_required=False,
    )
    if report_data is None:
        report_data = {"missing_fields": missing}

    preview_model = normalize_text(model) or normalize_text(reranker_model)
    draft_hash = _stable_payload_hash(report_data)
    cache_key = f"report:{report_id}:v{version or 'draft'}:{preview_model}:{preview_template_token()}:{draft_hash}"
    cached = preview_cache_get(cache_key)
    if cached is not None:
        return cached

    translated_report_data = await translate_report_data_to_english(
        report_data=report_data,
    )

    docx_bytes = render_docx_bytes_from_report_data(translated_report_data)

    warnings: list[str] = []
    pdf_base64: str | None = None
    try:
        pdf_bytes = convert_docx_bytes_to_pdf_bytes(docx_bytes)
        pdf_base64 = base64.b64encode(pdf_bytes).decode("ascii")
    except Exception as exc:
        warnings.append(f"PDF 预览生成失败：{normalize_text(exc)}")

    output_name = build_preview_output_name(
        report_title=record.title,
        report_id=report_id,
    )

    response = IncidentReportPreviewResponse(
        source="draft",
        version=version,
        label=output_name.replace(".docx", ""),
        html="",
        docx_base64=base64.b64encode(docx_bytes).decode("ascii"),
        docx_file_name=output_name,
        pdf_base64=pdf_base64,
        warnings=warnings,
    )

    preview_cache_set(cache_key=cache_key, payload=response)
    return response
