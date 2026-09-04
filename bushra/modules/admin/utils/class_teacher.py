"""Helpers for teachers assigned as class teacher (one or more classes)."""

from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from ....modals import db
from ....modals.assessment_db import Exam, ExamPaper
from ....modals.staff_db import ClassTeacher
from ....modals.students_db import Student
from ..services.grades import live_class_name
from ..services.report import build_broadsheet_data, compute_full_analysis


_BLANK_STREAMS = ("", "null", "None", "All")


def normalize_class_stream(stream):
    """Treat missing / empty stream values as class-level (None)."""
    if stream is None:
        return None
    if not isinstance(stream, str):
        stream = str(stream)
    stream = stream.strip()
    if stream in _BLANK_STREAMS:
        return None
    return stream


def _row_sort_key(row):
    return (row.updated_at is not None, row.updated_at, row.id or 0)


def _matching_rows(rows, stream):
    target = normalize_class_stream(stream)
    return [
        row for row in rows if normalize_class_stream(row.stream) == target
    ]


def _class_teacher_rows(branch_id, class_id):
    return ClassTeacher.query.filter_by(
        branch_id=branch_id,
        class_id=class_id,
    ).all()


def find_class_teacher_assignment(branch_id, class_id, stream=None):
    """
    Return the assignment that save/read should use for this class + stream.

    Prefers an exact stream match. If none exists, falls back to a class-level
    row (NULL/empty stream) so an older assignment is updated instead of
    leaving a stale teacher in place.
    """
    rows = _class_teacher_rows(branch_id, class_id)
    if not rows:
        return None

    exact = _matching_rows(rows, stream)
    if exact:
        return max(exact, key=_row_sort_key)

    if normalize_class_stream(stream) is not None:
        class_level = _matching_rows(rows, None)
        if class_level:
            return max(class_level, key=_row_sort_key)

    return None


def upsert_class_teacher_assignment(branch_id, class_id, stream, teacher):
    """
    Assign `teacher` as class teacher for this class/stream.

    Updates the existing row when one is found (including a class-level
    leftover), collapses duplicate rows for the same slot, and always sets
    both teacher_id and the teacher relationship so SQLAlchemy does not keep
    the previous teacher loaded.
    """
    stream = normalize_class_stream(stream)
    rows = _class_teacher_rows(branch_id, class_id)
    exact = _matching_rows(rows, stream)
    class_level = _matching_rows(rows, None)

    extras = []
    if exact:
        keeper = max(exact, key=_row_sort_key)
        extras.extend(row for row in exact if row.id != keeper.id)
        # Class-level leftovers make `.first()` lookups keep returning the old
        # teacher after a stream-specific assignment is saved.
        if stream is not None:
            extras.extend(row for row in class_level if row.id != keeper.id)
    elif stream is not None and class_level:
        keeper = max(class_level, key=_row_sort_key)
        keeper.stream = stream
        extras.extend(row for row in class_level if row.id != keeper.id)
    elif class_level:
        keeper = max(class_level, key=_row_sort_key)
        extras.extend(row for row in class_level if row.id != keeper.id)
    else:
        keeper = ClassTeacher(
            branch_id=branch_id,
            class_id=class_id,
            stream=stream,
            teacher_id=teacher.id,
        )
        db.session.add(keeper)

    keeper.teacher = teacher
    keeper.teacher_id = teacher.id

    for extra in extras:
        db.session.delete(extra)

    return keeper


def list_class_teacher_assignments(teacher):
    if not teacher or not getattr(teacher, "id", None):
        return []
    rows = (
        ClassTeacher.query.options(
            joinedload(ClassTeacher.class_),
            joinedload(ClassTeacher.branch),
        )
        .filter(ClassTeacher.teacher_id == teacher.id)
        .all()
    )
    rows.sort(key=lambda row: (row.branch_id or 0, assignment_label(row).lower()))
    return rows


def assignment_label(assignment):
    grade = ""
    if assignment.class_:
        grade = live_class_name(assignment.class_.grade_form)
    stream = (assignment.stream or "").strip()
    if grade and stream:
        return f"{grade} {stream}"
    return grade or stream or "Class"


def get_assignment_for_teacher(teacher, assignment_id):
    if not teacher or not assignment_id:
        return None
    return (
        ClassTeacher.query.options(
            joinedload(ClassTeacher.class_),
            joinedload(ClassTeacher.branch),
        )
        .filter_by(id=assignment_id, teacher_id=teacher.id)
        .first()
    )


def students_for_assignment(assignment):
    if not assignment:
        return []
    query = Student.query.filter_by(
        branch_id=assignment.branch_id,
        class_id=assignment.class_id,
    )
    stream = (assignment.stream or "").strip()
    if stream:
        query = query.filter(Student.stream == stream)
    return query.order_by(
        Student.admission_number.asc(),
        Student.fullname.asc(),
    ).all()


def assignment_covers_student(assignment, student):
    if not assignment or not student:
        return False
    if student.branch_id != assignment.branch_id:
        return False
    if student.class_id != assignment.class_id:
        return False
    stream = (assignment.stream or "").strip()
    if stream:
        return (student.stream or "") == stream
    return True


def teacher_owns_student(teacher, student):
    return any(
        assignment_covers_student(assignment, student)
        for assignment in list_class_teacher_assignments(teacher)
    )


def kenya_whatsapp_number(phone):
    digits = "".join(ch for ch in str(phone or "") if ch.isdigit())
    if digits.startswith("0") and len(digits) == 10:
        digits = "254" + digits[1:]
    elif digits.startswith("7") and len(digits) == 9:
        digits = "254" + digits
    if digits.startswith("254") and len(digits) >= 12:
        return digits
    return ""


def missing_learner_fields(student):
    missing = []
    photo = (student.passport or "").strip()
    if not photo or photo.lower() in ("default.jpg", "default.png"):
        missing.append("Photo")
    if not (student.parent_phone or "").strip():
        missing.append("Parent phone")
    if not (student.nemis_number or "").strip():
        missing.append("NEMIS")
    if not (student.birth_cert_no or "").strip():
        missing.append("Birth cert")
    return missing


def learner_has_photo(student):
    photo = (student.passport or "").strip()
    return bool(photo) and photo.lower() not in ("default.jpg", "default.png")


def learner_initials(name):
    parts = [part for part in str(name or "").split() if part]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def exams_for_assignment(assignment):
    if not assignment:
        return []
    query = (
        Exam.query.join(ExamPaper, ExamPaper.exam_id == Exam.id)
        .filter(
            ExamPaper.branch_id == assignment.branch_id,
            ExamPaper.class_id == assignment.class_id,
            Exam.is_inactive.is_(False),
        )
    )
    stream = (assignment.stream or "").strip()
    if stream:
        query = query.filter(
            or_(
                ExamPaper.stream == stream,
                ExamPaper.stream.is_(None),
                ExamPaper.stream == "",
            )
        )
    return (
        query.distinct()
        .order_by(Exam.year.desc(), Exam.term.desc(), Exam.name.asc())
        .all()
    )


def assignment_has_exam(assignment, exam_id):
    if not assignment or not exam_id:
        return False
    return any(exam.id == exam_id for exam in exams_for_assignment(assignment))


_SHORT_SUBJECT_NAMES = {
    "agriculture": "Agriculture",
    "agriculture and nutrition": "Agriculture",
    "arabic": "Arabic",
    "art and design": "Art",
    "biology": "Biology",
    "business": "Business",
    "business studies": "Business",
    "chemistry": "Chemistry",
    "christian religious education": "CRE",
    "computer science": "Computer",
    "computer studies": "Computer",
    "creative arts": "Creative Arts",
    "creative arts and sports": "Creative Arts",
    "english": "English",
    "english language": "English",
    "environmental activities": "Environment",
    "fasihi ya kiswahili": "Fasihi",
    "french": "French",
    "geography": "Geography",
    "german": "German",
    "health education": "Health",
    "hindu religious education": "HRE",
    "history": "History",
    "history and citizenship": "History",
    "home science": "Home Science",
    "hygiene and nutrition": "Hygiene",
    "ict": "ICT",
    "indigenous language": "Indigenous",
    "indigenous languages": "Indigenous",
    "integrated science": "Int. Science",
    "integrated sciences": "Int. Science",
    "islamic religious education": "IRE",
    "kenyan sign language": "KSL",
    "kiswahili": "Kiswahili",
    "life skills": "Life Skills",
    "literature in english": "Literature",
    "mandarin": "Mandarin",
    "mathematics": "Maths",
    "maths": "Maths",
    "music": "Music",
    "physical education": "PE",
    "physics": "Physics",
    "pre technical studies": "Pre-Technical",
    "pre-technical studies": "Pre-Technical",
    "religious education": "RE",
    "science and technology": "Sci & Tech",
    "social studies": "Social Studies",
}


def _short_subject_label(name):
    raw = " ".join(str(name or "").split())
    if not raw:
        return ""
    known = _SHORT_SUBJECT_NAMES.get(raw.lower())
    if known:
        return known
    if len(raw) <= 12:
        return raw
    shortened = raw.lower()
    for tail in (" education", " studies", " activities", " language"):
        if shortened.endswith(tail) and len(shortened) > len(tail) + 3:
            shortened = shortened[: -len(tail)].strip()
    words = [word for word in shortened.split() if word not in {"and", "&", "of", "the", "ya"}]
    label = " ".join(words).title() if words else raw
    parts = label.split()
    if len(label) > 16 and len(parts) > 2:
        return " ".join(parts[:2])
    return label


def _display_mark(value):
    if value in ("-", "", None):
        return "-"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if number.is_integer():
        return str(int(number))
    return str(value)


def class_exam_overview(assignment, exam_id):
    if not assignment or not exam_id:
        return None
    stream = (assignment.stream or "").strip() or None
    data = build_broadsheet_data(
        assignment.branch_id,
        assignment.class_id,
        exam_id,
        stream,
    )
    subjects = [
        {
            "id": subject.get("id"),
            "name": subject.get("name") or "",
            "label": _short_subject_label(subject.get("name") or ""),
        }
        for subject in (data.get("subjects") or [])
    ]
    rows = []
    for student in data.get("students") or []:
        marks = student.get("marks") or {}
        cells = []
        for subject in subjects:
            info = marks.get(subject["id"])
            if info is None:
                info = marks.get(str(subject["id"]))
            value = info.get("marks") if isinstance(info, dict) else info
            cells.append(_display_mark(value))
        rows.append(
            {
                "id": student.get("id"),
                "fullname": student.get("full_name") or student.get("fullname") or "",
                "admission_number": student.get("admission_number"),
                "marks": cells,
            }
        )
    rows.sort(
        key=lambda row: (
            row["admission_number"] is None,
            row["admission_number"] or 0,
            (row["fullname"] or "").lower(),
        )
    )
    return {
        "exam_name": data.get("exam_name") or "Exam",
        "subjects": subjects,
        "rows": rows,
    }


_TERM_ORDER = {"I": 1, "II": 2, "III": 3}
_CBC_GRADE_COLORS = {
    "EE": "#16a34a",
    "ME": "#2563eb",
    "AE": "#d97706",
    "BE": "#dc2626",
}
_844_GRADE_COLORS = {
    "A": "#15803d",
    "A-": "#16a34a",
    "B+": "#22c55e",
    "B": "#4ade80",
    "B-": "#84cc16",
    "C+": "#eab308",
    "C": "#f59e0b",
    "C-": "#f97316",
    "D+": "#fb923c",
    "D": "#ef4444",
    "D-": "#dc2626",
    "E": "#991b1b",
}
_FALLBACK_CHART_COLORS = [
    "#ff7979",
    "#2563eb",
    "#16a34a",
    "#d97706",
    "#7c3aed",
    "#0891b2",
]


def exam_term_key(term):
    return str(term or "").strip().upper()


def sitting_filters(exams, year=None, term=None):
    years = sorted({exam.year for exam in exams if exam.year}, reverse=True)
    selected_year = year if year in years else (years[0] if years else None)

    terms = sorted(
        {
            exam_term_key(exam.term)
            for exam in exams
            if exam.year == selected_year and exam_term_key(exam.term)
        },
        key=lambda value: _TERM_ORDER.get(value, 99),
    )
    wanted_term = exam_term_key(term)
    selected_term = wanted_term if wanted_term in terms else (terms[-1] if terms else None)

    sitting = [
        exam
        for exam in exams
        if exam.year == selected_year and exam_term_key(exam.term) == selected_term
    ]
    return years, terms, sitting, selected_year, selected_term


def _grade_chart_color(grade, grading_type, index=0):
    palette = _844_GRADE_COLORS if grading_type == "844" else _CBC_GRADE_COLORS
    if grade in palette:
        return palette[grade]
    return _FALLBACK_CHART_COLORS[index % len(_FALLBACK_CHART_COLORS)]


def _ranked_person(row):
    if not row:
        return None
    if row.get("rank_score") is None and not row.get("mean_value"):
        return None
    return {
        "name": row.get("name") or "",
        "admission_number": row.get("admission_number"),
        "mean_value": row.get("mean_value"),
        "score": row.get("score"),
        "position": row.get("position"),
        "gender": row.get("gender"),
    }


def _student_mark_mean(student):
    values = []
    for info in (student.get("marks") or {}).values():
        raw = info.get("marks") if isinstance(info, dict) else info
        if raw in (None, "-", ""):
            continue
        try:
            values.append(float(raw))
        except (TypeError, ValueError):
            continue
    if not values:
        return None
    return int(round(sum(values) / len(values)))


def _incomplete_student_ids(missing_marks):
    ids = set()
    for row in missing_marks or []:
        student_id = row.get("id")
        if student_id is not None:
            ids.add(student_id)
    return ids


def _learner_rank_rows(data, missing_marks):
    """
    Rank learners the same way the marksheet does, but only if every
    allocated paper for the sitting is entered. Incomplete sittings are
    omitted so a few strong papers cannot produce a mean grade.
    """
    grading_type = data.get("grading_type") or "cbc"
    is_844 = grading_type == "844"
    incomplete = _incomplete_student_ids(missing_marks)
    ranked = []

    for student in data.get("students") or []:
        student_id = student.get("id")
        if student_id in incomplete:
            continue

        total_points = student.get("total_points")
        mean_grade = student.get("mean_grade")
        mark_mean = _student_mark_mean(student)

        if is_844:
            if total_points is None or not mean_grade:
                continue
            rank_score = float(total_points)
            display_score = int(round(float(total_points)))
            mean_value = mean_grade
        else:
            if mark_mean is None:
                continue
            rank_score = float(mark_mean)
            display_score = mark_mean
            mean_value = mean_grade or mark_mean

        ranked.append(
            {
                "id": student_id,
                "name": student.get("full_name") or "",
                "admission_number": student.get("admission_number"),
                "gender": student.get("gender"),
                "rank_score": rank_score,
                "score": display_score,
                "mean_value": mean_value,
            }
        )

    ranked.sort(key=lambda row: (-row["rank_score"], row["name"] or ""))
    for position, row in enumerate(ranked, start=1):
        row["position"] = position
    return ranked


def _best_by_gender(ranked, predicate):
    for row in ranked:
        gender = str(row.get("gender") or "").strip().lower()
        if predicate(gender):
            return _ranked_person(row)
    return None


def _subject_means_from_data(data):
    subjects = data.get("subjects") or []
    averages = data.get("subject_averages") or {}
    subject_means = []
    for subject in subjects:
        subject_id = subject.get("id")
        mean = averages.get(subject_id)
        if mean is None:
            mean = averages.get(str(subject_id))
        if mean is not None:
            try:
                mean = int(round(float(mean)))
            except (TypeError, ValueError):
                mean = None
        name = subject.get("name") or ""
        subject_means.append(
            {
                "name": name,
                "label": _short_subject_label(name) or name,
                "mean": mean,
            }
        )
    numeric_means = [row["mean"] for row in subject_means if row["mean"] is not None]
    class_mean = (
        int(round(sum(numeric_means) / len(numeric_means))) if numeric_means else None
    )
    return subject_means, class_mean


def _class_mean_display(data, mark_mean, class_id):
    """
    Class mean + mean grade for the class-teacher summary.
    8-4-4 uses average learner ranking points, then the same
    aggregate scale as class ranking. CBC uses subject-mean score
    against the class grading scheme.
    """
    grading_type = data.get("grading_type") or "cbc"
    if grading_type == "844":
        from ..services.grading_844 import aggregate_to_final_grade

        totals = []
        for student in data.get("students") or []:
            points = student.get("total_points")
            if points is None:
                continue
            try:
                totals.append(float(points))
            except (TypeError, ValueError):
                continue
        if not totals:
            return None, None, "pts"
        class_mean_points = int(round(sum(totals) / len(totals)))
        return (
            class_mean_points,
            aggregate_to_final_grade(class_mean_points),
            "pts",
        )

    if mark_mean is None or not class_id:
        return mark_mean, None, None
    from ..utils import resolve_grade

    info = resolve_grade(class_id, mark_mean) or {}
    return mark_mean, info.get("performance_level"), None


def class_exam_performance(assignment, exam_id):
    if not assignment or not exam_id:
        return None

    stream = (assignment.stream or "").strip() or None
    data = build_broadsheet_data(
        assignment.branch_id,
        assignment.class_id,
        exam_id,
        stream,
    )
    analysis = compute_full_analysis(data)
    subject_means, mark_mean = _subject_means_from_data(data)
    class_mean, class_mean_grade, class_mean_unit = _class_mean_display(
        data, mark_mean, assignment.class_id
    )

    students = data.get("students") or []
    entered = 0
    for student in students:
        marks = student.get("marks") or {}
        has_mark = False
        for info in marks.values():
            value = info.get("marks") if isinstance(info, dict) else info
            if value not in (None, "-", ""):
                has_mark = True
                break
        if has_mark:
            entered += 1

    missing = data.get("missing_marks") or []
    grading_type = data.get("grading_type") or "cbc"
    grade_rows = analysis.get("overall_grade_analysis") or []
    grade_distribution = [
        {
            "grade": row.get("grade"),
            "count": row.get("count") or 0,
            "color": _grade_chart_color(row.get("grade"), grading_type, index),
        }
        for index, row in enumerate(grade_rows)
        if row.get("grade")
    ]

    ranked = _learner_rank_rows(data, missing)
    top_students = []
    for row in ranked[:5]:
        person = _ranked_person(row)
        if person:
            top_students.append(person)

    weakest = sorted(
        [row for row in subject_means if row["mean"] is not None],
        key=lambda row: row["mean"],
    )[:3]

    return {
        "exam_name": data.get("exam_name") or "Exam",
        "grading_type": grading_type,
        "is_844": grading_type == "844",
        "grade_label": analysis.get("grade_label") or "Mean Score",
        "score_label": analysis.get("score_label") or "Total Marks",
        "overall_grade_title": analysis.get("overall_grade_title")
        or "Grade distribution",
        "summary": {
            "class_mean": class_mean,
            "class_mean_grade": class_mean_grade,
            "class_mean_unit": class_mean_unit,
            "class_mean_grade_color": (
                _grade_chart_color(class_mean_grade, grading_type)
                if class_mean_grade
                else None
            ),
            "total_learners": data.get("total_learners") or len(students),
            "entered": entered,
            "missing_count": len(missing),
        },
        "subject_means": subject_means,
        "weakest_subjects": weakest,
        "grade_distribution": grade_distribution,
        "top_students": top_students,
        "best_boy": _best_by_gender(
            ranked, lambda gender: gender.startswith("m")
        ),
        "best_girl": _best_by_gender(
            ranked, lambda gender: gender.startswith("f")
        ),
        "missing_marks": missing[:8],
        "missing_more": max(0, len(missing) - 8),
        "charts": {
            "subject_labels": [row["label"] for row in subject_means],
            "subject_names": [row["name"] for row in subject_means],
            "subject_values": [row["mean"] for row in subject_means],
            "grade_labels": [row["grade"] for row in grade_distribution],
            "grade_values": [row["count"] for row in grade_distribution],
            "grade_colors": [row["color"] for row in grade_distribution],
        },
    }


def dashboard_class_performance(teacher):
    assignments = list_class_teacher_assignments(teacher)
    if not assignments:
        return None

    assignment = assignments[0]
    exams = exams_for_assignment(assignment)
    snapshot = {
        "assignment_id": assignment.id,
        "class_label": assignment_label(assignment),
        "exam_id": None,
        "exam_name": None,
        "year": None,
        "term": None,
        "class_mean": None,
        "class_mean_grade": None,
        "class_mean_unit": None,
        "charts": {"subject_labels": [], "subject_values": []},
    }
    if not exams:
        return snapshot

    exam = exams[0]
    snapshot["exam_id"] = exam.id
    snapshot["exam_name"] = exam.name
    snapshot["year"] = exam.year
    snapshot["term"] = exam_term_key(exam.term)

    try:
        stream = (assignment.stream or "").strip() or None
        data = build_broadsheet_data(
            assignment.branch_id,
            assignment.class_id,
            exam.id,
            stream,
        )
        subject_means, mark_mean = _subject_means_from_data(data)
        class_mean, class_mean_grade, class_mean_unit = _class_mean_display(
            data, mark_mean, assignment.class_id
        )
        snapshot["class_mean"] = class_mean
        snapshot["class_mean_grade"] = class_mean_grade
        snapshot["class_mean_unit"] = class_mean_unit
        snapshot["charts"] = {
            "subject_labels": [row["label"] for row in subject_means],
            "subject_names": [row["name"] for row in subject_means],
            "subject_values": [row["mean"] for row in subject_means],
        }
    except Exception:
        pass
    return snapshot


list_class_teacher_assignments = list_class_teacher_assignments
get_assignment_for_teacher = get_assignment_for_teacher
students_for_assignment = students_for_assignment
exams_for_assignment = exams_for_assignment
class_exam_overview = class_exam_overview
class_exam_performance = class_exam_performance
dashboard_class_performance = dashboard_class_performance
sitting_filters = sitting_filters
assignment_has_exam = assignment_has_exam
teacher_owns_student = teacher_owns_student
kenya_whatsapp_number = kenya_whatsapp_number
missing_learner_fields = missing_learner_fields
assignment_covers_student = assignment_covers_student
