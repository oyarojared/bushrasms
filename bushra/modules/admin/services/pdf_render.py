"""Helpers for faster bulk report-card PDF generation."""

from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor
from io import BytesIO


def html_to_pdf_bytes(html: str) -> bytes:
    """Render one HTML document to PDF bytes (used by worker processes)."""
    from weasyprint import HTML

    return HTML(string=html).write_pdf()


def merge_pdf_bytes(parts: list[bytes]) -> bytes:
    """Merge multiple single-document PDF byte strings into one PDF."""
    if not parts:
        return b""
    if len(parts) == 1:
        return parts[0]

    from pypdf import PdfReader, PdfWriter

    writer = PdfWriter()
    for part in parts:
        reader = PdfReader(BytesIO(part))
        for page in reader.pages:
            writer.add_page(page)

    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def render_bulk_report_pdf(html_documents: list[str]) -> bytes:
    """
    Render many report-card HTML documents in parallel, then merge into one PDF.
    Falls back to a single render when only one document is supplied.
    """
    if not html_documents:
        return b""
    if len(html_documents) == 1:
        return html_to_pdf_bytes(html_documents[0])

    workers = min(4, max(1, (os.cpu_count() or 1)))
    with ProcessPoolExecutor(max_workers=workers) as pool:
        pdf_parts = list(pool.map(html_to_pdf_bytes, html_documents))

    return merge_pdf_bytes(pdf_parts)
