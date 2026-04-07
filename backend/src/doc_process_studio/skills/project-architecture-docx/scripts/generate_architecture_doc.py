#!/usr/bin/env python3
"""根据项目目录自动生成系统架构与设计文档。"""

from __future__ import annotations

import argparse
import base64
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from datetime import datetime
from functools import lru_cache
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover
    yaml = None

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
DEFAULT_TEMPLATE = SKILL_ROOT / "assets" / "reference-template.docx"
DEFAULT_LOGO = SKILL_ROOT / "assets" / "logo.png"
REFRESH_SCRIPT = SCRIPT_DIR / "refresh_with_word.py"
DEFAULT_DOCUMENT_TITLE = "系統架構與設計文檔"
FONT_ZH = "宋体"
FONT_EN = "Times New Roman"
SIZE_TITLE = 20
SIZE_FOR = 20
SIZE_SYSTEM = 18
SIZE_VERSION = 13
SIZE_DATE = 14
SIZE_COPYRIGHT = 13
SIZE_HEADING_1 = 15
SIZE_HEADING_2 = 14
SIZE_HEADING_3 = 12
SIZE_BODY = 12
SIZE_HEADER = 10
SIZE_FOOTER = 10


def is_wsl() -> bool:
    """判断当前是否运行在 WSL。"""
    return "WSL_DISTRO_NAME" in os.environ or "microsoft" in platform.release().lower()


def find_windows_python_command() -> list[str] | None:
    """在 WSL 中查找可用的 Windows Python 命令。"""
    if not shutil.which("powershell.exe"):
        return None

    py_probe = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", "Get-Command py -ErrorAction SilentlyContinue"],
        capture_output=True,
        text=True,
    )
    if py_probe.returncode == 0 and py_probe.stdout.strip():
        return ["py", "-3"]

    python_probe = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", "Get-Command python -ErrorAction SilentlyContinue"],
        capture_output=True,
        text=True,
    )
    if python_probe.returncode == 0 and python_probe.stdout.strip():
        return ["python"]

    return None


class TraditionalChineseConverter:
    """统一的繁简转换入口，优先使用 OpenCC。"""

    def __init__(self) -> None:
        self.backend = None
        self._converter = None
        self._windows_python_cmd = None

        for module_name in ("opencc", "opencc_python_reimplemented"):
            try:
                module = __import__(module_name, fromlist=["OpenCC"])
                self._converter = module.OpenCC("s2t")
                self.backend = "python-opencc"
                return
            except Exception:
                continue

        if shutil.which("opencc"):
            self.backend = "opencc-cli"
            return

        if (sys.platform.startswith("win") or is_wsl()) and shutil.which("powershell.exe"):
            windows_python_cmd = find_windows_python_command()
            if windows_python_cmd:
                command_prefix = " ".join(windows_python_cmd)
                probe = subprocess.run(
                    [
                        "powershell.exe",
                        "-NoProfile",
                        "-Command",
                        (
                            f"& {command_prefix} -c "
                            "\"from opencc import OpenCC; print('OPENCC_OK')\""
                        ),
                    ],
                    capture_output=True,
                    text=True,
                )
                if "OPENCC_OK" in probe.stdout:
                    self.backend = "windows-python-opencc"
                    self._windows_python_cmd = windows_python_cmd
                    return

        raise RuntimeError(
            "未找到可用的繁简转换后端。请安装 OpenCC，或在 Windows Python 环境中安装 "
            "opencc-python-reimplemented。"
        )

    @lru_cache(maxsize=4096)
    def convert(self, text: str) -> str:
        """把输入文本转换为繁体中文。"""
        if not text:
            return text
        if self.backend == "python-opencc":
            return self._converter.convert(str(text))
        if self.backend == "opencc-cli":
            completed = subprocess.run(
                ["opencc", "-c", "s2t.json"],
                input=str(text),
                capture_output=True,
                text=True,
                check=True,
            )
            return completed.stdout.rstrip("\n")
        if self.backend == "windows-python-opencc":
            encoded = base64.b64encode(str(text).encode("utf-8")).decode("ascii")
            command_prefix = " ".join(self._windows_python_cmd)
            command = (
                "$OutputEncoding = [Console]::OutputEncoding = "
                "[System.Text.UTF8Encoding]::new(); "
                f"$b64='{encoded}'; "
                f"& {command_prefix} -c "
                "\"import base64,sys; from opencc import OpenCC; "
                "text=base64.b64decode(sys.argv[1]).decode('utf-8'); "
                "result=OpenCC('s2t').convert(text); "
                "print(base64.b64encode(result.encode('utf-8')).decode('ascii'))\" "
                "$b64"
            )
            completed = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", command],
                capture_output=True,
                text=True,
                check=True,
            )
            return base64.b64decode(completed.stdout.strip()).decode("utf-8")
        raise RuntimeError("繁简转换后端未初始化。")


CONVERTER = TraditionalChineseConverter()


def to_traditional_text(text: str) -> str:
    """统一使用成熟转换后端把文本转为繁体中文。"""
    return CONVERTER.convert(str(text)) if text is not None else text


def resolve_document_identity(
    project_root: Path,
    explicit_system_name: str | None,
    explicit_document_title: str | None,
) -> tuple[str, str]:
    """脚本层只接收明确身份；缺失时回退到项目默认值。"""
    system_name = (
        to_traditional_text(explicit_system_name).strip()
        if explicit_system_name
        else to_traditional_text(project_root.resolve().name).strip()
    )
    document_title = (
        to_traditional_text(explicit_document_title).strip()
        if explicit_document_title
        else DEFAULT_DOCUMENT_TITLE
    )
    return system_name, document_title


def normalize_heading_text(text: str) -> str:
    """清理标题里手写的数字编号，避免与 Word 自动编号重复。"""
    cleaned = to_traditional_text(str(text).strip())
    cleaned = cleaned.replace("\\.", ".")
    cleaned = re.sub(r"^\s*\d+(?:\.\d+)*\.?\s*", "", cleaned)
    return cleaned.strip()


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            return path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            return path.read_text(encoding="latin-1", errors="ignore")


def load_json(path: Path):
    return json.loads(read_text(path))


def load_yaml(path: Path):
    if yaml is None:
        return {}
    data = yaml.safe_load(read_text(path))
    return data


def clear_document_body(doc: Document) -> None:
    body = doc._element.body
    sect_pr = body.sectPr
    for child in list(body):
        if child is not sect_pr:
            body.remove(child)


def ensure_page_setup(doc: Document) -> None:
    section = doc.sections[0]
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(1.27)
    section.bottom_margin = Cm(1.27)
    section.left_margin = Cm(2.12)
    section.right_margin = Cm(1.95)
    section.header_distance = Cm(1.5)
    section.footer_distance = Cm(1.24)


def set_style_font(style, size: int, bold: bool | None = None) -> None:
    """统一修正文档样式字体，避免 Word 更新域后回退到模板默认字体。"""
    font = style.font
    font.name = FONT_EN
    font.size = Pt(size)
    if bold is not None:
        font.bold = bold

    style_element = style._element
    r_pr = style_element.find(qn("w:rPr"))
    if r_pr is None:
        r_pr = OxmlElement("w:rPr")
        style_element.append(r_pr)

    r_fonts = r_pr.find(qn("w:rFonts"))
    if r_fonts is None:
        r_fonts = OxmlElement("w:rFonts")
        r_pr.append(r_fonts)
    r_fonts.set(qn("w:ascii"), FONT_EN)
    r_fonts.set(qn("w:hAnsi"), FONT_EN)
    r_fonts.set(qn("w:eastAsia"), FONT_ZH)

    sz = r_pr.find(qn("w:sz"))
    if sz is None:
        sz = OxmlElement("w:sz")
        r_pr.append(sz)
    sz.set(qn("w:val"), str(size * 2))

    sz_cs = r_pr.find(qn("w:szCs"))
    if sz_cs is None:
        sz_cs = OxmlElement("w:szCs")
        r_pr.append(sz_cs)
    sz_cs.set(qn("w:val"), str(size * 2))


def set_style_tabs_and_indents(
    style,
    *,
    right_tab_pos: int | None = None,
    right_tab_leader: str | None = None,
    left_indent: int | None = None,
    hanging: int | None = None,
    right_indent: int | None = None,
) -> None:
    """调整目录样式的制表位和缩进，减少右侧空白边距。"""
    style_element = style._element
    p_pr = style_element.find(qn("w:pPr"))
    if p_pr is None:
        p_pr = OxmlElement("w:pPr")
        style_element.append(p_pr)

    tabs = p_pr.find(qn("w:tabs"))
    if tabs is None:
        tabs = OxmlElement("w:tabs")
        p_pr.append(tabs)

    if right_tab_pos is not None:
        for tab in list(tabs):
            if tab.get(qn("w:val")) == "right":
                tabs.remove(tab)
        new_tab = OxmlElement("w:tab")
        new_tab.set(qn("w:val"), "right")
        new_tab.set(qn("w:pos"), str(right_tab_pos))
        if right_tab_leader:
            new_tab.set(qn("w:leader"), right_tab_leader)
        tabs.append(new_tab)

    ind = p_pr.find(qn("w:ind"))
    if ind is None:
        ind = OxmlElement("w:ind")
        p_pr.append(ind)
    if left_indent is not None:
        ind.set(qn("w:left"), str(left_indent))
    if hanging is not None:
        ind.set(qn("w:hanging"), str(hanging))
    if right_indent is not None:
        ind.set(qn("w:right"), str(right_indent))


def find_style_by_name_or_id(doc: Document, style_key: str):
    """按样式名称或 style_id 查找样式，避免触发 doc.styles[style_id] 的弃用警告。"""
    normalized_key = str(style_key).strip().lower()
    if not normalized_key:
        return None

    for style in doc.styles:
        style_name = getattr(style, "name", "")
        style_id = getattr(style, "style_id", "")
        if isinstance(style_name, str) and style_name.strip().lower() == normalized_key:
            return style
        if isinstance(style_id, str) and style_id.strip().lower() == normalized_key:
            return style
    return None


def normalize_document_styles(doc: Document) -> None:
    """修正模板中的关键样式，确保 Word 更新目录和页码后字体仍然正确。"""
    style_map = {
        "Normal": (SIZE_BODY, False),
        "Heading 1": (SIZE_HEADING_1, True),
        "Heading 2": (SIZE_HEADING_2, True),
        "Heading 3": (SIZE_HEADING_3, True),
        "toc 1": (12, True),
        "toc 2": (12, False),
        "toc 3": (12, False),
        "ac": (SIZE_FOOTER, False),
        "ae": (SIZE_FOOTER, False),
        "-Section-Central": (SIZE_TITLE, True),
        "-H-body": (SIZE_HEADING_2, True),
        "-body": (SIZE_HEADING_2, True),
    }
    for style_name, (size, bold) in style_map.items():
        style = find_style_by_name_or_id(doc, style_name)
        if style is not None:
            set_style_font(style, size, bold)

    toc1_style = find_style_by_name_or_id(doc, "toc 1")
    if toc1_style is not None:
        set_style_tabs_and_indents(
            toc1_style,
            right_tab_pos=9300,
            right_tab_leader="dot",
            left_indent=448,
            hanging=448,
            right_indent=0,
        )
    toc2_style = find_style_by_name_or_id(doc, "toc 2")
    if toc2_style is not None:
        set_style_tabs_and_indents(
            toc2_style,
            right_tab_pos=9300,
            right_tab_leader="dot",
            left_indent=1038,
            hanging=750,
            right_indent=0,
        )
    toc3_style = find_style_by_name_or_id(doc, "toc 3")
    if toc3_style is not None:
        set_style_tabs_and_indents(
            toc3_style,
            right_tab_pos=9300,
            right_tab_leader="dot",
            left_indent=1418,
            hanging=938,
            right_indent=0,
        )


def set_run_font(run, size: int | None = None, bold: bool | None = None) -> None:
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.font.bold = bold
    run.font.name = FONT_EN
    run._element.get_or_add_rPr()
    r_fonts = run._element.rPr.rFonts
    r_fonts.set(qn("w:ascii"), FONT_EN)
    r_fonts.set(qn("w:hAnsi"), FONT_EN)
    r_fonts.set(qn("w:eastAsia"), FONT_ZH)
    r_fonts.set(qn("w:cs"), FONT_EN)
    for attr in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        key = qn(attr)
        if key in r_fonts.attrib:
            del r_fonts.attrib[key]


def set_paragraph_default_font(paragraph, size: int, bold: bool = False) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    r_pr = p_pr.find(qn("w:rPr"))
    if r_pr is None:
        r_pr = OxmlElement("w:rPr")
        p_pr.append(r_pr)

    r_fonts = r_pr.find(qn("w:rFonts"))
    if r_fonts is None:
        r_fonts = OxmlElement("w:rFonts")
        r_pr.append(r_fonts)
    r_fonts.set(qn("w:ascii"), FONT_EN)
    r_fonts.set(qn("w:hAnsi"), FONT_EN)
    r_fonts.set(qn("w:eastAsia"), FONT_ZH)
    r_fonts.set(qn("w:cs"), FONT_EN)
    for attr in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        key = qn(attr)
        if key in r_fonts.attrib:
            del r_fonts.attrib[key]

    sz = r_pr.find(qn("w:sz"))
    if sz is None:
        sz = OxmlElement("w:sz")
        r_pr.append(sz)
    sz.set(qn("w:val"), str(size * 2))

    sz_cs = r_pr.find(qn("w:szCs"))
    if sz_cs is None:
        sz_cs = OxmlElement("w:szCs")
        r_pr.append(sz_cs)
    sz_cs.set(qn("w:val"), str(size * 2))

    existing_b = r_pr.find(qn("w:b"))
    if bold and existing_b is None:
        r_pr.append(OxmlElement("w:b"))
    if not bold and existing_b is not None:
        r_pr.remove(existing_b)


def clear_paragraph_numbering(paragraph) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    num_pr = p_pr.find(qn("w:numPr"))
    if num_pr is not None:
        p_pr.remove(num_pr)


def style_paragraph(
    doc: Document,
    paragraph,
    style_name: str,
    fallback_align: WD_ALIGN_PARAGRAPH | None = None,
) -> None:
    """为段落应用样式，优先按样式对象赋值，避免 style_id 查找警告。"""
    resolved_style = find_style_by_name_or_id(doc, style_name)
    if resolved_style is not None:
        paragraph.style = resolved_style
        return
    if fallback_align is not None:
        paragraph.alignment = fallback_align


def add_text_paragraph(doc: Document, text: str, style: str = "Normal", bold: bool = False) -> None:
    paragraph = doc.add_paragraph()
    style_paragraph(doc, paragraph, style)
    run = paragraph.add_run(to_traditional_text(text))
    set_run_font(run, SIZE_BODY, bold)
    if style == "Normal":
        paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        paragraph.paragraph_format.line_spacing = 1.25


def add_heading(
    doc: Document,
    text: str,
    level: int,
    bookmark_name: str | None = None,
    bookmark_id: int | None = None,
) -> None:
    text = normalize_heading_text(text)
    paragraph = doc.add_paragraph()
    style_name = {1: "Heading 1", 2: "Heading 2", 3: "Heading 3"}.get(level, "Heading 1")
    style_paragraph(doc, paragraph, style_name)
    run = paragraph.add_run(text)
    set_run_font(run, {1: SIZE_HEADING_1, 2: SIZE_HEADING_2, 3: SIZE_HEADING_3}.get(level, SIZE_BODY), True)
    if bookmark_name is not None and bookmark_id is not None:
        add_bookmark(paragraph, bookmark_name, bookmark_id)


def shade_cell(cell, fill: str = "D9E2F3") -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def set_cell_text(
    cell,
    text: str,
    bold: bool = False,
    center: bool = False,
    font_size: int = 11,
) -> None:
    cell.text = ""
    paragraph = cell.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER if center else WD_ALIGN_PARAGRAPH.LEFT
    set_paragraph_default_font(paragraph, font_size, bold)
    run = paragraph.add_run(to_traditional_text(text))
    set_run_font(run, font_size, bold)


def apply_table_borders(table) -> None:
    tbl = table._tbl
    tbl_pr = tbl.tblPr
    borders = tbl_pr.first_child_found_in("w:tblBorders")
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tbl_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        element = borders.find(qn(f"w:{edge}"))
        if element is None:
            element = OxmlElement(f"w:{edge}")
            borders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), "8")
        element.set(qn("w:space"), "0")
        element.set(qn("w:color"), "7F7F7F")


def add_table(
    doc: Document,
    headers: list[str],
    rows: list[list[str]],
    style_name: str | None = None,
    header_fill: str | None = "D9E2F3",
    enforce_borders: bool = True,
    font_size: int = 11,
) -> None:
    table = doc.add_table(rows=len(rows) + 1, cols=len(headers))
    if style_name:
        resolved_style = find_style_by_name_or_id(doc, style_name)
        if resolved_style is not None:
            table.style = resolved_style

    for index, header in enumerate(headers):
        set_cell_text(table.rows[0].cells[index], header, bold=True, center=True, font_size=font_size)
        if header_fill:
            shade_cell(table.rows[0].cells[index], header_fill)
    for row_index, row in enumerate(rows, start=1):
        for col_index, value in enumerate(row):
            set_cell_text(table.rows[row_index].cells[col_index], value, font_size=font_size)
            if style_name == "格線表格 4 - 輔色 52":
                shade_cell(table.rows[row_index].cells[col_index], "DEEAF6")
    if enforce_borders:
        apply_table_borders(table)


def add_page_break(doc: Document) -> None:
    doc.add_page_break()


def add_field(paragraph, field_code: str, result_text: str | None = None, result_size: int | None = None) -> None:
    begin_run = paragraph.add_run()
    set_run_font(begin_run, result_size or SIZE_BODY, False)
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    begin.set(qn("w:dirty"), "true")
    begin_run._r.append(begin)

    instr_run = paragraph.add_run()
    set_run_font(instr_run, result_size or SIZE_BODY, False)
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = field_code
    instr_run._r.append(instr)

    separate_run = paragraph.add_run()
    set_run_font(separate_run, result_size or SIZE_BODY, False)
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    separate_run._r.append(separate)

    if result_text is not None:
        result_run = paragraph.add_run(result_text)
        set_run_font(result_run, result_size or SIZE_BODY, False)
        r_pr = result_run._element.get_or_add_rPr()
        no_proof = OxmlElement("w:noProof")
        r_pr.append(no_proof)

    end_run = paragraph.add_run()
    set_run_font(end_run, result_size or SIZE_BODY, False)
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    end_run._r.append(end)


def set_update_fields_on_open(doc: Document) -> None:
    settings = doc.settings.element
    existing = settings.find(qn("w:updateFields"))
    if existing is None:
        existing = OxmlElement("w:updateFields")
        settings.append(existing)
    existing.set(qn("w:val"), "true")


def clear_paragraph(paragraph) -> None:
    for child in list(paragraph._p):
        paragraph._p.remove(child)


def clear_container(container) -> None:
    for paragraph in list(container.paragraphs):
        paragraph._element.getparent().remove(paragraph._element)
    for table in list(container.tables):
        table._element.getparent().remove(table._element)


def hide_table_borders(table) -> None:
    tbl = table._tbl
    tbl_pr = tbl.tblPr
    borders = tbl_pr.first_child_found_in("w:tblBorders")
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tbl_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        element = borders.find(qn(f"w:{edge}"))
        if element is None:
            element = OxmlElement(f"w:{edge}")
            borders.append(element)
        element.set(qn("w:val"), "none")
        element.set(qn("w:sz"), "0")
        element.set(qn("w:space"), "0")
        element.set(qn("w:color"), "auto")


def set_table_line(table, edge: str, size: str = "8", color: str = "808080") -> None:
    tbl = table._tbl
    tbl_pr = tbl.tblPr
    borders = tbl_pr.first_child_found_in("w:tblBorders")
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tbl_pr.append(borders)
    element = borders.find(qn(f"w:{edge}"))
    if element is None:
        element = OxmlElement(f"w:{edge}")
        borders.append(element)
    element.set(qn("w:val"), "single")
    element.set(qn("w:sz"), size)
    element.set(qn("w:space"), "0")
    element.set(qn("w:color"), color)


def configure_header_footer(
    doc: Document,
    system_name: str,
    document_title: str,
    version: str,
    current: datetime,
) -> None:
    section = doc.sections[0]
    section.different_first_page_header_footer = True

    header = section.header
    clear_container(header)
    header_table = header.add_table(rows=1, cols=2, width=Cm(16.8))
    header_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    hide_table_borders(header_table)
    set_table_line(header_table, "bottom")
    left_cell = header_table.rows[0].cells[0]
    right_cell = header_table.rows[0].cells[1]
    left_cell.width = Cm(9.1)
    right_cell.width = Cm(7.7)
    left_cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.BOTTOM
    right_cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.BOTTOM

    left_p = left_cell.paragraphs[0]
    right_p = right_cell.paragraphs[0]
    style_paragraph(doc, left_p, "ae")
    style_paragraph(doc, right_p, "ae")
    clear_paragraph(left_p)
    clear_paragraph(right_p)
    set_paragraph_default_font(left_p, SIZE_FOOTER, False)
    set_paragraph_default_font(right_p, SIZE_FOOTER, False)
    left_run = left_p.add_run(system_name)
    set_run_font(left_run, SIZE_FOOTER, False)
    right_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    right_run = right_p.add_run(to_traditional_text(document_title))
    set_run_font(right_run, SIZE_FOOTER, False)

    footer = section.footer
    clear_container(footer)
    footer_table = footer.add_table(rows=1, cols=3, width=Cm(16.8))
    footer_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    hide_table_borders(footer_table)
    set_table_line(footer_table, "top")
    cells = footer_table.rows[0].cells
    widths = (Cm(5.9), Cm(5.9), Cm(5.0))
    for cell, width in zip(cells, widths):
        cell.width = width
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.BOTTOM
    footer_left = cells[0].paragraphs[0]
    footer_mid = cells[1].paragraphs[0]
    footer_right = cells[2].paragraphs[0]
    for paragraph in (footer_left, footer_mid, footer_right):
        style_paragraph(doc, paragraph, "ac")
        clear_paragraph(paragraph)
        set_paragraph_default_font(paragraph, SIZE_FOOTER, False)
    footer_mid.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer_right.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    left_run = footer_left.add_run(f"Version {version}")
    set_run_font(left_run, SIZE_FOOTER, False)
    add_field(footer_mid, ' TIME  \\@ "MMMM yyyy" ', current.strftime("%B %Y"), SIZE_FOOTER)
    prefix_run = footer_right.add_run("Page ")
    set_run_font(prefix_run, SIZE_FOOTER, False)
    add_field(footer_right, " PAGE   \\* MERGEFORMAT ", "1", SIZE_FOOTER)

    clear_container(section.first_page_header)
    clear_container(section.first_page_footer)


def resolve_logo_path(project_root: Path, explicit_logo: str | None) -> Path | None:
    if explicit_logo:
        path = Path(explicit_logo).resolve()
        return path if path.exists() else None
    if DEFAULT_LOGO.exists():
        return DEFAULT_LOGO
    candidates = [
        project_root / "logo.png",
        project_root / "logo.jpg",
        project_root / "logo.jpeg",
        project_root / "assets" / "logo.png",
        project_root / "assets" / "logo.jpg",
        project_root / "static" / "logo.png",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def add_cover(
    doc: Document,
    system_name: str,
    document_title: str,
    version: str,
    current: datetime,
    logo_path: Path | None,
) -> None:
    for _ in range(2):
        doc.add_paragraph("")
    if logo_path and logo_path.exists():
        logo_paragraph = doc.add_paragraph()
        logo_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        logo_run = logo_paragraph.add_run()
        logo_run.add_picture(str(logo_path), width=Cm(2.8))
        doc.add_paragraph("")
    title = doc.add_paragraph()
    style_paragraph(doc, title, "-Section-Central", WD_ALIGN_PARAGRAPH.CENTER)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run(to_traditional_text(document_title))
    set_run_font(run, SIZE_TITLE, True)

    doc.add_paragraph("")
    connector = doc.add_paragraph()
    style_paragraph(doc, connector, "-Section-Central", WD_ALIGN_PARAGRAPH.CENTER)
    connector.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = connector.add_run("for")
    set_run_font(run, SIZE_FOR, True)

    doc.add_paragraph("")
    system = doc.add_paragraph()
    style_paragraph(doc, system, "Normal", WD_ALIGN_PARAGRAPH.CENTER)
    system.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = system.add_run(system_name)
    set_run_font(run, SIZE_SYSTEM, False)

    for _ in range(5):
        doc.add_paragraph("")
    version_p = doc.add_paragraph()
    style_paragraph(doc, version_p, "Normal", WD_ALIGN_PARAGRAPH.CENTER)
    version_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = version_p.add_run(f"Version: {version}")
    set_run_font(run, SIZE_VERSION, False)

    doc.add_paragraph("")

    date_p = doc.add_paragraph()
    style_paragraph(doc, date_p, "Normal", WD_ALIGN_PARAGRAPH.CENTER)
    date_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = date_p.add_run(current.strftime("%B %Y"))
    set_run_font(run, SIZE_DATE, True)

    doc.add_paragraph("")

    copy_p = doc.add_paragraph()
    style_paragraph(doc, copy_p, "Normal", WD_ALIGN_PARAGRAPH.CENTER)
    copy_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = copy_p.add_run("© The Government of the Hong Kong Special Administrative Region")
    set_run_font(run, SIZE_COPYRIGHT, False)

    doc.add_paragraph("")

    notice_p = doc.add_paragraph()
    style_paragraph(doc, notice_p, "Normal", WD_ALIGN_PARAGRAPH.CENTER)
    notice_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = notice_p.add_run(
        "The contents of this document remain the property of and may not be reproduced in whole or in part without the express permission of the Government of the HKSAR."
    )
    set_run_font(run, SIZE_COPYRIGHT, False)

    add_page_break(doc)


def make_bookmark_name(text: str, index: int) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9\u4e00-\u9fff]+", "-", text).strip("-")
    return f"sec-{index}-{cleaned or 'section'}"


def add_bookmark(paragraph, bookmark_name: str, bookmark_id: int) -> None:
    start = OxmlElement("w:bookmarkStart")
    start.set(qn("w:id"), str(bookmark_id))
    start.set(qn("w:name"), bookmark_name)
    end = OxmlElement("w:bookmarkEnd")
    end.set(qn("w:id"), str(bookmark_id))
    paragraph._p.insert(0, start)
    paragraph._p.append(end)


def add_internal_hyperlink(paragraph, text: str, anchor: str, bold: bool = False) -> None:
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("w:anchor"), anchor)
    hyperlink.set(qn("w:history"), "1")
    run = OxmlElement("w:r")
    r_pr = OxmlElement("w:rPr")
    r_style = OxmlElement("w:rStyle")
    r_style.set(qn("w:val"), "Hyperlink")
    r_pr.append(r_style)
    fonts = OxmlElement("w:rFonts")
    fonts.set(qn("w:ascii"), FONT_EN)
    fonts.set(qn("w:hAnsi"), FONT_EN)
    fonts.set(qn("w:eastAsia"), FONT_ZH)
    r_pr.append(fonts)
    sz = OxmlElement("w:sz")
    sz.set(qn("w:val"), "24" if bold else "22")
    r_pr.append(sz)
    sz_cs = OxmlElement("w:szCs")
    sz_cs.set(qn("w:val"), "24" if bold else "22")
    r_pr.append(sz_cs)
    if bold:
        r_pr.append(OxmlElement("w:b"))
    text_node = OxmlElement("w:t")
    text_node.text = text
    run.append(r_pr)
    run.append(text_node)
    hyperlink.append(run)
    paragraph._p.append(hyperlink)


def add_revision_history(doc: Document, version: str, current: datetime) -> None:
    heading = doc.add_paragraph()
    clear_paragraph_numbering(heading)
    heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = heading.add_run("文檔修訂曆史")
    set_run_font(run, SIZE_HEADING_2, True)
    run.font.underline = True

    add_table(
        doc,
        ["版本號", "提交日期", "編寫人", "檢閱人", "確認?", "贊同?", "備注"],
        [[version, current.strftime("%Y-%m-%d"), "", "", "N", "N", "初稿"]],
        style_name="格線表格 4 - 輔色 52",
        header_fill=None,
        enforce_borders=False,
        font_size=10,
    )
    add_page_break(doc)


def add_toc(doc: Document, outline: list[tuple[int, str, str]]) -> None:
    title = doc.add_paragraph()
    clear_paragraph_numbering(title)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("目錄")
    set_run_font(run, SIZE_HEADING_2, True)
    run.font.underline = True
    paragraph = doc.add_paragraph()
    clear_paragraph_numbering(paragraph)
    add_field(paragraph, r' TOC \o "1-3" \h \z \u ')
    add_page_break(doc)


def normalize_doc_plan(path: Path) -> list[dict]:
    """读取用户提供的文档结构定义。"""
    if path.suffix.lower() in {".yaml", ".yml"}:
        data = load_yaml(path)
    else:
        data = load_json(path)

    if isinstance(data, str):
        normalized = data.strip()
        reparsed = None
        if normalized:
            try:
                reparsed = json.loads(normalized)
            except json.JSONDecodeError:
                if yaml is not None:
                    try:
                        reparsed = yaml.safe_load(normalized)
                    except Exception:
                        reparsed = None
        if isinstance(reparsed, (dict, list)):
            data = reparsed

    if isinstance(data, list):
        chapters = data
    elif isinstance(data, dict):
        chapters = data.get("chapters", [])
    else:
        raise SystemExit(
            "`--doc-plan` 内容格式错误：应为 JSON/YAML 对象或数组，"
            f"当前为 {type(data).__name__}。"
        )

    if not isinstance(chapters, list):
        raise SystemExit("`--doc-plan` 中的 chapters 必须是数组。")
    if any(not isinstance(chapter, dict) for chapter in chapters):
        raise SystemExit("`--doc-plan` 的 chapters 必须是对象数组。")
    return chapters


def text_list(value) -> list[str]:
    """把字符串或字符串列表规整成列表。"""
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return [str(value)]


def render_custom_node(
    doc: Document,
    node: dict,
    level: int,
    bookmark_id: int,
) -> int:
    """遞迴渲染自定義章節節點。"""
    title = normalize_heading_text(str(node.get("title") or node.get("heading") or "").strip())
    if not title:
        return bookmark_id

    add_heading(doc, title, min(level, 3), make_bookmark_name(title, bookmark_id), bookmark_id)
    bookmark_id += 1

    paragraphs = text_list(node.get("content")) or text_list(node.get("paragraphs"))
    for paragraph in paragraphs:
        add_text_paragraph(doc, paragraph)

    for child in node.get("sections", []) or []:
        bookmark_id = render_custom_node(doc, child, level + 1, bookmark_id)
    return bookmark_id


def render_custom_plan(doc: Document, chapters: list[dict]) -> None:
    """按用户提供的文档结构渲染正文。"""
    bookmark_id = 1
    total = len(chapters)
    for index, chapter in enumerate(chapters, start=1):
        bookmark_id = render_custom_node(doc, chapter, 1, bookmark_id)
        if index < total:
            add_page_break(doc)


def build_document(
    project_root: Path,
    output_path: Path,
    system_name: str,
    document_title: str,
    version: str,
    template_path: Path | None,
    logo_path: str | None,
    doc_plan_path: Path | None,
    refresh_with_word: bool,
    fail_on_refresh_error: bool,
) -> bool:
    if not doc_plan_path or not doc_plan_path.exists():
        raise SystemExit("必须提供 --doc-plan；文档标题与正文内容应由模型层先生成，再交给脚本排版。")

    document_title = to_traditional_text(document_title or DEFAULT_DOCUMENT_TITLE).strip()
    system_name = to_traditional_text(system_name).strip()
    doc = Document(str(template_path)) if template_path and template_path.exists() else Document()
    clear_document_body(doc)
    ensure_page_setup(doc)
    normalize_document_styles(doc)
    set_update_fields_on_open(doc)

    current = datetime.now()
    resolved_logo = resolve_logo_path(project_root, logo_path)
    configure_header_footer(doc, system_name, document_title, version, current)
    add_cover(doc, system_name, document_title, version, current, resolved_logo)
    add_revision_history(doc, version, current)
    plan_chapters = normalize_doc_plan(doc_plan_path)
    outline_source: list[tuple[int, str]] = []

    def collect_outline(nodes: list[dict], level: int) -> None:
        for node in nodes:
            title = normalize_heading_text(str(node.get("title") or node.get("heading") or "").strip())
            if title:
                outline_source.append((level, title))
            children = node.get("sections", []) or []
            if isinstance(children, list) and children:
                collect_outline(children, min(level + 1, 3))

    collect_outline(plan_chapters, 1)

    outline = []
    for index, (level, text) in enumerate(outline_source, start=1):
        outline.append((level, text, make_bookmark_name(text, index)))
    add_toc(doc, outline)
    render_custom_plan(doc, plan_chapters)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    refresh_completed = False
    if refresh_with_word:
        try:
            subprocess.run(
                [sys.executable, str(REFRESH_SCRIPT), "--document", str(output_path)],
                check=True,
            )
            refresh_completed = True
        except subprocess.CalledProcessError:
            if fail_on_refresh_error:
                raise
    return refresh_completed


def can_refresh_automatically() -> bool:
    """检测当前环境是否具备自动刷新文档域的能力。"""
    completed = subprocess.run(
        [sys.executable, str(REFRESH_SCRIPT), "--check"],
        capture_output=True,
        text=True,
    )
    return completed.returncode == 0


def detect_refresh_backend_name() -> str | None:
    """返回当前可用的自动刷新后端名称。"""
    completed = subprocess.run(
        [sys.executable, str(REFRESH_SCRIPT), "--check"],
        capture_output=True,
        text=True,
    )
    if completed.returncode == 0:
        return completed.stdout.strip() or "available"
    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="根据项目目录生成系统架构与设计文档 DOCX。")
    parser.add_argument("--project-root", required=True, help="项目根目录")
    parser.add_argument("--output", required=True, help="输出 docx 路径")
    parser.add_argument("--system-name", help="系统名称；若显式提供，则直接采用，不再猜测或清洗")
    parser.add_argument(
        "--document-title",
        help=f"文档标题；若未提供，则回退为 {DEFAULT_DOCUMENT_TITLE}",
    )
    parser.add_argument("--version", default="1.0", help="版本号，默认 1.0")
    parser.add_argument("--template-docx", help="自定义参考 docx 模板路径")
    parser.add_argument("--logo-path", help="封面 logo 图片路径")
    parser.add_argument("--doc-plan", help="自定义文档章节结构，支持 JSON/YAML")
    parser.add_argument(
        "--refresh-with-word",
        dest="refresh_with_word",
        action="store_true",
        default=None,
        help="生成后强制调用可用的本机文档引擎刷新目录与页码",
    )
    parser.add_argument(
        "--no-refresh-with-word",
        dest="refresh_with_word",
        action="store_false",
        help="即使环境支持，也不要自动刷新目录与页码",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    output = Path(args.output).resolve()
    template = Path(args.template_docx).resolve() if args.template_docx else DEFAULT_TEMPLATE
    doc_plan_path = Path(args.doc_plan).resolve() if args.doc_plan else None

    if not project_root.exists():
        raise SystemExit(f"项目根目录不存在：{project_root}")

    system_name, document_title = resolve_document_identity(
        project_root=project_root,
        explicit_system_name=args.system_name,
        explicit_document_title=args.document_title,
    )

    refresh_with_word = args.refresh_with_word
    fail_on_refresh_error = args.refresh_with_word is True
    refresh_backend = detect_refresh_backend_name()
    if refresh_with_word is None:
        refresh_with_word = refresh_backend is not None
        fail_on_refresh_error = False

    refresh_completed = build_document(
        project_root=project_root,
        output_path=output,
        system_name=system_name,
        document_title=document_title,
        version=args.version,
        template_path=template,
        logo_path=args.logo_path,
        doc_plan_path=doc_plan_path,
        refresh_with_word=refresh_with_word,
        fail_on_refresh_error=fail_on_refresh_error,
    )
    print(f"已生成文档：{output}")
    print(f"系统名称：{system_name}")
    print(f"文档标题：{document_title}")
    print(f"刷新后端：{refresh_backend or '不可用'}")
    if refresh_completed:
        print("自动刷新：已执行")
    elif refresh_with_word:
        print("自动刷新：已尝试，但当前执行环境未完成刷新")
    else:
        print("自动刷新：当前环境不可用或已禁用")


if __name__ == "__main__":
    main()
