import logging
from dataclasses import dataclass
from io import BytesIO
from typing import Any

import pdfplumber
import pypdfium2
import pytesseract

logger = logging.getLogger(__name__)

# Minimum text length to consider a page as having extractable text.
# Pages with large images AND text below this threshold are treated as scanned images and processed via OCR.
_MIN_TEXT_LENGTH_FOR_SCANNED = 200

# OCR languages: English + Simplified Chinese + Traditional Chinese
_OCR_LANGUAGES = "chi_sim+eng"


@dataclass
class ParsedPage:
    page_number: int
    text: str
    content_type: str = "text"
    """Content type: 'text' for regular text, 'table' for table-as-markdown,
    'ocr' for OCR-extracted, 'mixed' for text+OCR combined."""


def _table_to_markdown(table: list[list[str | None]]) -> str:
    """Convert a pdfplumber-extracted table to Markdown format."""
    if not table:
        return ""

    # Convert all cells to non-None strings using list comprehension
    str_table = [[(cell or "").replace("\n", " ").strip() for cell in row] for row in table]

    if not str_table:
        return ""

    num_cols = max(len(r) for r in str_table)
    for row in str_table:
        while len(row) < num_cols:
            row.append("")

    lines: list[str] = []
    lines.append("| " + " | ".join(str_table[0]) + " |")
    lines.append("| " + " | ".join(["---"] * num_cols) + " |")
    for row in str_table[1:]:
        lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines)


def _extract_non_table_text(plumber_page: pdfplumber.pdf.Page) -> str:
    """Extract text from a page excluding table regions."""
    found_tables = plumber_page.find_tables()
    if not found_tables:
        return (plumber_page.extract_text() or "").strip()

    bboxes = [t.bbox for t in found_tables]

    def not_in_table(obj: dict[str, Any]) -> bool:
        for x0, top, x1, bottom in bboxes:
            if (
                obj.get("x0", 0) >= x0
                and obj.get("x1", 0) <= x1
                and obj.get("top", 0) >= top
                and obj.get("bottom", 0) <= bottom
            ):
                return False
        return True

    filtered_page = plumber_page.filter(not_in_table)
    return (filtered_page.extract_text() or "").strip()


def _ocr_page(page: pypdfium2._helpers.page.PdfPage) -> str:
    """Render a PDF page to image and run OCR."""
    bitmap = page.render(scale=2)
    pil_image = bitmap.to_pil()
    try:
        result: str = pytesseract.image_to_string(pil_image, lang=_OCR_LANGUAGES)
        return result.strip()
    except Exception:
        logger.warning("OCR failed for page", exc_info=True)
        return ""


def _has_large_images(plumber_page: pdfplumber.pdf.Page) -> bool:
    """Check if a page contains large images (likely scanned content)."""
    for image in plumber_page.images:
        width = abs(image.get("x1", 0) - image.get("x0", 0))
        height = abs(image.get("bottom", 0) - image.get("top", 0))
        if width > 200 and height > 200:
            return True
    return False


def parse_pdf(file_bytes: bytes, file_name: str) -> list[ParsedPage]:
    pages: list[ParsedPage] = []
    try:
        _parse_with_pdfplumber(file_bytes, file_name, pages)
    except Exception:
        logger.warning("pdfplumber failed for %s, falling back to pypdf", file_name, exc_info=True)
        pages.clear()
        _parse_with_pypdf_fallback(file_bytes, file_name, pages)
    return pages


def _parse_with_pdfplumber(
    file_bytes: bytes,
    file_name: str,
    pages: list[ParsedPage],
) -> None:
    with pdfplumber.open(BytesIO(file_bytes)) as pdf:
        pdfium_doc = None

        for page_index, plumber_page in enumerate(pdf.pages, start=1):
            text = (plumber_page.extract_text() or "").strip()
            tables = plumber_page.extract_tables()
            has_large_img = _has_large_images(plumber_page)

            has_tables = any(t and len(t) >= 2 for t in tables)
            is_scanned = len(text) < _MIN_TEXT_LENGTH_FOR_SCANNED and has_large_img
            is_mixed = len(text) >= _MIN_TEXT_LENGTH_FOR_SCANNED and has_large_img

            if has_tables:
                table_markdowns: list[str] = []
                for table in tables:
                    if table and len(table) >= 2:
                        md = _table_to_markdown(table)
                        if md:
                            table_markdowns.append(md)

                if table_markdowns:
                    non_table_text = _extract_non_table_text(plumber_page)
                    page_parts: list[str] = []
                    if non_table_text:
                        page_parts.append(non_table_text)
                    page_parts.extend(table_markdowns)

                    # For mixed pages (table + large images), also run OCR
                    if is_mixed:
                        if pdfium_doc is None:
                            pdfium_doc = pypdfium2.PdfDocument(file_bytes)
                        pdfium_page = pdfium_doc[page_index - 1]
                        ocr_text = _ocr_page(pdfium_page)
                        if ocr_text and ocr_text not in text:
                            page_parts.append("[Image Content]\n" + ocr_text)

                    combined = "\n\n".join(page_parts)
                    pages.append(
                        ParsedPage(
                            page_number=page_index,
                            text=combined,
                            content_type="mixed" if is_mixed else "table",
                        )
                    )
                else:
                    if is_mixed:
                        if pdfium_doc is None:
                            pdfium_doc = pypdfium2.PdfDocument(file_bytes)
                        pdfium_page = pdfium_doc[page_index - 1]
                        ocr_text = _ocr_page(pdfium_page)
                        if ocr_text and ocr_text not in text:
                            combined = text + "\n\n[Image Content]\n" + ocr_text
                            pages.append(
                                ParsedPage(
                                    page_number=page_index,
                                    text=combined,
                                    content_type="mixed",
                                )
                            )
                            continue
                    pages.append(
                        ParsedPage(
                            page_number=page_index,
                            text=text,
                            content_type="text",
                        )
                    )

            elif is_scanned:
                if pdfium_doc is None:
                    pdfium_doc = pypdfium2.PdfDocument(file_bytes)
                pdfium_page = pdfium_doc[page_index - 1]
                ocr_text = _ocr_page(pdfium_page)
                if ocr_text:
                    pages.append(
                        ParsedPage(
                            page_number=page_index,
                            text=ocr_text,
                            content_type="ocr",
                        )
                    )
                elif text:
                    pages.append(
                        ParsedPage(
                            page_number=page_index,
                            text=text,
                            content_type="text",
                        )
                    )

            elif is_mixed:
                # Page has both extractable text and large images
                if pdfium_doc is None:
                    pdfium_doc = pypdfium2.PdfDocument(file_bytes)
                pdfium_page = pdfium_doc[page_index - 1]
                ocr_text = _ocr_page(pdfium_page)
                if ocr_text and ocr_text not in text:
                    combined = text + "\n\n[Image Content]\n" + ocr_text
                    pages.append(
                        ParsedPage(
                            page_number=page_index,
                            text=combined,
                            content_type="mixed",
                        )
                    )
                else:
                    pages.append(
                        ParsedPage(
                            page_number=page_index,
                            text=text,
                            content_type="text",
                        )
                    )

            else:
                if text:
                    pages.append(
                        ParsedPage(
                            page_number=page_index,
                            text=text,
                            content_type="text",
                        )
                    )


def _parse_with_pypdf_fallback(
    file_bytes: bytes,
    file_name: str,
    pages: list[ParsedPage],
) -> None:
    from pypdf import PdfReader

    reader = PdfReader(BytesIO(file_bytes))
    for page_index, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            pages.append(
                ParsedPage(
                    page_number=page_index,
                    text=text,
                    content_type="text",
                )
            )
