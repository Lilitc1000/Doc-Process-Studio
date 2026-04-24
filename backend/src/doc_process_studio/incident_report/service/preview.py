import base64
import importlib.util
import io
import shutil
import subprocess
import tempfile
from collections import OrderedDict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    import mammoth
except ImportError:
    mammoth = None

from ...chat.models.attachment import ChatAttachment
from ..schemas.response import IncidentReportPreviewResponse
from ...chat.service.attachments import resolve_attachment_path, save_generated_attachment
from .constants import INCIDENT_REPORT_DOCX_MIME_TYPE, INCIDENT_REPORT_SCRIPT_PATH
from .normalization import normalize_text

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
        docx_path.write_bytes(docx_bytes)

        command = [
            libreoffice_bin,
            "--headless",
            "--convert-to",
            "pdf:writer_pdf_Export",
            "--outdir",
            str(temp_path),
            str(docx_path),
        ]
        process = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=60,
        )
        if process.returncode != 0 or not pdf_path.is_file():
            stderr_text = process.stderr.decode("utf-8", errors="ignore").strip()
            stdout_text = process.stdout.decode("utf-8", errors="ignore").strip()
            detail = stderr_text or stdout_text or "unknown error"
            raise RuntimeError(f"DOCX 转 PDF 失败：{detail}")
        return pdf_path.read_bytes()


def convert_docx_bytes_to_preview_html(docx_bytes: bytes) -> tuple[str, list[str]]:
    if mammoth is None:
        raise RuntimeError("缺少 mammoth 依赖，无法进行 Word 预览。")
    result = mammoth.convert_to_html(io.BytesIO(docx_bytes))
    warnings = [
        normalize_text(getattr(message, "message", ""))
        for message in result.messages
        if normalize_text(getattr(message, "message", ""))
    ]
    return result.value, warnings


def load_docx_bytes_from_attachment(attachment_id: str) -> bytes:
    metadata, attachment_path, is_expired = resolve_attachment_path(attachment_id)
    if is_expired:
        raise RuntimeError("预览附件已过期，请重新生成。")
    if metadata is None or attachment_path is None:
        raise RuntimeError("未找到可预览的附件。")
    if not is_docx_attachment(metadata):
        raise RuntimeError("仅支持预览 DOCX 附件。")
    return attachment_path.read_bytes()


def build_preview_payload_from_docx_bytes(
    docx_bytes: bytes,
) -> tuple[str, str | None, list[str]]:
    warnings: list[str] = []
    html = ""
    pdf_base64: str | None = None

    try:
        pdf_bytes = convert_docx_bytes_to_pdf_bytes(docx_bytes)
        pdf_base64 = base64.b64encode(pdf_bytes).decode("ascii")
    except Exception as exc:
        warnings.append(f"PDF 预览生成失败，已回退为 HTML：{normalize_text(exc)}")

    try:
        html, html_warnings = convert_docx_bytes_to_preview_html(docx_bytes)
        warnings.extend(html_warnings)
    except Exception as exc:
        if pdf_base64 is None:
            raise RuntimeError(f"文档预览失败：{normalize_text(exc)}") from exc
        warnings.append(f"HTML 预览生成失败：{normalize_text(exc)}")

    return html, pdf_base64, warnings


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


def _build_output_name(*, session_title: str, session_id: str, suffix: str) -> str:
    normalized_title = session_title.strip().replace(" ", "-").replace("/", "-")
    if not normalized_title:
        normalized_title = f"incident-report-{session_id[:8]}"
    return f"{normalized_title}{suffix}"


def build_initial_output_name(*, session_title: str, session_id: str) -> str:
    return _build_output_name(session_title=session_title, session_id=session_id, suffix="-V1.docx")


def build_preview_output_name(*, session_title: str, session_id: str) -> str:
    return _build_output_name(session_title=session_title, session_id=session_id, suffix="-preview.docx")
