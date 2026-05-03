from unittest.mock import MagicMock, patch

import pytest

from doc_process_studio.incident_report.service.preview import (
    _build_output_name,
    _stable_payload_hash,
    convert_docx_bytes_to_pdf_bytes,
    is_docx_attachment,
    load_docx_bytes_from_attachment,
    preview_cache_get,
    preview_cache_set,
    preview_template_token,
    render_docx_bytes_from_report_data,
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


def test_convert_docx_bytes_to_pdf_bytes_no_libreoffice():
    with patch("shutil.which", return_value=None):
        with pytest.raises(RuntimeError, match="LibreOffice"):
            convert_docx_bytes_to_pdf_bytes(b"fake docx")


def test_load_docx_bytes_from_attachment_expired():
    with patch(
        "doc_process_studio.incident_report.service.preview.resolve_attachment_path",
        return_value=(MagicMock(), MagicMock(), True),
    ):
        with pytest.raises(RuntimeError, match="expired"):
            load_docx_bytes_from_attachment("att-1")


def test_load_docx_bytes_from_attachment_not_found():
    with patch(
        "doc_process_studio.incident_report.service.preview.resolve_attachment_path",
        return_value=(None, None, False),
    ):
        with pytest.raises(RuntimeError, match="No previewable"):
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


def test_preview_cache_returns_deep_copy():
    import doc_process_studio.incident_report.service.preview as preview_module
    preview_module._PREVIEW_RESULT_CACHE.clear()
    payload = IncidentReportPreviewResponse(source="draft", label="test")
    preview_cache_set(cache_key="deep-copy-test", payload=payload)

    cached = preview_cache_get("deep-copy-test")
    assert cached is not None
    cached.label = "modified"

    cached_again = preview_cache_get("deep-copy-test")
    assert cached_again.label == "test"


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


def test_stable_payload_hash_deterministic():
    data = {"b": 2, "a": 1}
    h1 = _stable_payload_hash(data)
    h2 = _stable_payload_hash(data)
    assert h1 == h2


def test_stable_payload_hash_different_data():
    h1 = _stable_payload_hash({"a": 1})
    h2 = _stable_payload_hash({"a": 2})
    assert h1 != h2
