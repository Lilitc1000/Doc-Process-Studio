"""报告预览 — 纯技术函数。

本模块仅包含无状态、纯函数式的技术工具，不包含任何业务逻辑（如权限检查、
报告加载等）。业务逻辑由 application/preview_service.py 编排。

函数分类：
  渲染工具 → render_docx_bytes_from_report_data, convert_docx_bytes_to_pdf_bytes
  缓存工具 → preview_cache_get, preview_cache_set, preview_template_token, _stable_payload_hash
  文件名工具 → build_preview_output_name

注意：本模块位于 infrastructure 层，可直接调用跨域服务（chat.schemas/chat.service）。
"""

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

from ...application.dtos import IncidentReportPreviewResponse
from ...domain.values.constants import INCIDENT_REPORT_SCRIPT_PATH

logger = logging.getLogger(__name__)

_PREVIEW_RESULT_CACHE_MAX_ENTRIES = 12
_PREVIEW_RESULT_CACHE: OrderedDict[str, IncidentReportPreviewResponse] = OrderedDict()

_incident_generator_module: Any | None = None


def load_incident_generator_module() -> Any:
    """延迟加载 DOCX 生成脚本模块。纯技术函数。"""
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
    """将 report_data 渲染为 DOCX 字节流。纯技术函数。"""
    module = load_incident_generator_module()
    normalized = module.normalize_incident_data(report_data)
    generator = module.FaultLogFormGenerator()
    document = generator.generate_form(normalized)
    output = io.BytesIO()
    document.save(output)
    return output.getvalue()


def convert_docx_bytes_to_pdf_bytes(docx_bytes: bytes) -> bytes:
    """将 DOCX 字节流转换为 PDF 字节流。纯技术函数。"""
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
            capture_output=True,
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


def _stable_payload_hash(payload: Any) -> str:
    """计算 payload 的稳定哈希。纯技术函数。"""
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
    """从缓存获取预览结果。纯技术函数。"""
    cached = _PREVIEW_RESULT_CACHE.get(cache_key)
    if cached is None:
        return None
    _PREVIEW_RESULT_CACHE.move_to_end(cache_key)
    return cached.model_copy(deep=True)


def preview_cache_set(*, cache_key: str, payload: IncidentReportPreviewResponse) -> None:
    """写入预览结果缓存。纯技术函数。"""
    _PREVIEW_RESULT_CACHE[cache_key] = payload.model_copy(deep=True)
    _PREVIEW_RESULT_CACHE.move_to_end(cache_key)
    while len(_PREVIEW_RESULT_CACHE) > _PREVIEW_RESULT_CACHE_MAX_ENTRIES:
        _PREVIEW_RESULT_CACHE.popitem(last=False)


def preview_template_token() -> str:
    """获取模板文件的时间戳 token。纯技术函数。"""
    try:
        return str(INCIDENT_REPORT_SCRIPT_PATH.stat().st_mtime_ns)
    except Exception:
        logger.debug("Failed to stat preview template, returning 'unknown'")
        return "unknown"


def _build_output_name(*, report_title: str, report_id: str, suffix: str) -> str:
    """构建输出文件名。纯技术函数。"""
    normalized_title = report_title.strip().replace(" ", "-").replace("/", "-")
    if not normalized_title:
        normalized_title = f"incident-report-{report_id[:8]}"
    return f"{normalized_title}{suffix}"


def build_preview_output_name(*, report_title: str, report_id: str) -> str:
    """构建预览输出文件名。纯技术函数。"""
    return _build_output_name(report_title=report_title, report_id=report_id, suffix="-preview.docx")
