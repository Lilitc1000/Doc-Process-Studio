from doc_process_studio.incident_report.application.dtos import IncidentReportPreviewResponse
from doc_process_studio.incident_report.infrastructure.utils.preview import (
    build_preview_output_name,
    preview_cache_get,
    preview_cache_set,
)


def test_build_preview_output_name() -> None:
    result = build_preview_output_name(report_title="Test Report", report_id="abc12345")
    assert result == "Test-Report-preview.docx"


def test_preview_cache_set_and_get() -> None:
    import doc_process_studio.incident_report.infrastructure.utils.preview as preview_module

    preview_module._PREVIEW_RESULT_CACHE.clear()
    payload = IncidentReportPreviewResponse(
        source="draft",
        label="test",
    )
    preview_cache_set(cache_key="test-key", payload=payload)
    result = preview_cache_get("test-key")
    assert result is not None


def test_preview_cache_get_missing() -> None:
    import doc_process_studio.incident_report.infrastructure.utils.preview as preview_module

    preview_module._PREVIEW_RESULT_CACHE.clear()
    result = preview_cache_get("nonexistent")
    assert result is None


def test_preview_cache_eviction() -> None:
    import doc_process_studio.incident_report.infrastructure.utils.preview as preview_module

    preview_module._PREVIEW_RESULT_CACHE.clear()
    for i in range(15):
        payload = IncidentReportPreviewResponse(
            source="draft",
            label=f"test-{i}",
        )
        preview_cache_set(cache_key=f"key-{i}", payload=payload)
    assert len(preview_module._PREVIEW_RESULT_CACHE) <= 12
