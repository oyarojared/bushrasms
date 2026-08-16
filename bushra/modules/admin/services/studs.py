from ....modals import db
from ....modals.students_db import Student
from ....modals.assessment_db import StudentExamMark, ExamPaper, Exam, GradeGradingScheme
from ....modals.subjects_db import Subject, Lesson
from ....modals.branches_db import BranchClasses
from sqlalchemy import func

from ..utils.general_utils import resolve_grade
from ..services.grading_844 import (
    normalize_form_name,
    is_844_form,
    resolve_844_grade,
    subject_comment,
    compute_844_aggregate,
)

import threading

branch_locks = {}


def get_branch_lock(branch_id):
    if branch_id not in branch_locks:
        branch_locks[branch_id] = threading.Lock()
    return branch_locks[branch_id]


def _format_mark(value):
    if value is None:
        return None
    number = float(value)
    if number.is_integer():
        return int(number)
    return round(number, 1)


def _term_sort_key(term):
    return {"I": 1, "II": 2, "III": 3}.get(term, 0)


def _cbe_overall_grade(class_id, raw_total, subjects):
    total_out_of = sum(s.get("marks_out_of") or 100 for s in subjects)
    if not total_out_of:
        return {
            "performance_level": None,
            "points": None,
            "descriptor": None,
        }

    percentage = (raw_total / total_out_of) * 100
    scheme_link = GradeGradingScheme.query.filter_by(grade_id=class_id).first()

    if not scheme_link or not scheme_link.scheme:
        return {
            "performance_level": None,
            "points": None,
            "descriptor": None,
        }

    for boundary in scheme_link.scheme.boundaries:
        if boundary.min_score <= percentage <= boundary.max_score:
            return {
                "performance_level": boundary.performance_level,
                "points": boundary.points,
                "descriptor": boundary.descriptor,
            }

    return {
        "performance_level": None,
        "points": None,
        "descriptor": None,
    }


def _subject_teacher_initials(branch_id, class_id, stream, subject_id):
    lesson = Lesson.query.filter_by(
        branch_id=branch_id,
        class_id=class_id,
        stream=stream or None,
        subject_id=subject_id,
    ).first()

    if not lesson or not lesson.teacher:
        return None

    names = lesson.teacher.fullname.strip().split()
    if not names:
        return None

    return ".".join(name[0].upper() for name in names)


def get_student_academic_history(student_id):
    """
    Return exam results for a student grouped by exam, newest first.
    """
    rows = (
        db.session.query(StudentExamMark, ExamPaper, Exam, Subject, BranchClasses)
        .join(ExamPaper, StudentExamMark.exam_paper_id == ExamPaper.id)
        .join(Exam, ExamPaper.exam_id == Exam.id)
        .join(Subject, ExamPaper.subject_id == Subject.id)
        .join(BranchClasses, ExamPaper.class_id == BranchClasses.id)
        .filter(StudentExamMark.student_id == student_id)
        .order_by(
            Exam.year.desc(),
            Exam.term.desc(),
            Exam.name.asc(),
            Subject.name.asc(),
        )
        .all()
    )

    exams_map = {}

    for mark, paper, exam, subject, class_ in rows:
        exam_key = exam.id

        if exam_key not in exams_map:
            normalized_form = normalize_form_name(class_.grade_form)
            exams_map[exam_key] = {
                "exam_id": exam.id,
                "branch_id": paper.branch_id,
                "class_id": paper.class_id,
                "name": exam.name,
                "year": exam.year,
                "term": exam.term,
                "title": f"{exam.name} · Term {exam.term} · {exam.year}",
                "grade_form": class_.grade_form,
                "stream": paper.stream or "",
                "is_844": is_844_form(normalized_form),
                "subjects": [],
                "_total_raw": 0.0,
            }

        entry = exams_map[exam_key]
        teacher = _subject_teacher_initials(
            paper.branch_id,
            paper.class_id,
            paper.stream,
            subject.id,
        )

        if entry["is_844"]:
            letter_grade, points = resolve_844_grade(mark.marks, subject.category)
            entry["subjects"].append(
                {
                    "subject_name": subject.name,
                    "subject_code": subject.code,
                    "subject_category": subject.category,
                    "marks": _format_mark(mark.marks),
                    "marks_out_of": paper.marks_out_of,
                    "grade": letter_grade,
                    "points": points,
                    "comment": subject_comment(mark.marks),
                    "teacher_initials": teacher,
                }
            )
        else:
            grade_info = resolve_grade(paper.class_id, mark.marks)
            entry["subjects"].append(
                {
                    "subject_name": subject.name,
                    "subject_code": subject.code,
                    "subject_category": subject.category,
                    "marks": _format_mark(mark.marks),
                    "marks_out_of": paper.marks_out_of,
                    "performance_level": grade_info.get("performance_level"),
                    "grade": grade_info.get("performance_level"),
                    "points": grade_info.get("points"),
                    "comment": grade_info.get("descriptor"),
                    "teacher_initials": teacher,
                }
            )

        entry["_total_raw"] += float(mark.marks or 0)

    history = []

    for exam in exams_map.values():
        count = len(exam["subjects"])
        raw_total = exam.pop("_total_raw", 0.0)
        exam["subject_count"] = count
        exam["total_marks"] = _format_mark(raw_total)
        exam["average"] = _format_mark(raw_total / count) if count else None

        if exam["is_844"]:
            point_rows = [
                {"points": s["points"], "category": s["subject_category"]}
                for s in exam["subjects"]
                if s.get("points") is not None
            ]
            agg = compute_844_aggregate(point_rows)
            exam["summary"] = {
                "total_points": agg["total_points"],
                "mean_grade": agg["mean_grade"],
                "total_marks": exam["total_marks"],
                "average": exam["average"],
            }
        else:
            overall = _cbe_overall_grade(exam["class_id"], raw_total, exam["subjects"])
            exam["summary"] = {
                "total_marks": exam["total_marks"],
                "average": exam["average"],
                "performance_level": overall["performance_level"],
                "points": overall["points"],
                "descriptor": overall["descriptor"],
            }

        history.append(exam)

    history.sort(
        key=lambda item: (
            -item["year"],
            -_term_sort_key(item["term"]),
            item["name"].lower(),
        )
    )

    return history


def get_next_adm_no(branch_id):
    lock = get_branch_lock(branch_id)

    with lock:
        max_adm = (
            db.session.query(func.max(Student.admission_number))
            .filter(Student.branch_id == branch_id)
            .scalar()
        )

        return (max_adm or 0) + 1