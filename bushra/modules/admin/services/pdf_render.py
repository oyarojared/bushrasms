"""In-process HTML → PDF rendering. No worker pool (unsafe under gunicorn)."""

from __future__ import annotations

from io import BytesIO


def html_to_pdf_bytes(html: str) -> bytes:
    from weasyprint import HTML

    if not html:
        return b""
    return HTML(string=html).write_pdf()


def merge_pdf_bytes(parts: list[bytes]) -> bytes:
    if not parts:
        return b""
    if len(parts) == 1:
        return parts[0]

    from pypdf import PdfReader, PdfWriter

    writer = PdfWriter()
    for part in parts:
        if not part:
            continue
        reader = PdfReader(BytesIO(part))
        for page in reader.pages:
            writer.add_page(page)

    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def render_html_to_pdf(html: str) -> bytes:
    return html_to_pdf_bytes(html)


def render_html_chunks_to_pdf(html_documents, on_chunk=None) -> bytes:
    parts = []
    total = len(html_documents)
    for index, html in enumerate(html_documents, start=1):
        parts.append(html_to_pdf_bytes(html))
        if on_chunk:
            on_chunk(index, total)
    return merge_pdf_bytes(parts)
