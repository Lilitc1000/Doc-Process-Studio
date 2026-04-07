#!/usr/bin/env python3
"""通过 Windows Word 自动刷新目录、页码与日期域。"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph


SCRIPT_DIR = Path(__file__).resolve().parent
PS_SCRIPT = SCRIPT_DIR / "refresh_with_word.ps1"


def is_wsl() -> bool:
    """判断当前是否运行在 WSL。"""
    return "WSL_DISTRO_NAME" in os.environ or "microsoft" in platform.release().lower()


def detect_refresh_backend() -> str | None:
    """检测当前环境可用的文档刷新后端。"""
    if sys.platform.startswith("win") and shutil.which("powershell"):
        return "windows-word"
    if is_wsl() and shutil.which("powershell.exe") and shutil.which("wslpath"):
        return "windows-word"
    return None


def wsl_to_windows_path(path: Path) -> str:
    """把 WSL 路径转换成 Windows 路径，供 powershell.exe 使用。"""
    completed = subprocess.run(
        ["wslpath", "-w", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def refresh_document(document_path: Path) -> None:
    """调用 Windows Word 打开文档、更新字段并保存。"""
    backend = detect_refresh_backend()
    if backend != "windows-word":
        raise RuntimeError("当前环境没有可用的 Word 自动刷新能力。")

    if sys.platform.startswith("win"):
        subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(PS_SCRIPT.resolve()),
                "-DocumentPath",
                str(document_path.resolve()),
            ],
            check=True,
        )
        return

    windows_doc_path = wsl_to_windows_path(document_path.resolve())
    windows_script_path = wsl_to_windows_path(PS_SCRIPT.resolve())
    subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            windows_script_path,
            "-DocumentPath",
            windows_doc_path,
        ],
        check=True,
    )


def patch_revision_history_table_fonts(document_path: Path) -> None:
    """用 python-docx 做合法结构修改，避免手写 XML 造成 Word 修复提示。"""

    def set_run_font(run) -> None:
        run.font.name = "Times New Roman"
        run.font.size = run.font.size or None
        r_pr = run._element.get_or_add_rPr()
        r_fonts = r_pr.rFonts
        if r_fonts is None:
            r_fonts = OxmlElement("w:rFonts")
            r_pr.insert(0, r_fonts)
        r_fonts.set(qn("w:ascii"), "Times New Roman")
        r_fonts.set(qn("w:hAnsi"), "Times New Roman")
        r_fonts.set(qn("w:eastAsia"), "宋体")
        r_fonts.set(qn("w:cs"), "Times New Roman")
        for attr in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
            key = qn(attr)
            if key in r_fonts.attrib:
                del r_fonts.attrib[key]

        sz = r_pr.find(qn("w:sz"))
        if sz is None:
            sz = OxmlElement("w:sz")
            r_pr.append(sz)
        sz.set(qn("w:val"), "20")

        sz_cs = r_pr.find(qn("w:szCs"))
        if sz_cs is None:
            sz_cs = OxmlElement("w:szCs")
            r_pr.append(sz_cs)
        sz_cs.set(qn("w:val"), "20")

    def set_paragraph_default_font(paragraph) -> None:
        p_pr = paragraph._p.get_or_add_pPr()
        r_pr = p_pr.find(qn("w:rPr"))
        if r_pr is None:
            r_pr = OxmlElement("w:rPr")
            p_pr.append(r_pr)

        r_fonts = r_pr.find(qn("w:rFonts"))
        if r_fonts is None:
            r_fonts = OxmlElement("w:rFonts")
            r_pr.insert(0, r_fonts)
        r_fonts.set(qn("w:ascii"), "Times New Roman")
        r_fonts.set(qn("w:hAnsi"), "Times New Roman")
        r_fonts.set(qn("w:eastAsia"), "宋体")
        r_fonts.set(qn("w:cs"), "Times New Roman")
        for attr in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
            key = qn(attr)
            if key in r_fonts.attrib:
                del r_fonts.attrib[key]

        sz = r_pr.find(qn("w:sz"))
        if sz is None:
            sz = OxmlElement("w:sz")
            r_pr.append(sz)
        sz.set(qn("w:val"), "20")

        sz_cs = r_pr.find(qn("w:szCs"))
        if sz_cs is None:
            sz_cs = OxmlElement("w:szCs")
            r_pr.append(sz_cs)
        sz_cs.set(qn("w:val"), "20")

    doc = Document(str(document_path))
    body = doc.element.body
    target_table = None
    found_heading = False
    for child in body.iterchildren():
        if child.tag == qn("w:p"):
            paragraph = Paragraph(child, doc)
            text = paragraph.text.strip()
            found_heading = text == "文檔修訂曆史"
            continue
        if found_heading and child.tag == qn("w:tbl"):
            target_table = Table(child, doc)
            break

    if target_table is None:
        return

    for row in target_table.rows:
        for cell in row.cells:
            for paragraph in cell.paragraphs:
                set_paragraph_default_font(paragraph)
                for run in paragraph.runs:
                    set_run_font(run)

    doc.save(str(document_path))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="通过 Windows Word 刷新 docx 文档中的域。")
    parser.add_argument("--document", help="要刷新的 docx 路径")
    parser.add_argument("--check", action="store_true", help="只检查当前环境是否支持自动刷新")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.check:
        backend = detect_refresh_backend()
        if backend:
            print(backend)
            return
        raise SystemExit(1)

    if not args.document:
        raise SystemExit("未提供 --document")
    document_path = Path(args.document).resolve()
    if not document_path.exists():
        raise SystemExit(f"文档不存在：{document_path}")
    try:
        refresh_document(document_path)
        patch_revision_history_table_fonts(document_path)
    except Exception as exc:
        raise SystemExit(f"文档刷新失败：{exc}") from exc
    print(f"已通过 Word 刷新文档：{document_path}")


if __name__ == "__main__":
    main()
