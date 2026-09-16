"""Build an official student transfer letter PDF."""

from __future__ import annotations

import re
from datetime import date

from pathlib import Path

from flask import current_app, render_template

from ....modals.staff_db import Teacher
from ..services.grades import live_class_name
from ..services.pdf_render import render_html_to_pdf
from ..services.report import build_pdf_image_data_uri, build_static_image_path


def _is_placeholder_passport(filename):
    name = (filename or "").strip().lower()
    return (not name) or name.startswith("default")


def student_passport_uri(student):
    """Real learner photo only — skip missing files and the default placeholder."""
    filename = (getattr(student, "passport", None) or "").strip()
    if _is_placeholder_passport(filename):
        return None
    base = Path(current_app.root_path).parents[2] / "uploads" / "passports"
    path = base / filename
    if not path.exists():
        return None
    return build_pdf_image_data_uri(path.resolve().as_uri(), max_size=140, quality=82)


def gender_terms(gender):
    """Pronouns that stay correct when gender was never recorded."""
    value = (gender or "").strip().lower()
    if value in {"m", "male", "boy", "b"}:
        return {
            "label": "Male",
            "subject": "He",
            "object": "him",
            "possessive": "his",
            "choice": "his",
            "known": True,
        }
    if value in {"f", "female", "girl", "g"}:
        return {
            "label": "Female",
            "subject": "She",
            "object": "her",
            "possessive": "her",
            "choice": "her",
            "known": True,
        }
    return {
        "label": None,
        "subject": "The student",
        "object": "the student",
        "possessive": "the student's",
        "choice": "his or her",
        "known": False,
    }


def hoi_name(branch):
    raw = (getattr(branch, "branch_head", None) or "").strip()
    if not raw:
        return ""
    teacher = None
    try:
        teacher = Teacher.query.get(int(raw))
    except (TypeError, ValueError):
        teacher = None
    if teacher and teacher.fullname:
        return teacher.fullname.strip()
    return raw


def student_grade_name(student):
    return live_class_name(
        getattr(getattr(student, "class_info", None), "grade_form", "") or ""
    )


def is_transfer_letter_eligible(student):
    """CBE and other grades only — not 8-4-4 Form 3 or Form 4."""
    grade = student_grade_name(student)
    return not re.search(r"\bform\s*[34]\b", grade, flags=re.I)


def default_release_sentence(school_name, terms):
    school = (school_name or "this school").strip()
    return (
        f"This is to certify that the learner named above has been officially "
        f"released by {school} to proceed to a school of {terms['choice']} "
        f"choice due to unavoidable circumstances."
    )


def transfer_letter_context(student, branch, reason=""):
    terms = gender_terms(getattr(student, "gender", None))
    school_name = (getattr(branch, "branch_name", None) or "the school").strip()
    class_name = student_grade_name(student)
    stream = (getattr(student, "stream", None) or "").strip()
    grade_line = class_name
    if stream:
        grade_line = f"{class_name} {stream}".strip()

    cleaned_reason = " ".join((reason or "").split()).strip()
    if cleaned_reason:
        body = (
            f"This is to certify that the learner named above has been "
            f"officially released by {school_name}. The reason for this "
            f"transfer is: {cleaned_reason}."
        )
    else:
        body = default_release_sentence(school_name, terms)

    wish_line = f"We wish {terms['object']} every success in future studies."

    logo_uri = None
    if getattr(branch, "logo", None):
        logo_uri = build_pdf_image_data_uri(
            build_static_image_path(branch.logo),
            max_size=160,
            quality=85,
        )

    return {
        "school_name": school_name,
        "school_address": (getattr(branch, "school_code", None) or "").strip(),
        "school_email": (getattr(branch, "email", None) or "").strip(),
        "school_motto": (getattr(branch, "motto", None) or "").strip(),
        "logo_uri": logo_uri,
        "passport_uri": student_passport_uri(student),
        "student_name": student.fullname,
        "admission_number": student.admission_number,
        "assessment_number": (student.knec_assessment_no or "").strip(),
        "grade_line": grade_line or "—",
        "date_of_birth": getattr(student, "dob", None),
        "gender_label": terms["label"],
        "body": body,
        "wish_line": wish_line,
        "hoi_name": hoi_name(branch),
        "letter_date": date.today(),
        "has_custom_reason": bool(cleaned_reason),
    }


def letter_filename(student):
    raw = re.sub(r"[^A-Za-z0-9]+", "_", student.fullname or "student").strip("_")
    name = raw[:60] or "student"
    return f"{name}_transfer_letter.pdf"


def render_transfer_letter_pdf(context):
    html = render_template("student_templates/transfer_letter.html", **context)
    return render_html_to_pdf(html)
