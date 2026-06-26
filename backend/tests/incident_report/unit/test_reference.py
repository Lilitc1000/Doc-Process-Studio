from pathlib import Path

from doc_process_studio.incident_report.infrastructure.adapters.reference_context import (
    _extract_reference_summary,
    _select_references_by_heuristic,
)
from doc_process_studio.incident_report.infrastructure.adapters.reference_context import (
    _load_text_file as load_text_file,
)


def test_extract_reference_summary_basic():
    text = "# Title\nLine 1\nLine 2\nLine 3\nLine 4"
    result = _extract_reference_summary(text)
    assert "Line 1" in result
    assert len(result) <= 260


def test_extract_reference_summary_no_headings():
    text = "Line 1\nLine 2\nLine 3"
    result = _extract_reference_summary(text)
    assert "Line 1" in result


def test_extract_reference_summary_empty():
    result = _extract_reference_summary("")
    assert result == ""


def test_select_references_by_heuristic_common():
    paths = ["body-sections/common.md", "body-sections/impact.md"]
    result = _select_references_by_heuristic(section_id="impact", available_paths=paths)
    assert "body-sections/common.md" in result
    assert "body-sections/impact.md" in result


def test_select_references_by_heuristic_no_match():
    paths = ["body-sections/impact.md", "body-sections/root-cause.md"]
    result = _select_references_by_heuristic(section_id="timeline", available_paths=paths)
    assert len(result) >= 1


def test_select_references_by_heuristic_empty_paths():
    result = _select_references_by_heuristic(section_id="impact", available_paths=[])
    assert result == []


def test_select_references_by_heuristic_quick():
    paths = ["body-sections/common.md", "body-sections/quick.md"]
    result = _select_references_by_heuristic(section_id="quick", available_paths=paths)
    assert "body-sections/quick.md" in result


def test_load_text_file_nonexistent():
    result = load_text_file(Path("/nonexistent/file.txt"))
    assert result == ""
