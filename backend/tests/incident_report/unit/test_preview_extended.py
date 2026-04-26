from unittest.mock import MagicMock, patch

import pytest

from doc_process_studio.incident_report.service.preview import (
    _build_output_name,
    convert_docx_bytes_to_preview_html,
    convert_docx_bytes_to_pdf_bytes,
    is_docx_attachment,
    load_docx_bytes_from_attachment,
    preview_cache_get,
    preview_cache_set,
    preview_template_token,
    render_docx_bytes_from_report_data,
    build_preview_payload_from_docx_bytes,
)
from doc_process_studio.incident_report.schemas.response import IncidentReportPreviewResponse


def test_is_docx_attachment_with_no_name():
    class FakeAttachment:
        name = ""
        mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    assert is_docx_attachment(FakeAttachment()) is False


def test_is_docx_attachment_with_no_attrs():
    class FakeAttachment:
        pass

    assert is_docx_attachment(FakeAttachment()) is False


def test_build_output_name_with_spaces_and_slashes():
    result = _build_output_name(report_title="a/b c", report_id="abc12345", suffix=".docx")
    assert "/" not in result
    assert " " not in result
    assert result.endswith(".docx")


def test_build_output_name_empty_title():
    result = _build_output_name(report_title="", report_id="abc12345", suffix=".docx")
    assert "abc12345" in result


def test_preview_template_token_with_missing_file():
    import doc_process_studio.incident_report.service.preview as preview_module
    original_path = preview_module.INCIDENT_REPORT_SCRIPT_PATH
    fake_path = MagicMock()
    fake_path.stat.side_effect = FileNotFoundError("not found")
    preview_module.INCIDENT_REPORT_SCRIPT_PATH = fake_path
    try:
        result = preview_template_token()
    finally:
        preview_module.INCIDENT_REPORT_SCRIPT_PATH = original_path
    assert result == "unknown"


def test_preview_template_token_with_existing_file():
    import doc_process_studio.incident_report.service.preview as preview_module
    original_path = preview_module.INCIDENT_REPORT_SCRIPT_PATH
    fake_path = MagicMock()
    fake_path.stat.return_value.st_mtime_ns = 1234567890
    preview_module.INCIDENT_REPORT_SCRIPT_PATH = fake_path
    try:
        result = preview_template_token()
    finally:
        preview_module.INCIDENT_REPORT_SCRIPT_PATH = original_path
    assert result == "1234567890"


def test_convert_docx_bytes_to_preview_html_no_mammoth():
    import doc_process_studio.incident_report.service.preview as preview_module
    original_mammoth = preview_module.mammoth
    preview_module.mammoth = None
    try:
        with pytest.raises(RuntimeError, match="mammoth"):
            convert_docx_bytes_to_preview_html(b"fake docx")
    finally:
        preview_module.mammoth = original_mammoth


def test_convert_docx_bytes_to_pdf_bytes_no_libreoffice():
    with patch("shutil.which", return_value=None):
        with pytest.raises(RuntimeError, match="LibreOffice"):
            convert_docx_bytes_to_pdf_bytes(b"fake docx")


def test_load_docx_bytes_from_attachment_expired():
    with patch(
        "doc_process_studio.incident_report.service.preview.resolve_attachment_path",
        return_value=(MagicMock(), MagicMock(), True),
    ):
        with pytest.raises(RuntimeError, match="过期"):
            load_docx_bytes_from_attachment("att-1")


def test_load_docx_bytes_from_attachment_not_found():
    with patch(
        "doc_process_studio.incident_report.service.preview.resolve_attachment_path",
        return_value=(None, None, False),
    ):
        with pytest.raises(RuntimeError, match="未找到"):
            load_docx_bytes_from_attachment("att-1")


def test_load_docx_bytes_from_attachment_not_docx():
    fake_metadata = MagicMock()
    fake_metadata.name = "report.pdf"
    fake_metadata.mime_type = "application/pdf"
    fake_path = MagicMock()

    with patch(
        "doc_process_studio.incident_report.service.preview.resolve_attachment_path",
        return_value=(fake_metadata, fake_path, False),
    ):
        with pytest.raises(RuntimeError, match="DOCX"):
            load_docx_bytes_from_attachment("att-1")


def test_build_preview_payload_from_docx_bytes_pdf_fallback():
    with patch(
        "doc_process_studio.incident_report.service.preview.convert_docx_bytes_to_pdf_bytes",
        side_effect=RuntimeError("no libreoffice"),
    ), patch(
        "doc_process_studio.incident_report.service.preview.convert_docx_bytes_to_preview_html",
        return_value=("<p>html</p>", []),
    ):
        html, pdf_base64, warnings = build_preview_payload_from_docx_bytes(b"fake")
    assert html == "<p>html</p>"
    assert pdf_base64 is None
    assert any("PDF" in w for w in warnings)


def test_build_preview_payload_from_docx_bytes_both_fail():
    with patch(
        "doc_process_studio.incident_report.service.preview.convert_docx_bytes_to_pdf_bytes",
        side_effect=RuntimeError("no libreoffice"),
    ), patch(
        "doc_process_studio.incident_report.service.preview.convert_docx_bytes_to_preview_html",
        side_effect=RuntimeError("no mammoth"),
    ):
        with pytest.raises(RuntimeError, match="文档预览失败"):
            build_preview_payload_from_docx_bytes(b"fake")


def test_build_preview_payload_from_docx_bytes_html_fail_with_pdf():
    with patch(
        "doc_process_studio.incident_report.service.preview.convert_docx_bytes_to_pdf_bytes",
        return_value=b"%PDF-fake",
    ), patch(
        "doc_process_studio.incident_report.service.preview.convert_docx_bytes_to_preview_html",
        side_effect=RuntimeError("no mammoth"),
    ):
        html, pdf_base64, warnings = build_preview_payload_from_docx_bytes(b"fake")
    assert pdf_base64 is not None
    assert any("HTML" in w for w in warnings)


def test_preview_cache_returns_deep_copy():
    import doc_process_studio.incident_report.service.preview as preview_module
    preview_module._PREVIEW_RESULT_CACHE.clear()
    payload = IncidentReportPreviewResponse(source="draft", label="test", html="<p>original</p>")
    preview_cache_set(cache_key="deep-copy-test", payload=payload)

    cached = preview_cache_get("deep-copy-test")
    assert cached is not None
    cached.html = "<p>modified</p>"

    cached_again = preview_cache_get("deep-copy-test")
    assert cached_again.html == "<p>original</p>"


def test_render_docx_bytes_from_report_data():
    mock_module = MagicMock()
    mock_module.normalize_incident_data.return_value = {"normalized": True}
    mock_generator = MagicMock()
    mock_document = MagicMock()
    mock_generator.generate_form.return_value = mock_document
    mock_module.FaultLogFormGenerator.return_value = mock_generator

    with patch(
        "doc_process_studio.incident_report.service.preview.load_incident_generator_module",
        return_value=mock_module,
    ):
        result = render_docx_bytes_from_report_data({"key": "value"})
    assert isinstance(result, bytes)
    mock_module.normalize_incident_data.assert_called_once_with({"key": "value"})
    mock_generator.generate_form.assert_called_once_with({"normalized": True})
