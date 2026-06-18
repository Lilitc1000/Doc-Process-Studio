import base64
import hashlib
import importlib.util
import io
import json
import logging
import os
import shutil
import subprocess
import tempfile
from collections import OrderedDict
from pathlib import Path
from typing import Any

from ...chat.schemas.attachment import ChatAttachment
from ..schemas.common import PermissionDenied
from ..schemas.response import IncidentReportPreviewResponse
from ...chat.service.attachments import resolve_attachment_path, save_generated_attachment
from .constants import INCIDENT_REPORT_DOCX_MIME_TYPE, INCIDENT_REPORT_SCRIPT_PATH
from .normalization import normalize_text

logger = logging.getLogger(__name__)

_PREVIEW_RESULT_CACHE_MAX_ENTRIES = 12
_PREVIEW_RESULT_CACHE: OrderedDict[str, IncidentReportPreviewResponse] = OrderedDict()

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
        raise RuntimeError("Incident report script not found, cannot generate preview.")
    spec = importlib.util.spec_from_file_location(
        "incident_report_generator_module",
        INCIDENT_REPORT_SCRIPT_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to load incident report script.")
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
            logger.debug("Failed to delete temp file %s", temp_path, exc_info=True)


def convert_docx_bytes_to_pdf_bytes(docx_bytes: bytes) -> bytes:
    libreoffice_bin = shutil.which("libreoffice") or shutil.which("soffice")
    if not libreoffice_bin:
        raise RuntimeError("LibreOffice not detected, cannot generate PDF preview.")

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
            raise RuntimeError(f"DOCX to PDF conversion failed: {detail}")
        return pdf_path.read_bytes()


def load_docx_bytes_from_attachment(attachment_id: str) -> bytes:
    metadata, attachment_path, is_expired = resolve_attachment_path(attachment_id)
    if is_expired:
        raise RuntimeError("Preview attachment has expired, please regenerate.")
    if metadata is None or attachment_path is None:
        raise RuntimeError("No previewable attachment found.")
    if not is_docx_attachment(metadata):
        raise RuntimeError("Only DOCX attachments can be previewed.")
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
        logger.debug("Failed to serialize payload for hashing, using repr fallback")
        normalized = repr(payload)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


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
        logger.debug("Failed to stat preview template, returning 'unknown'")
        return "unknown"


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
    user_id: str | None = None,
    version: int | None = None,
    model: str | None = None,
    reranker_model: str | None = None,
) -> IncidentReportPreviewResponse:
    from .report_store import load_report_orm
    from .report_data import build_report_data_from_snapshot
    from .generation import _build_snapshot_from_form_data

    record = await load_report_orm(report_id)
    if record is None:
        raise ValueError(f"Report {report_id} does not exist.")

    if user_id:
        from ..infrastructure.permission_helper import has_permission

        can_view = (
            record.reporter_id == user_id
            or record.assignee_id == user_id
            or record.verifier_id == user_id
            or await has_permission(user_id, "report:view_all")
        )
        if not can_view:
            raise PermissionDenied("无权预览此报告")

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

    docx_bytes = render_docx_bytes_from_report_data(report_data)

    warnings: list[str] = []
    pdf_base64: str | None = None
    try:
        pdf_bytes = convert_docx_bytes_to_pdf_bytes(docx_bytes)
        pdf_base64 = base64.b64encode(pdf_bytes).decode("ascii")
    except Exception as exc:
        warnings.append(f"PDF preview generation failed: {normalize_text(exc)}")

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
