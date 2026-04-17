#!/usr/bin/env python3
"""通过 Word 或 LibreOffice 自动刷新目录、页码与日期域。"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph


SCRIPT_DIR = Path(__file__).resolve().parent
PS_SCRIPT = SCRIPT_DIR / "refresh_with_word.ps1"

LIBREOFFICE_BIN_CANDIDATES = [
    "libreoffice",
    "soffice",
    "/usr/bin/libreoffice",
    "/usr/bin/soffice",
    "/snap/bin/libreoffice",
]


def is_wsl() -> bool:
    return "WSL_DISTRO_NAME" in os.environ or "microsoft" in platform.release().lower()


def _find_libreoffice_binary() -> str | None:
    for candidate in LIBREOFFICE_BIN_CANDIDATES:
        if shutil.which(candidate):
            return candidate
    return None


def detect_refresh_backend() -> str | None:
    if is_wsl() and shutil.which("powershell.exe") and shutil.which("wslpath"):
        return "windows-word"
    if sys.platform.startswith("win") and shutil.which("powershell"):
        return "windows-word"
    if _find_libreoffice_binary():
        return "libreoffice"
    return None


def wsl_to_windows_path(path: Path) -> str:
    completed = subprocess.run(
        ["wslpath", "-w", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def refresh_document(document_path: Path) -> None:
    backend = detect_refresh_backend()
    if backend == "libreoffice":
        _refresh_with_libreoffice(document_path)
        return
    if backend == "windows-word":
        _refresh_with_windows_word(document_path)
        return
    raise RuntimeError("当前环境没有可用的文档刷新后端（Word 或 LibreOffice）。")


def _build_libreoffice_env() -> dict[str, str]:
    env = os.environ.copy()
    env["SAL_DISABLE_SYNCHRONOUS_PRINTER_DETECTION"] = "1"
    home = env.get("HOME", "")
    if not home or not os.path.isdir(home) or not os.access(home, os.W_OK):
        env["HOME"] = tempfile.gettempdir()
    return env


def _read_docx_xml(document_path: Path, member_name: str) -> str:
    try:
        with zipfile.ZipFile(document_path) as archive:
            return archive.read(member_name).decode("utf-8", errors="ignore")
    except Exception:
        return ""


def _document_has_toc_field(document_path: Path) -> bool:
    document_xml = _read_docx_xml(document_path, "word/document.xml")
    if not document_xml:
        return False
    return "TOC \\o" in document_xml or "TOC \\\\o" in document_xml


def _document_has_static_toc_entries(document_path: Path) -> bool:
    document_xml = _read_docx_xml(document_path, "word/document.xml")
    if not document_xml:
        return False
    return 'w:anchor="_Toc' in document_xml


def _refresh_with_libreoffice(document_path: Path) -> None:
    libreoffice_bin = _find_libreoffice_binary()
    if not libreoffice_bin:
        raise RuntimeError("未找到 LibreOffice 可执行文件。")

    lo_env = _build_libreoffice_env()
    has_toc_field_before = _document_has_toc_field(document_path)

    with tempfile.TemporaryDirectory(prefix="lo_refresh_") as tmpdir:
        result = subprocess.run(
            [
                libreoffice_bin,
                "--headless",
                "--norestore",
                "--nocrashreport",
                "--writer",
                "--convert-to",
                "docx",
                "--outdir",
                tmpdir,
                str(document_path),
            ],
            capture_output=True,
            text=True,
            timeout=120,
            env=lo_env,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"LibreOffice 刷新失败（退出码 {result.returncode}）：{result.stderr or result.stdout}"
            )

        converted = Path(tmpdir) / document_path.name
        if not converted.exists():
            raise RuntimeError(
                f"LibreOffice 未生成输出文件。stdout: {result.stdout}, stderr: {result.stderr}"
            )

        if has_toc_field_before:
            has_toc_field_after = _document_has_toc_field(converted)
            has_static_toc_after = _document_has_static_toc_entries(converted)
            if not has_toc_field_after and not has_static_toc_after:
                raise RuntimeError(
                    "LibreOffice 刷新后目录字段丢失，已保留原始文档。"
                    "请改用 Windows Word 刷新，或保持原文件在打开时自动更新目录。"
                )

        shutil.copy2(str(converted), str(document_path))


def _refresh_with_windows_word(document_path: Path) -> None:
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
    parser = argparse.ArgumentParser(description="通过 Word 或 LibreOffice 刷新 docx 文档中的域。")
    parser.add_argument("--document", help="要刷新的 docx 路径")
    parser.add_argument("--check", action="store_true", help="只检查当前环境是否支持自动刷新")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    backend = detect_refresh_backend()
    if args.check:
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
    print(f"已通过 {backend} 刷新文档：{document_path}")


if __name__ == "__main__":
    main()
