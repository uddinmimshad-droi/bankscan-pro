import gc
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional

import fitz
import pdfplumber
import pytesseract
from pdf2image import convert_from_path

from utils import looks_like_garbage_text


@dataclass
class PageExtraction:
    page_number: int
    text: str
    method: str
    tables: List[List[List[str]]]
    error: Optional[str] = None


@dataclass
class PdfExtractionResult:
    pages: List[PageExtraction]
    total_pages: int
    ocr_pages: int
    digital_pages: int
    failed_pages: List[int]


def inspect_pdf(pdf_path: Path) -> int:
    try:
        document = fitz.open(pdf_path)
    except Exception as exc:
        raise ValueError("The PDF appears to be corrupted or unreadable.") from exc
    try:
        if document.needs_pass:
            raise PermissionError("Password-protected PDFs are not supported.")
        return document.page_count
    finally:
        document.close()


def extract_pdf_text(
    pdf_path: Path,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> PdfExtractionResult:
    total_pages = inspect_pdf(pdf_path)
    if total_pages > 200:
        raise ValueError("PDF exceeds the 200 page limit.")

    pages: List[PageExtraction] = []
    failed_pages: List[int] = []
    digital_pages = 0
    ocr_pages = 0

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for index, page in enumerate(pdf.pages, start=1):
                if progress_callback:
                    progress_callback(index, total_pages, f"Processing page {index} of {total_pages}...")
                method = "digital"
                text = ""
                tables: List[List[List[str]]] = []
                error = None

                try:
                    text = page.extract_text(x_tolerance=1, y_tolerance=3) or ""
                    tables = page.extract_tables() or []
                except Exception as exc:
                    error = f"pdfplumber failed: {exc}"

                if looks_like_garbage_text(text, len(page.images)):
                    method = "ocr"
                    try:
                        images = convert_from_path(
                            str(pdf_path),
                            dpi=150,
                            first_page=index,
                            last_page=index,

                            fmt="png",
                            thread_count=1,
                        )
                        text = pytesseract.image_to_string(images[0], config="--psm 6") if images else ""
                        if images:
                            for img in images:
                                img.close()
                        if looks_like_garbage_text(text):
                            raise ValueError("OCR returned no usable text.")
                        ocr_pages += 1
                        error = None
                    except Exception as exc:
                        failed_pages.append(index)
                        pages.append(PageExtraction(index, "", "failed", [], str(exc)))
                        continue
                else:
                    digital_pages += 1

                pages.append(PageExtraction(index, text, method, tables, error))
                page.flush_cache()
                if index % 10 == 0:
                    gc.collect()
    except PermissionError:
        raise
    except InterruptedError:
        raise
    except Exception as exc:
        raise ValueError("Unable to read the PDF. It may be corrupted or unsupported.") from exc

    return PdfExtractionResult(
        pages=pages,
        total_pages=total_pages,
        ocr_pages=ocr_pages,
        digital_pages=digital_pages,
        failed_pages=failed_pages,
    )
