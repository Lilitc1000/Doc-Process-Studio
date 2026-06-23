from doc_process_studio.incident_report.schemas.response import IncidentReportPreviewResponse
from doc_process_studio.incident_report.service.preview import (
    build_initial_output_name,
    build_preview_output_name,
    is_docx_attachment,
    preview_cache_get,
    preview_cache_set,
)


def test_is_docx_attachment_true():
    class FakeAttachment:
        name = "report.docx"
        mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    assert is_docx_attachment(FakeAttachment()) is True


def test_is_docx_attachment_wrong_name():
    class FakeAttachment:
        name = "report.pdf"
        mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    assert is_docx_attachment(FakeAttachment()) is False


def test_is_docx_attachment_wrong_mime():
    class FakeAttachment:
        name = "report.docx"
        mime_type = "application/pdf"

    assert is_docx_attachment(FakeAttachment()) is False


def test_build_initial_output_name():
    result = build_initial_output_name(report_title="Test Report", report_id="abc12345")
    assert result == "Test-Report-V1.docx"


def test_build_initial_output_name_empty_title():
    result = build_initial_output_name(report_title="", report_id="abc12345")
    assert "abc12345" in result
    assert result.endswith("-V1.docx")


def test_build_initial_output_name_special_chars():
    result = build_initial_output_name(report_title="a/b c", report_id="abc12345")
    assert "/" not in result
    assert " " not in result


def test_build_preview_output_name():
    result = build_preview_output_name(report_title="Test Report", report_id="abc12345")
    assert result == "Test-Report-preview.docx"


def test_preview_cache_set_and_get():
    import doc_process_studio.incident_report.service.preview as preview_module

    preview_module._PREVIEW_RESULT_CACHE.clear()
    payload = IncidentReportPreviewResponse(
        source="draft",
        label="test",
        html="<p>test</p>",
    )
    preview_cache_set(cache_key="test-key", payload=payload)
    result = preview_cache_get("test-key")
    assert result is not None
    assert result.html == "<p>test</p>"


def test_preview_cache_get_missing():
    import doc_process_studio.incident_report.service.preview as preview_module

    preview_module._PREVIEW_RESULT_CACHE.clear()
    result = preview_cache_get("nonexistent")
    assert result is None


def test_preview_cache_eviction():
    import doc_process_studio.incident_report.service.preview as preview_module

    preview_module._PREVIEW_RESULT_CACHE.clear()
    for i in range(15):
        payload = IncidentReportPreviewResponse(
            source="draft",
            label=f"test-{i}",
            html=f"<p>{i}</p>",
        )
        preview_cache_set(cache_key=f"key-{i}", payload=payload)
    assert len(preview_module._PREVIEW_RESULT_CACHE) <= 12
