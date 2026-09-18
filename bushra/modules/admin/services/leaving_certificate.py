"""Build a Kenya secondary school leaving certificate PDF (ED/B 100).

No student row is created or updated. The printed fields follow the
Ministry of Education blank; extra particulars are not added.
"""

from __future__ import annotations

import base64
import io
import random
import re
from datetime import date
from pathlib import Path

from flask import current_app, render_template
from PIL import Image, ImageOps

from .pdf_render import render_html_to_pdf
from .transfer_letter import student_grade_name

_COAT_OF_ARMS_URI = None
_COAT_OF_ARMS_NAME = "court_of_arms.png"

DEFAULT_FORM_ENROLLED = "ONE"
LEAVING_FORM = "FOUR"

HEADTEACHER_REPORTS = (
    "The pupil has the ability to work towards and achieve set goals. The pupil was industrious and of good conduct.",
    "The pupil is able to apply effort and finish assigned tasks. Conduct in school remained sound and respectful.",
    "The pupil has the capacity to learn, work independently, and meet expectations. Industry and behaviour were good throughout.",
    "The pupil can set to work with purpose and follow tasks through. The pupil maintained good conduct and discipline.",
    "The pupil has the ability to take instruction and produce useful work. Diligence and behaviour were consistently good.",
    "The pupil is able to work with others and achieve shared goals. The pupil kept good conduct in school.",
    "The pupil has the ability to organise work and pursue set goals. The pupil was cooperative and well behaved.",
    "The pupil can concentrate on given work and see it through. Industry and conduct remained positive throughout.",
    "The pupil has the ability to learn from guidance and apply it in assigned work. Good conduct was maintained.",
    "The pupil is able to work steadily towards agreed goals. The pupil showed industry and sound discipline.",
    "The pupil has the ability to handle school tasks with care and effort. Behaviour and respect for rules were good.",
    "The pupil can work under direction and also show initiative. The pupil maintained good conduct throughout.",
    "The pupil has the ability to persist with work until goals are met. Diligence and behaviour were commendable.",
    "The pupil is able to work with purpose and achieve what is asked. The pupil was industrious and of good character.",
)

_GENDERED = re.compile(
    r"\b(he|she|his|her|him|himself|herself|they|them|their|theirs|themselves)\b",
    re.I,
)

_ONES = (
    "",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "eleven",
    "twelve",
    "thirteen",
    "fourteen",
    "fifteen",
    "sixteen",
    "seventeen",
    "eighteen",
    "nineteen",
)
_TENS = (
    "",
    "",
    "twenty",
    "thirty",
    "forty",
    "fifty",
    "sixty",
    "seventy",
    "eighty",
    "ninety",
)
_DAY_WORDS = {
    1: "first",
    2: "second",
    3: "third",
    4: "fourth",
    5: "fifth",
    6: "sixth",
    7: "seventh",
    8: "eighth",
    9: "ninth",
    10: "tenth",
    11: "eleventh",
    12: "twelfth",
    13: "thirteenth",
    14: "fourteenth",
    15: "fifteenth",
    16: "sixteenth",
    17: "seventeenth",
    18: "eighteenth",
    19: "nineteenth",
    20: "twentieth",
    30: "thirtieth",
}


def coat_of_arms_data_uri():
    """Load the coat of arms as gray ink on white paper.

    The shield stays darker than the lions. Blacks are lifted slightly so the
    emblem does not print as a solid silhouette.
    """
    global _COAT_OF_ARMS_URI
    if _COAT_OF_ARMS_URI:
        return _COAT_OF_ARMS_URI
    path = Path(current_app.root_path) / "static" / "logos" / _COAT_OF_ARMS_NAME
    if not path.exists():
        return None
    image = Image.open(path).convert("RGBA")
    paper = Image.new("RGBA", image.size, (255, 255, 255, 255))
    gray = ImageOps.grayscale(Image.alpha_composite(paper, image))
    width, height = gray.size
    corners = (
        gray.getpixel((2, 2))
        + gray.getpixel((width - 3, 2))
        + gray.getpixel((2, height - 3))
        + gray.getpixel((width - 3, height - 3))
    )
    if corners / 4 < 80:
        gray = ImageOps.invert(gray)
    printed = gray
    ink = printed.point(lambda pixel: 255 if pixel < 248 else 0)
    bbox = ink.getbbox()
    if bbox:
        printed = printed.crop(bbox)
    buffer = io.BytesIO()
    printed.convert("L").save(buffer, format="PNG", optimize=True)
    _COAT_OF_ARMS_URI = (
        "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")
    )
    return _COAT_OF_ARMS_URI


def is_leaving_certificate_eligible(student):
    """Only 8-4-4 Form 4 learners on the register."""
    grade = student_grade_name(student)
    return bool(re.search(r"\bform\s*4\b", grade, flags=re.I))


def pick_headteacher_report(index=None):
    if index is None:
        return random.choice(HEADTEACHER_REPORTS)
    return HEADTEACHER_REPORTS[int(index) % len(HEADTEACHER_REPORTS)]


def reports_are_gender_neutral(reports=HEADTEACHER_REPORTS):
    return all(not _GENDERED.search(text) for text in reports)


def _cardinal(number):
    number = int(number)
    if number < 0:
        return ""
    if number < 20:
        return _ONES[number]
    if number < 100:
        tens, ones = divmod(number, 10)
        if ones == 0:
            return _TENS[tens]
        return f"{_TENS[tens]} {_ONES[ones]}"
    if number < 1000:
        hundreds, rest = divmod(number, 100)
        if rest == 0:
            return f"{_ONES[hundreds]} hundred"
        return f"{_ONES[hundreds]} hundred and {_cardinal(rest)}"
    if number < 1_000_000:
        thousands, rest = divmod(number, 1000)
        if rest == 0:
            return f"{_cardinal(thousands)} thousand"
        if rest < 100:
            return f"{_cardinal(thousands)} thousand and {_cardinal(rest)}"
        return f"{_cardinal(thousands)} thousand {_cardinal(rest)}"
    return str(number)


def year_in_words(year):
    year = int(year)
    if 1900 <= year < 2000:
        remainder = year - 1900
        if remainder == 0:
            return "nineteen hundred"
        return f"nineteen {_cardinal(remainder)}"
    if 2000 <= year < 3000:
        rest = year - 2000
        if rest == 0:
            return "two thousand"
        return f"two thousand and {_cardinal(rest)}"
    return _cardinal(year)


def day_in_words(day):
    day = int(day)
    if day in _DAY_WORDS:
        return _DAY_WORDS[day]
    tens, ones = divmod(day, 10)
    tens_word = _TENS[tens]
    ones_word = _DAY_WORDS.get(ones)
    if not tens_word or not ones_word:
        return str(day)
    return f"{tens_word} {ones_word}"


def _ordinal_suffix(day):
    if 10 <= (day % 100) <= 20:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")


def format_date_short(value):
    if not value:
        return ""
    return f"{value.day}{_ordinal_suffix(value.day)} {value.strftime('%B')}, {value.year}"


def date_in_words(value):
    if not value:
        return ""
    return (
        f"{day_in_words(value.day)} {value.strftime('%B')} {year_in_words(value.year)}"
    ).upper()


def _clean(value):
    return " ".join(str(value or "").split()).strip()


_TRAILING_SCHOOL = re.compile(r"(?:\s+school)+\s*$", re.I)


def without_trailing_school(name):
    """Drop a trailing SCHOOL so the printed label is not doubled."""
    cleaned = _clean(name)
    if not cleaned:
        return ""
    if re.fullmatch(r"school", cleaned, flags=re.I):
        return ""
    return _TRAILING_SCHOOL.sub("", cleaned).strip() or cleaned


def school_name_for_certificate(name):
    """Drop a trailing 'School' so the preprinted SCHOOL label is not doubled."""
    return without_trailing_school(name).upper()


def school_address_from_branch(branch):
    if not branch:
        return ""
    parts = []
    address = _clean(getattr(branch, "school_code", None))
    email = _clean(getattr(branch, "email", None))
    if address:
        parts.append(address)
    if email:
        parts.append(email)
    return ", ".join(parts)


def branch_form_defaults(branch):
    today = date.today()
    return {
        "school_name": without_trailing_school(
            getattr(branch, "branch_name", None) if branch else ""
        ),
        "school_address": school_address_from_branch(branch),
        "student_name": "",
        "admission_number": "",
        "date_of_birth": None,
        "date_of_admission": None,
        "form_enrolled": DEFAULT_FORM_ENROLLED,
        "date_of_leaving": None,
        "issue_date": today,
        "headteacher_report": pick_headteacher_report(),
    }


def student_form_defaults(student, branch):
    defaults = branch_form_defaults(branch)
    defaults.update(
        {
            "student_name": _clean(getattr(student, "fullname", None)),
            "admission_number": str(getattr(student, "admission_number", "") or ""),
            "date_of_birth": getattr(student, "dob", None),
            "date_of_admission": getattr(student, "date_of_admission", None),
        }
    )
    return defaults


REPORT_LABEL = "Headteacher's report on the pupil's ability, industry and conduct"
REPORT_MAX_WORDS = 25
REPORT_MAX_LINES = 3
_REPORT_FIRST_WIDTH = 24
_REPORT_LINE_WIDTH = 86


def report_word_count(text):
    return len(_clean(text).split())


def _wrap_words(text, width):
    words = _clean(text).split()
    if not words:
        return []
    lines = []
    current = []
    length = 0
    for word in words:
        extra = len(word) + (1 if current else 0)
        if current and length + extra > width:
            lines.append(" ".join(current))
            current = [word]
            length = len(word)
        else:
            current.append(word)
            length += extra
    if current:
        lines.append(" ".join(current))
    return lines


def _headteacher_report_lines(text):
    words = _clean(text).split()
    if not words:
        return []
    first_words = []
    length = 0
    used = 0
    for word in words:
        extra = len(word) + (1 if first_words else 0)
        if first_words and length + extra > _REPORT_FIRST_WIDTH:
            break
        first_words.append(word)
        length += extra
        used += 1
    lines = [" ".join(first_words)]
    lines.extend(_wrap_words(" ".join(words[used:]), _REPORT_LINE_WIDTH))
    return [line for line in lines if line]


def headteacher_report_fits(text):
    """True when the comment stays on the three dotted certificate lines."""
    return (
        report_word_count(text) <= REPORT_MAX_WORDS
        and len(_headteacher_report_lines(text)) <= REPORT_MAX_LINES
    )


def split_headteacher_report(text):
    """Put the comment on dotted rows. The label itself is never underlined."""
    lines = _headteacher_report_lines(text)
    first = lines[0] if lines else ""
    more = lines[1:REPORT_MAX_LINES]
    blanks = max(0, REPORT_MAX_LINES - (1 + len(more)))
    return first, more, blanks


def leaving_certificate_context(data):
    dob = data.get("date_of_birth")
    admitted = data.get("date_of_admission")
    left = data.get("date_of_leaving")
    issued = data.get("issue_date") or date.today()
    report = _clean(data.get("headteacher_report"))
    student_name = _clean(data.get("student_name"))
    form_enrolled = _clean(data.get("form_enrolled")) or DEFAULT_FORM_ENROLLED
    report_first, report_more, report_blanks = split_headteacher_report(report)

    return {
        "school_name": school_name_for_certificate(data.get("school_name")),
        "school_address": _clean(data.get("school_address")),
        "student_name": student_name.upper(),
        "admission_number": _clean(data.get("admission_number")),
        "date_of_birth": format_date_short(dob),
        "date_of_admission": format_date_short(admitted),
        "date_of_leaving": format_date_short(left),
        "form_enrolled": form_enrolled.upper(),
        "form_left": LEAVING_FORM,
        "form_course": LEAVING_FORM,
        "headteacher_report": report,
        "report_first": report_first,
        "report_more": report_more,
        "report_blanks": report_blanks,
        "issue_date": format_date_short(issued),
        "coat_of_arms_uri": coat_of_arms_data_uri(),
    }


def context_from_form(form):
    return leaving_certificate_context(
        {
            "school_name": form.school_name.data,
            "school_address": form.school_address.data,
            "student_name": form.student_name.data,
            "admission_number": form.admission_number.data,
            "date_of_birth": form.date_of_birth.data,
            "date_of_admission": form.date_of_admission.data,
            "form_enrolled": form.form_enrolled.data,
            "date_of_leaving": form.date_of_leaving.data,
            "issue_date": form.issue_date.data,
            "headteacher_report": form.headteacher_report.data,
        }
    )


def certificate_filename(student_name):
    raw = re.sub(r"[^A-Za-z0-9]+", "_", student_name or "student").strip("_")
    name = raw[:60] or "student"
    return f"{name}_leaving_certificate.pdf"


def render_leaving_certificate_pdf(context):
    html = render_template("student_templates/leaving_certificate.html", **context)
    return render_html_to_pdf(html)
