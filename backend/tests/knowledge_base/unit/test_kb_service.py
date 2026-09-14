"""知识库相关纯函数与会话侧辅助能力的单元测试。

覆盖：文件类型识别、KB 技能 id 解析、KB 工具 schema。
"""

from doc_process_studio.knowledge_base.infrastructure.parsing import detect_file_type

# ── file type detection ──


def test_detect_file_type_pdf() -> None:
    assert detect_file_type("report.pdf") == "pdf"


def test_detect_file_type_docx() -> None:
    assert detect_file_type("document.docx") == "docx"


def test_detect_file_type_xlsx() -> None:
    assert detect_file_type("spreadsheet.xlsx") == "xlsx"


def test_detect_file_type_unsupported_returns_empty() -> None:
    assert detect_file_type("image.png") == ""


def test_detect_file_type_case_insensitive() -> None:
    assert detect_file_type("Report.PDF") == "pdf"


def test_detect_file_type_doc_alias() -> None:
    assert detect_file_type("old.doc") == "docx"


def test_detect_file_type_xls_alias() -> None:
    assert detect_file_type("old.xls") == "xlsx"


# ── kb skill helpers（标识符即 RAGFlow dataset id）──


def test_is_kb_skill_id() -> None:
    from doc_process_studio.chat.infrastructure.streaming.context import is_kb_skill_id

    assert is_kb_skill_id("kb:f05e5a4aadac11f1b9211b18c23af0c8") is True
    assert is_kb_skill_id("document-assistant") is False
    assert is_kb_skill_id("kb:") is True


def test_extract_kb_project_id() -> None:
    from doc_process_studio.chat.infrastructure.streaming.context import extract_kb_project_id

    assert extract_kb_project_id("kb:f05e5a4aadac11f1b9211b18c23af0c8") == "f05e5a4aadac11f1b9211b18c23af0c8"
    assert extract_kb_project_id("kb:") == ""
    assert extract_kb_project_id("other-skill") == ""


def test_build_kb_skill_interface_keeps_dataset_id() -> None:
    from doc_process_studio.chat.infrastructure.streaming.context import build_kb_skill_interface

    interface = build_kb_skill_interface("f05e5a4aadac11f1b9211b18c23af0c8")
    assert interface.id == "kb:f05e5a4aadac11f1b9211b18c23af0c8"
    assert interface.skill_type == "chat"
    assert "f05e5a4aadac11f1b9211b18c23af0c8" in (interface.default_prompt or "")


# ── tool schema ──


def test_build_kb_skill_tools() -> None:
    from doc_process_studio.skill.infrastructure.tool_loop.tool_schema import _build_kb_skill_tools

    tools = _build_kb_skill_tools()
    assert len(tools) == 1
    assert tools[0]["function"]["name"] == "search_knowledge_base"
    assert tools[0]["function"]["parameters"]["required"] == ["query"]


def test_build_skill_tools_kb_prefix() -> None:
    from doc_process_studio.skill.infrastructure.tool_loop.tool_schema import build_skill_tools

    tools = build_skill_tools("kb:f05e5a4aadac11f1b9211b18c23af0c8")
    assert len(tools) == 1
    assert tools[0]["function"]["name"] == "search_knowledge_base"
