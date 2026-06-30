from doc_process_studio.incident_report.infrastructure.utils.normalization import (
    compose_datetime_text,
    contains_html_tag,
    extract_appendix_from_rich_text,
    extract_date_text,
    format_date_text,
    format_datetime_text,
    merge_appendix_images,
    normalize_severity_option,
    normalize_status_option,
    normalize_text,
    normalize_time_text,
    normalize_timeline_items,
    parse_date_time,
    safe_json_list,
    severity_option_to_text,
    split_affected_date_summary,
    split_lines,
    status_option_to_text,
)


def test_normalize_text_string() -> None:
    assert normalize_text("  hello  ") == "hello"


def test_normalize_text_none() -> None:
    assert normalize_text(None) == ""


def test_normalize_text_int() -> None:
    assert normalize_text(42) == "42"


def test_normalize_text_empty() -> None:
    assert normalize_text("") == ""


def test_split_lines_list() -> None:
    assert split_lines(["a", "b", "  c  "]) == ["a", "b", "c"]


def test_split_lines_newline_string() -> None:
    assert split_lines("a\nb\nc") == ["a", "b", "c"]


def test_split_lines_semicolon_string() -> None:
    assert split_lines("a;b;c") == ["a", "b", "c"]


def test_split_lines_single_string() -> None:
    assert split_lines("hello") == ["hello"]


def test_split_lines_empty() -> None:
    assert split_lines("") == []
    assert split_lines(None) == []


def test_split_lines_list_with_empty_items() -> None:
    assert split_lines(["a", "", "  ", "b"]) == ["a", "b"]


def test_split_lines_dash_stripped() -> None:
    assert split_lines("- item1\n- item2") == ["item1", "item2"]


def test_parse_date_time_dd_mm_yyyy_hh_mm() -> None:
    result = parse_date_time("08/04/2026 09:10")
    assert result is not None
    assert result.year == 2026
    assert result.month == 4
    assert result.day == 8
    assert result.hour == 9
    assert result.minute == 10


def test_parse_date_time_iso_format() -> None:
    result = parse_date_time("2026-04-08 09:10")
    assert result is not None
    assert result.year == 2026
    assert result.month == 4


def test_parse_date_time_iso_t_format() -> None:
    result = parse_date_time("2026-04-08T09:10")
    assert result is not None
    assert result.year == 2026


def test_parse_date_time_slash_format() -> None:
    result = parse_date_time("2026/04/08 09:10")
    assert result is not None
    assert result.year == 2026


def test_parse_date_time_empty() -> None:
    assert parse_date_time("") is None
    assert parse_date_time("  ") is None


def test_parse_date_time_invalid() -> None:
    assert parse_date_time("not-a-date") is None


def test_format_datetime_text_iso() -> None:
    assert format_datetime_text("2026-04-08T09:10") == "08/04/2026 09:10"


def test_format_datetime_text_iso_space() -> None:
    assert format_datetime_text("2026-04-08 09:10") == "08/04/2026 09:10"


def test_format_datetime_text_empty() -> None:
    assert format_datetime_text("") == ""


def test_format_datetime_text_non_iso() -> None:
    assert format_datetime_text("some text") == "some text"


def test_format_date_text_iso() -> None:
    assert format_date_text("2026-04-08") == "08/04/2026"


def test_format_date_text_dd_mm_yyyy() -> None:
    assert format_date_text("08/04/2026") == "08/04/2026"


def test_format_date_text_dot_separated() -> None:
    assert format_date_text("2026.04.08") == "08/04/2026"


def test_format_date_text_dd_mm_yyyy_dot() -> None:
    assert format_date_text("08.04.2026") == "08/04/2026"


def test_format_date_text_empty() -> None:
    assert format_date_text("") == ""


def test_format_date_text_unrecognized() -> None:
    assert format_date_text("April 8th") == "April 8th"


def test_normalize_time_text_hh_mm() -> None:
    assert normalize_time_text("09:10") == "09:10"


def test_normalize_time_text_chinese() -> None:
    assert normalize_time_text("9点10分") == "09:10"


def test_normalize_time_text_am() -> None:
    assert normalize_time_text("9:10 AM") == "09:10"


def test_normalize_time_text_pm() -> None:
    assert normalize_time_text("3:30 PM") == "15:30"


def test_normalize_time_text_12am() -> None:
    assert normalize_time_text("12:00 AM") == "00:00"


def test_normalize_time_text_12pm() -> None:
    assert normalize_time_text("12:30 PM") == "12:30"


def test_normalize_time_text_half() -> None:
    assert normalize_time_text("9点半") == "09:30"


def test_normalize_time_text_hour_only() -> None:
    assert normalize_time_text("9点") == "09:00"


def test_normalize_time_text_h_suffix() -> None:
    assert normalize_time_text("9h10") == "09:10"


def test_normalize_time_text_empty() -> None:
    assert normalize_time_text("") == ""


def test_normalize_time_text_invalid_minute() -> None:
    assert normalize_time_text("9:99") == ""


def test_extract_date_text_iso() -> None:
    assert extract_date_text("2026-04-08") == "08/04/2026"


def test_extract_date_text_within_text() -> None:
    assert extract_date_text("事故发生在2026-04-08当天") == "08/04/2026"


def test_extract_date_text_dd_mm_yyyy_within() -> None:
    assert extract_date_text("08/04/2026 09:10") == "08/04/2026"


def test_extract_date_text_empty() -> None:
    assert extract_date_text("") == ""


def test_extract_date_text_no_date() -> None:
    assert extract_date_text("no date here") == ""


def test_compose_datetime_text_full() -> None:
    result = compose_datetime_text("2026-04-08 09:10")
    assert result == "08/04/2026 09:10"


def test_compose_datetime_text_date_only() -> None:
    result = compose_datetime_text("2026-04-08")
    assert result == "08/04/2026"


def test_compose_datetime_text_time_with_fallback_date() -> None:
    result = compose_datetime_text("9:10", fallback_date="2026-04-08")
    assert result == "08/04/2026 09:10"


def test_compose_datetime_text_empty() -> None:
    assert compose_datetime_text("") == ""


def test_compose_datetime_text_time_no_fallback() -> None:
    result = compose_datetime_text("9:10")
    assert result == "09:10"


def test_split_affected_date_summary_two_times() -> None:
    date, start, end = split_affected_date_summary("2026-04-08 09:10 - 10:30")
    assert date == "08/04/2026"
    assert start == "09:10"
    assert end == "10:30"


def test_split_affected_date_summary_one_time() -> None:
    date, start, end = split_affected_date_summary("2026-04-08 09:10")
    assert date == "08/04/2026"
    assert start == "09:10"
    assert end == "09:10"


def test_split_affected_date_summary_no_time() -> None:
    date, start, end = split_affected_date_summary("2026-04-08")
    assert date == "08/04/2026"
    assert start == ""
    assert end == ""


def test_split_affected_date_summary_empty() -> None:
    date, start, end = split_affected_date_summary("")
    assert date == ""
    assert start == ""
    assert end == ""


def test_safe_json_list_list_input() -> None:
    assert safe_json_list([1, 2, 3]) == [1, 2, 3]


def test_safe_json_list_json_string() -> None:
    assert safe_json_list("[1, 2, 3]") == [1, 2, 3]


def test_safe_json_list_dict_with_items() -> None:
    assert safe_json_list('{"items": [1, 2]}') == [1, 2]


def test_safe_json_list_invalid_string() -> None:
    assert safe_json_list("not json") == []


def test_safe_json_list_non_list_json() -> None:
    assert safe_json_list('{"key": "value"}') == []


def test_safe_json_list_none() -> None:
    assert safe_json_list(None) == []


def test_extract_appendix_from_rich_text_plain() -> None:
    text, images = extract_appendix_from_rich_text("hello world")
    assert text == "hello world"
    assert images == []


def test_extract_appendix_from_rich_text_with_img() -> None:
    html = '<p>说明</p><p><img alt="chart.png" src="data:image/png;base64,AAAA" /></p>'
    text, images = extract_appendix_from_rich_text(html)
    assert "说明" in text
    assert len(images) == 1
    assert images[0]["name"] == "chart.png"
    assert images[0]["data_url"] == "data:image/png;base64,AAAA"


def test_extract_appendix_from_rich_text_img_no_alt() -> None:
    html = '<img src="data:image/png;base64,BBBB" />'
    text, images = extract_appendix_from_rich_text(html)
    assert len(images) == 1
    assert images[0]["name"] == "appendix-image-1.png"


def test_extract_appendix_from_rich_text_non_image_src_skipped() -> None:
    html = '<img alt="link" src="https://example.com/image.png" />'
    text, images = extract_appendix_from_rich_text(html)
    assert images == []


def test_extract_appendix_from_rich_text_empty() -> None:
    text, images = extract_appendix_from_rich_text("")
    assert text == ""
    assert images == []


def test_extract_appendix_from_rich_text_br_and_p() -> None:
    html = "<p>line1</p><br/><p>line2</p>"
    text, images = extract_appendix_from_rich_text(html)
    assert "line1" in text
    assert "line2" in text


def test_contains_html_tag_true() -> None:
    assert contains_html_tag("<p>hello</p>") is True


def test_contains_html_tag_false() -> None:
    assert contains_html_tag("hello world") is False


def test_contains_html_tag_empty() -> None:
    assert contains_html_tag("") is False


def test_contains_html_tag_none() -> None:
    assert contains_html_tag(None) is False


def test_merge_appendix_images_dedup() -> None:
    img1 = [{"name": "a.png", "data_url": "data:image/png;base64,AAA"}]
    img2 = [{"name": "a.png", "data_url": "data:image/png;base64,AAA"}]
    result = merge_appendix_images(img1, img2)
    assert len(result) == 1


def test_merge_appendix_images_different() -> None:
    img1 = [{"name": "a.png", "data_url": "data:image/png;base64,AAA"}]
    img2 = [{"name": "b.png", "data_url": "data:image/png;base64,BBB"}]
    result = merge_appendix_images(img1, img2)
    assert len(result) == 2


def test_merge_appendix_images_skips_non_dict() -> None:
    result = merge_appendix_images(["not a dict"])
    assert result == []


def test_merge_appendix_images_skips_non_data_image() -> None:
    result = merge_appendix_images([{"name": "a.png", "data_url": "https://example.com/a.png"}])
    assert result == []


def test_merge_appendix_images_empty_name_gets_default() -> None:
    result = merge_appendix_images([{"data_url": "data:image/png;base64,AAA"}])
    assert len(result) == 1
    assert result[0]["name"] == "appendix-image-1.png"


def test_normalize_timeline_items_list_of_dicts() -> None:
    items = [{"time": "09:10", "event": "故障发生", "resolution": "重启服务"}]
    result = normalize_timeline_items(items)
    assert len(result) == 1
    assert result[0]["event"] == "故障发生"
    assert result[0]["resolution"] == "重启服务"


def test_normalize_timeline_items_dict_with_items_key() -> None:
    data = {"items": [{"time": "09:10", "event": "故障发生"}]}
    result = normalize_timeline_items(data)
    assert len(result) == 1


def test_normalize_timeline_items_dict_with_timeline_key() -> None:
    data = {"timeline": [{"time": "09:10", "event": "故障发生"}]}
    result = normalize_timeline_items(data)
    assert len(result) == 1


def test_normalize_timeline_items_string_with_dash() -> None:
    result = normalize_timeline_items("09:10-故障发生")
    assert len(result) == 1
    assert result[0]["event"] == "故障发生"


def test_normalize_timeline_items_string_plain() -> None:
    result = normalize_timeline_items("故障发生")
    assert len(result) == 1
    assert result[0]["event"] == "故障发生"
    assert result[0]["time"] == ""


def test_normalize_timeline_items_list_of_strings() -> None:
    result = normalize_timeline_items(["事件1", "事件2"])
    assert len(result) == 2


def test_normalize_timeline_items_alternate_keys() -> None:
    items = [{"at": "09:10", "description": "故障", "action": "重启"}]
    result = normalize_timeline_items(items)
    assert len(result) == 1
    assert result[0]["event"] == "故障"
    assert result[0]["resolution"] == "重启"


def test_normalize_timeline_items_filters_all_empty() -> None:
    items = [{"time": "", "event": "", "resolution": "", "evidence": ""}]
    result = normalize_timeline_items(items)
    assert len(result) == 0


def test_normalize_status_option_exact() -> None:
    assert normalize_status_option("fault_cleared") == "fault_cleared"
    assert normalize_status_option("temporarily_fixed") == "temporarily_fixed"
    assert normalize_status_option("follow_up_action_required") == "follow_up_action_required"


def test_normalize_status_option_empty() -> None:
    assert normalize_status_option("") == "fault_cleared"


def test_normalize_status_option_follow() -> None:
    assert normalize_status_option("follow up needed") == "follow_up_action_required"


def test_normalize_status_option_temporar() -> None:
    assert normalize_status_option("temporary fix") == "temporarily_fixed"


def test_normalize_status_option_cleared() -> None:
    assert normalize_status_option("cleared") == "fault_cleared"


def test_normalize_status_option_chinese() -> None:
    assert normalize_status_option("已清除") == "fault_cleared"
    assert normalize_status_option("临时") == "temporarily_fixed"
    assert normalize_status_option("跟进") == "follow_up_action_required"


def test_normalize_status_option_unknown() -> None:
    assert normalize_status_option("something else") == "fault_cleared"


def test_status_option_to_text() -> None:
    assert status_option_to_text("fault_cleared") == "Fault has been Cleared"
    assert status_option_to_text("temporarily_fixed") == "Temporarily fixed"
    assert status_option_to_text("follow_up_action_required") == "Follow up action required"


def test_normalize_severity_option_exact() -> None:
    assert normalize_severity_option("not_applicable") == "not_applicable"
    assert normalize_severity_option("minor") == "minor"
    assert normalize_severity_option("major") == "major"


def test_normalize_severity_option_empty() -> None:
    assert normalize_severity_option("") == "not_applicable"


def test_normalize_severity_option_high() -> None:
    assert normalize_severity_option("high") == "major"


def test_normalize_severity_option_critical() -> None:
    assert normalize_severity_option("critical") == "major"


def test_normalize_severity_option_low() -> None:
    assert normalize_severity_option("low") == "minor"


def test_normalize_severity_option_na() -> None:
    assert normalize_severity_option("n/a") == "not_applicable"


def test_normalize_severity_option_chinese() -> None:
    assert normalize_severity_option("严重") == "major"
    assert normalize_severity_option("轻微") == "minor"
    assert normalize_severity_option("不适用") == "not_applicable"


def test_normalize_severity_option_unknown() -> None:
    assert normalize_severity_option("unknown") == "not_applicable"


def test_normalize_severity_option_p0() -> None:
    assert normalize_severity_option("P0") == "major"


def test_normalize_severity_option_p1() -> None:
    assert normalize_severity_option("P1") == "major"


def test_normalize_severity_option_p2() -> None:
    assert normalize_severity_option("P2") == "minor"


def test_normalize_severity_option_p3() -> None:
    assert normalize_severity_option("P3") == "minor"


def test_severity_option_to_text() -> None:
    assert severity_option_to_text("major") == "Major"
    assert severity_option_to_text("minor") == "Minor"
    assert severity_option_to_text("not_applicable") == "Not Applicable"
