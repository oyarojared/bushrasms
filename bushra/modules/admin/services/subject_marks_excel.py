"""One subject, one sheet: admission number, full name, and marks."""

from io import BytesIO

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill

ADM_HEADERS = {
    "adm",
    "adm no",
    "adm no.",
    "admission",
    "admission no",
    "admission no.",
    "admission number",
}
MARK_HEADERS = {"mark", "marks", "score"}


def subject_marks_filename(class_name, subject_name, exam_name):
    raw = f"{class_name or 'class'}_{subject_name or 'subject'}_{exam_name or 'exam'}_marks"
    safe = "".join(ch if ch.isalnum() or ch in (" ", "_", "-") else " " for ch in raw)
    safe = "_".join(part for part in safe.split() if part)
    return f"{safe or 'subject_marks'}.xlsx"


def build_subject_marks_workbook(students, marks_by_student_id):
    """A sheet a teacher can fill and upload again."""
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Marks"

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="923006")
    center = Alignment(horizontal="center", vertical="center")
    left = Alignment(horizontal="left", vertical="center")

    for column, label in enumerate(("Adm No", "Full name", "Marks"), start=1):
        cell = sheet.cell(row=1, column=column, value=label)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center

    ordered = sorted(
        students,
        key=lambda student: (
            int(student.admission_number)
            if str(student.admission_number).isdigit()
            else 10**9,
            str(student.admission_number),
        ),
    )
    for row_index, student in enumerate(ordered, start=2):
        sheet.cell(row=row_index, column=1, value=int(student.admission_number) if str(student.admission_number).isdigit() else student.admission_number).alignment = center
        name = getattr(student, "fullname", None) or getattr(student, "full_name", "")
        sheet.cell(row=row_index, column=2, value=name).alignment = left
        mark = marks_by_student_id.get(student.id)
        mark_cell = sheet.cell(row=row_index, column=3)
        mark_cell.alignment = center
        if mark is None:
            mark_cell.value = None
        else:
            number = float(mark)
            mark_cell.value = int(number) if number == int(number) else number

    sheet.column_dimensions["A"].width = 14
    sheet.column_dimensions["B"].width = 32
    sheet.column_dimensions["C"].width = 12
    sheet.auto_filter.ref = f"A1:C{max(1, len(ordered) + 1)}"
    sheet.freeze_panes = "A2"

    payload = BytesIO()
    workbook.save(payload)
    payload.seek(0)
    return payload


def _header_key(value):
    return " ".join(str(value or "").strip().lower().replace("_", " ").split())


def _admission_key(value):
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, float):
        if not value.is_integer():
            return None
        return str(int(value))
    if isinstance(value, int):
        return str(value)
    text = str(value).strip()
    if not text:
        return None
    if text.endswith(".0") and text[:-2].isdigit():
        text = text[:-2]
    if text.isdigit():
        return str(int(text))
    return None


def _mark_value(value):
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError("A mark must be a number.")
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        value = text
    try:
        return float(value)
    except (TypeError, ValueError) as error:
        raise ValueError("A mark must be a number.") from error


def parse_subject_marks_workbook(source):
    """Rows from a filled subject sheet. A blank mark means clear that learner."""
    try:
        workbook = load_workbook(source, data_only=True, read_only=True)
    except Exception as error:
        raise ValueError("Use the Excel sheet downloaded from this page (.xlsx).") from error

    sheet = workbook.active
    header_row = None
    adm_col = None
    mark_col = None
    for row_index, row in enumerate(sheet.iter_rows(max_row=8, values_only=True), start=1):
        found_adm = None
        found_mark = None
        for column, value in enumerate(row):
            key = _header_key(value)
            if key in ADM_HEADERS:
                found_adm = column
            elif key in MARK_HEADERS:
                found_mark = column
        if found_adm is not None and found_mark is not None:
            header_row = row_index
            adm_col = found_adm
            mark_col = found_mark
            break

    if header_row is None:
        raise ValueError("The sheet needs columns named Adm No, Full name, and Marks.")

    rows = []
    seen = set()
    for row in sheet.iter_rows(min_row=header_row + 1, values_only=True):
        if row is None:
            continue
        adm_raw = row[adm_col] if adm_col < len(row) else None
        mark_raw = row[mark_col] if mark_col < len(row) else None
        if adm_raw is None and (mark_raw is None or str(mark_raw).strip() == ""):
            continue
        admission = _admission_key(adm_raw)
        if admission is None:
            raise ValueError("Every row with a mark needs an admission number.")
        if admission in seen:
            raise ValueError(f"Admission {admission} is listed more than once.")
        seen.add(admission)
        try:
            marks = _mark_value(mark_raw)
        except ValueError as error:
            raise ValueError(f"Admission {admission}: {error}") from error
        rows.append({"admission_number": admission, "marks": marks})

    if not rows:
        raise ValueError("The sheet has no learners to upload.")
    return rows


def match_subject_mark_rows(students, rows, marks_out_of):
    """Pair sheet rows with the learners on the marks screen."""
    by_admission = {str(student.admission_number): student for student in students}
    updates = []
    skipped = []
    errors = []
    limit = int(marks_out_of or 100)
    for row in rows:
        admission = row["admission_number"]
        student = by_admission.get(admission)
        if student is None:
            skipped.append(admission)
            continue
        marks = row["marks"]
        if marks is not None and (marks < 0 or marks > limit):
            errors.append(
                f"Admission {admission} has {marks:g}, which is outside 0 to {limit}."
            )
            continue
        updates.append({"student_id": student.id, "marks": marks})
    return updates, skipped, errors
