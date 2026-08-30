"""Build and render class (or single-learner) report-card PDFs."""

from __future__ import annotations

from flask import render_template
from urllib.parse import quote

from ....modals.branches_db import Branch, BranchClasses
from ....modals.students_db import Student
from .grades import live_class_name
from .grading_844 import generate_class_reports, normalize_form_name
from .pdf_render import render_html_chunks_to_pdf, render_html_to_pdf
from .report import get_report_card_data

CHUNK_SIZE = 6


def _student_rows(template, report_data):
    if template == "academics/report_card_844.html":
        return list(report_data or [])
    return list((report_data or {}).get("students") or [])


def _slice_report_data(template, report_data, rows):
    if template == "academics/report_card_844.html":
        return rows
    return {**report_data, "students": rows}


def _download_filename(class_obj, stream, student_id):
    class_name = class_obj.grade_form
    if stream:
        class_name = f"{class_name} {stream}"
    if student_id:
        student_obj = Student.query.get(student_id)
        student_name = student_obj.fullname if student_obj else "learner"
        return f"{student_name}_assessment.pdf"
    return f"{class_name}_Assessment_Reports.pdf"


def build_report_bundle(branch_id, class_id, exam_id, stream=None, student_id=None,
                        include_ranking=True, opening_date=None):
    class_obj = BranchClasses.query.get_or_404(class_id)
    school = Branch.query.get(branch_id)
    normalized_form = normalize_form_name(live_class_name(class_obj.grade_form))
    is_844 = normalized_form in ("Form 3", "Form 4", "IGCSE")

    if is_844:
        if student_id:
            class_reports = generate_class_reports(
                branch_id=branch_id,
                class_id=class_id,
                exam_id=exam_id,
                stream=stream,
                include_student_id=int(student_id),
            )
            report_data = [
                report for report in class_reports
                if report["student_id"] == int(student_id)
            ]
            if not report_data:
                raise ValueError("Student report not found in class rankings")
        else:
            report_data = generate_class_reports(
                branch_id=branch_id,
                class_id=class_id,
                exam_id=exam_id,
                stream=stream,
            )
        template = "academics/report_card_844.html"
    else:
        report_data = get_report_card_data(
            branch_id=branch_id,
            class_id=class_id,
            exam_id=exam_id,
            stream=stream,
            student_id=student_id,
        )
        template = "academics/report_card.html"

    if not report_data:
        raise ValueError("No report data generated")

    extras = {
        "include_ranking": True if is_844 else include_ranking,
        "opening_date": None if is_844 else opening_date,
    }
    filename = _download_filename(class_obj, stream, student_id)
    return {
        "template": template,
        "report_data": report_data,
        "school": school,
        "extras": extras,
        "filename": filename,
        "is_844": is_844,
    }


def render_bundle_pdf(bundle, lite=False, on_progress=None):
    template = bundle["template"]
    report_data = bundle["report_data"]
    school = bundle["school"]
    extras = {**bundle["extras"], "pdf_lite": lite}
    rows = _student_rows(template, report_data)
    total = len(rows) or 1

    if total <= 1:
        if on_progress:
            on_progress(0, total, "Generating PDF…")
        html = render_template(
            template,
            data=report_data,
            school=school,
            **extras,
        )
        pdf = render_html_to_pdf(html)
        if on_progress:
            on_progress(total, total, "Finishing PDF…")
        return pdf

    html_documents = []
    for start in range(0, total, CHUNK_SIZE):
        chunk = rows[start:start + CHUNK_SIZE]
        html_documents.append(
            render_template(
                template,
                data=_slice_report_data(template, report_data, chunk),
                school=school,
                **extras,
            )
        )

    def on_chunk(index, chunk_count):
        if not on_progress:
            return
        done = min(total, index * CHUNK_SIZE)
        on_progress(
            done,
            total,
            f"Generating PDF ({done} of {total})…",
        )

    if on_progress:
        on_progress(0, total, "Generating PDF…")
    return render_html_chunks_to_pdf(html_documents, on_chunk=on_chunk)


def render_class_report_pdf(params, on_progress=None):
    bundle = build_report_bundle(
        branch_id=params["branch_id"],
        class_id=params["class_id"],
        exam_id=params["exam_id"],
        stream=params.get("stream"),
        student_id=params.get("student_id"),
        include_ranking=params.get("include_ranking", True),
        opening_date=params.get("opening_date"),
    )
    pdf = render_bundle_pdf(
        bundle,
        lite=not params.get("student_id"),
        on_progress=on_progress,
    )
    return pdf, bundle["filename"]


def pdf_http_headers(filename):
    safe_filename = quote(filename)
    return {
        "Content-Type": "application/pdf",
        "Content-Disposition": f'attachment; filename="{safe_filename}"',
    }
