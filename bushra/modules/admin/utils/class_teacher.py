"""Helpers for teachers assigned as class teacher (one or more classes)."""

from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from ....modals.assessment_db import Exam, ExamPaper
from ....modals.staff_db import ClassTeacher
from ....modals.students_db import Student
from ..services.grades import live_class_name
from ..services.report import build_broadsheet_data


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


list_class_teacher_assignments = list_class_teacher_assignments
get_assignment_for_teacher = get_assignment_for_teacher
students_for_assignment = students_for_assignment
exams_for_assignment = exams_for_assignment
class_exam_overview = class_exam_overview
assignment_has_exam = assignment_has_exam
teacher_owns_student = teacher_owns_student
kenya_whatsapp_number = kenya_whatsapp_number
missing_learner_fields = missing_learner_fields
assignment_covers_student = assignment_covers_student
