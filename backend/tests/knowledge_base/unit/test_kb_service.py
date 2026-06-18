import hashlib

from doc_process_studio.knowledge_base.schemas.common import KBChunkPayload


def _compute_content_hash(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


# ── chunker ──


def test_chunk_text_splits_long_text_by_paragraphs() -> None:
    from doc_process_studio.knowledge_base.service.chunker import chunk_text

    paragraphs = [f"Paragraph {i}. " + "A" * 500 for i in range(10)]
    long_text = "\n\n".join(paragraphs)
    chunks = chunk_text(long_text, max_characters=1800)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk.content) <= 1800


def test_chunk_text_short_text_single_chunk() -> None:
    from doc_process_studio.knowledge_base.service.chunker import chunk_text

    short_text = "Hello world"
    chunks = chunk_text(short_text)
    assert len(chunks) == 1
    assert chunks[0].content == short_text


def test_chunk_text_preserves_metadata() -> None:
    from doc_process_studio.knowledge_base.service.chunker import chunk_text

    text = "Some content here"
    chunks = chunk_text(
        text,
        page_number=1,
        section_title="Intro",
        sheet_name="Sheet1",
    )
    assert chunks[0].page_number == 1
    assert chunks[0].section_title == "Intro"
    assert chunks[0].sheet_name == "Sheet1"


def test_chunk_text_empty_input() -> None:
    from doc_process_studio.knowledge_base.service.chunker import chunk_text

    chunks = chunk_text("")
    assert len(chunks) == 0


def test_chunk_text_normalizes_whitespace() -> None:
    from doc_process_studio.knowledge_base.service.chunker import chunk_text

    text = "Hello\n\n\n\nWorld"
    chunks = chunk_text(text)
    assert len(chunks) == 1
    assert "\n\n\n" not in chunks[0].content


# ── content hash ──


def test_content_hash_deterministic() -> None:
    data = b"test content"
    hash1 = _compute_content_hash(data)
    hash2 = _compute_content_hash(data)
    assert hash1 == hash2


def test_content_hash_different_for_different_content() -> None:
    hash1 = _compute_content_hash(b"content A")
    hash2 = _compute_content_hash(b"content B")
    assert hash1 != hash2


# ── KBChunkPayload ──


def test_kb_chunk_payload_creation() -> None:
    payload = KBChunkPayload(
        content="test content",
        project_name="TestProject",
        document_id="doc-001",
        file_name="test.pdf",
        file_type="pdf",
        page_number=1,
        section_title="Section 1",
        file_path="TestProject/test.pdf",
    )
    assert payload.content == "test content"
    assert payload.project_name == "TestProject"
    assert payload.document_id == "doc-001"
    assert payload.file_name == "test.pdf"
    assert payload.file_type == "pdf"


def test_kb_chunk_payload_defaults() -> None:
    payload = KBChunkPayload(
        content="chunk text",
        project_name="Proj",
        document_id="doc-002",
        file_name="file.docx",
        file_type="docx",
    )
    assert payload.version == 1
    assert payload.is_latest is True
    assert payload.page_number is None
    assert payload.chunk_index == 0


# ── file type detection ──


def test_detect_file_type_pdf() -> None:
    from doc_process_studio.knowledge_base.service.documents import _detect_file_type

    assert _detect_file_type("report.pdf") == "pdf"


def test_detect_file_type_docx() -> None:
    from doc_process_studio.knowledge_base.service.documents import _detect_file_type

    assert _detect_file_type("document.docx") == "docx"


def test_detect_file_type_xlsx() -> None:
    from doc_process_studio.knowledge_base.service.documents import _detect_file_type

    assert _detect_file_type("spreadsheet.xlsx") == "xlsx"


def test_detect_file_type_unsupported_returns_empty() -> None:
    from doc_process_studio.knowledge_base.service.documents import _detect_file_type

    assert _detect_file_type("image.png") == ""


def test_detect_file_type_case_insensitive() -> None:
    from doc_process_studio.knowledge_base.service.documents import _detect_file_type

    assert _detect_file_type("Report.PDF") == "pdf"


def test_detect_file_type_doc_alias() -> None:
    from doc_process_studio.knowledge_base.service.documents import _detect_file_type

    assert _detect_file_type("old.doc") == "docx"


def test_detect_file_type_xls_alias() -> None:
    from doc_process_studio.knowledge_base.service.documents import _detect_file_type

    assert _detect_file_type("old.xls") == "xlsx"


# ── kb skill helpers ──


def test_is_kb_skill_id() -> None:
    from doc_process_studio.chat.service.streaming.context import is_kb_skill_id

    assert is_kb_skill_id("kb:MyProject") is True
    assert is_kb_skill_id("document-assistant") is False
    assert is_kb_skill_id("kb:") is True


def test_extract_kb_project_name() -> None:
    from doc_process_studio.chat.service.streaming.context import extract_kb_project_name

    assert extract_kb_project_name("kb:MyProject") == "MyProject"
    assert extract_kb_project_name("kb:") == ""
    assert extract_kb_project_name("other-skill") == ""


def test_build_kb_skill_interface() -> None:
    from doc_process_studio.chat.service.streaming.context import build_kb_skill_interface

    interface = build_kb_skill_interface("TestProject")
    assert interface.id == "kb:TestProject"
    assert "TestProject" in interface.display_name
    assert interface.skill_type == "chat"


# ── tool schema ──


def test_build_kb_skill_tools() -> None:
    from doc_process_studio.skill.service.tool_loop.tool_schema import _build_kb_skill_tools

    tools = _build_kb_skill_tools("kb:MyProject")
    assert len(tools) == 1
    assert tools[0]["function"]["name"] == "search_knowledge_base"
    assert "MyProject" in tools[0]["function"]["description"]


def test_build_skill_tools_kb_prefix() -> None:
    from doc_process_studio.skill.service.tool_loop.tool_schema import build_skill_tools

    tools = build_skill_tools("kb:TestProject")
    assert len(tools) == 1
    assert tools[0]["function"]["name"] == "search_knowledge_base"
