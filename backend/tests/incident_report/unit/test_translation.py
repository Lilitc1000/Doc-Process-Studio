import asyncio

import doc_process_studio.incident_report.service.translation as translation_module


def test_translate_report_data_returns_input_unchanged():
    report_data = {
        "reference_no": "DAS-20260420-001",
        "description": "Customer reported order placement errors",
    }
    result = asyncio.run(
        translation_module.translate_report_data_to_english(report_data=report_data)
    )
    assert result is report_data


def test_translate_report_data_returns_empty_dict():
    report_data = {}
    result = asyncio.run(
        translation_module.translate_report_data_to_english(report_data=report_data)
    )
    assert result == {}


def test_translate_report_data_preserves_nested_structure():
    report_data = {
        "report_body": {
            "description": "Service outage",
            "timeline": [
                {"time": "09:10", "event": "Fault detected"},
            ],
        },
    }
    result = asyncio.run(
        translation_module.translate_report_data_to_english(report_data=report_data)
    )
    assert result is report_data
    assert result["report_body"]["description"] == "Service outage"
