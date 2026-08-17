from ....modals import db
from collections import defaultdict
from sqlalchemy import or_
from sqlalchemy.orm import joinedload
from ....modals.students_db import Student, StudentSubjectAllocation
from ....modals.staff_db import Teacher, ClassTeacher
from ....modals.subjects_db import Lesson, Subject
from ....modals.assessment_db import Exam, ExamPaper, StudentExamMark
from ....modals.branches_db import Branch, BranchClasses
from .report import build_passport_path, build_static_image_path, build_pdf_image_data_uri


# =========================================================
# Utilities
# =========================================================
def normalize_form_name(form_name: str) -> str:
    if not form_name:
        return ""
    form_name = form_name.strip().lower()
    if "form" in form_name:
        num = "".join(filter(str.isdigit, form_name))
        return f"Form {num}"
    
    # Handle IGCSE class
    ig_name = form_name.strip().lower()
    if "igcse" in ig_name:
        return "IGCSE"
    
    return form_name.title()


def is_844_form(normalized_form: str) -> bool:
    return normalized_form in ("Form 3", "Form 4", "IGCSE")


def teacher_initials(teacher: Teacher):
    if not teacher:
        return None
    names = teacher.fullname.split()
    # Take the first letter of the first two names, uppercase, join with dot
    initials = ".".join(n[0].upper() for n in names[:2])
    return initials

def performance_remark(points):
    # Remarks based on total points
    if points >= 75:
        return "Excellent performance. Keep it up!"
    elif points >= 65:
        return "Very good work. Aim higher."
    elif points >= 50:
        return "Good effort. Can do better."
    elif points >= 40:
        return "Fair performance. Put more effort."
    else:
        return "Below average. Needs serious improvement."


# =========================================================
# KCSE GRADE → POINTS (SOURCE OF TRUTH)
# =========================================================
GRADE_POINTS = {
    "A": 12,
    "A-": 11,
    "B+": 10,
    "B": 9,
    "B-": 8,
    "C+": 7,
    "C": 6,
    "C-": 5,
    "D+": 4,
    "D": 3,
    "D-": 2,
    "E": 1,
}


# =========================================================
# STATIC 8-4-4 GRADING (MARK → GRADE ONLY)
# =========================================================
EIGHT_FOUR_FOUR_GRADING = {
    "LANGUAGES": [
        (0, 29, "E"),
        (30, 34, "D-"),
        (35, 39, "D"),
        (40, 44, "D+"),
        (45, 49, "C-"),
        (50, 54, "C"),
        (55, 59, "C+"),
        (60, 64, "B-"),
        (65, 69, "B"),
        (70, 74, "B+"),
        (75, 79, "A-"),
        (80, 100, "A"),
    ],
    "SCIENCE & TECHNOLOGY": [
        (0, 24, "E"),
        (25, 29, "D-"),
        (30, 34, "D"),
        (35, 39, "D+"),
        (40, 44, "C-"),
        (45, 49, "C"),
        (50, 54, "C+"),
        (55, 59, "B-"),
        (60, 64, "B"),
        (65, 69, "B+"),
        (70, 74, "A-"),
        (75, 100, "A"),
    ],
    "MATHEMATICS": [
        (0, 24, "E"),
        (25, 29, "D-"),
        (30, 34, "D"),
        (35, 39, "D+"),
        (40, 44, "C-"),
        (45, 49, "C"),
        (50, 54, "C+"),
        (55, 59, "B-"),
        (60, 64, "B"),
        (65, 69, "B+"),
        (70, 74, "A-"),
        (75, 100, "A"),
    ],
    "ARTS & HUMANITIES": [
        (0, 34, "E"),
        (35, 39, "D-"),
        (40, 44, "D"),
        (45, 49, "D+"),
        (50, 54, "C-"),
        (55, 59, "C"),
        (60, 64, "C+"),
        (65, 70, "B-"),
        (71, 74, "B"),
        (75, 79, "B+"),
        (80, 84, "A-"),
        (85, 100, "A"),
    ],
}


def resolve_844_grade(score, subject_category):
    """
    Returns:
        grade (str)
        points (int)  → KCSE points (A=12 ... E=1)
    """
    category = subject_category.upper()
    for min_s, max_s, grade in EIGHT_FOUR_FOUR_GRADING.get(category, []):
        if min_s <= score <= max_s:
            return grade, GRADE_POINTS.get(grade, 1)
    return "E", 1


# =========================================================
# AGGREGATE POINTS → FINAL GRADE SCALE
# =========================================================
AGGREGATE_POINT_SCALE = [
    (7, 10, "E"),
    (11, 17, "D-"),
    (18, 24, "D"),
    (25, 31, "D+"),
    (32, 38, "C-"),
    (39, 45, "C"),
    (46, 52, "C+"),
    (53, 59, "B-"),
    (60, 66, "B"),
    (67, 73, "B+"), 
    (74, 79, "A-"), 
    (80, 84, "A"), 
]

def aggregate_to_final_grade(points):
    for min_p, max_p, grade in AGGREGATE_POINT_SCALE:
        if min_p <= points <= max_p:
            return grade
    return "E"


def simplify_844_grade(grade):
    """Collapse letter grades into A–E buckets for analytics charts."""
    if not grade:
        return None
    letter = str(grade).strip().upper()[0]
    if letter in ("A", "B", "C", "D", "E"):
        return letter
    return None


def is_low_844_grade(grade):
    bucket = simplify_844_grade(grade)
    return bucket in ("D", "E")


def compute_844_aggregate(all_subject_points):
    """Compute KCSE aggregate total and mean grade from subject point rows."""
    if not all_subject_points:
        return {"total_points": 0, "mean_grade": "—"}

    math_points = [
        s["points"]
        for s in all_subject_points
        if str(s.get("category", "")).upper() == "MATHEMATICS"
    ]
    math_points = math_points[0] if math_points else 0

    language_points = [
        s["points"]
        for s in all_subject_points
        if str(s.get("category", "")).upper() == "LANGUAGES"
    ]
    language_points = max(language_points) if language_points else 0

    math_index = next(
        (
            i
            for i, s in enumerate(all_subject_points)
            if str(s.get("category", "")).upper() == "MATHEMATICS"
        ),
        None,
    )

    language_indices = [
        i
        for i, s in enumerate(all_subject_points)
        if str(s.get("category", "")).upper() == "LANGUAGES"
    ]

    best_language_index = None
    if language_indices:
        best_language_index = max(
            language_indices,
            key=lambda i: all_subject_points[i]["points"],
        )

    remaining_points = [
        s["points"]
        for i, s in enumerate(all_subject_points)
        if i not in (math_index, best_language_index)
    ]

    best_five = sorted(remaining_points, reverse=True)[:5]
    total_points = math_points + language_points + sum(best_five)

    return {
        "total_points": total_points,
        "mean_grade": aggregate_to_final_grade(total_points),
    }


# =========================================================
# Automatic comment based on marks
# =========================================================
def subject_comment(marks):
    if marks >= 80:
        return "Excellent."
    elif marks >= 70:
        return "Very good."
    elif marks >= 60:
        return "Good."
    elif marks >= 50:
        return "Satisfactory."
    elif marks >= 40:
        return "Fair"
    elif marks >= 30:
        return "Need Improvement."
    else:
        return "Poor."


def _term_sort_key(term):
    return {"I": 1, "II": 2, "III": 3}.get(term, 0)


def _exam_chronological_key(exam):
    return (exam.year, _term_sort_key(exam.term), (exam.name or "").lower())


def _collect_844_point_rows(student, exam):
    """Collect subject point rows for aggregate grading on one exam."""
    branch = student.branch
    class_ = student.class_info
    if not branch or not class_:
        return []

    point_rows = []
    for alloc in student.subject_allocations:
        subject = alloc.subject
        if not subject:
            continue

        exam_paper = (
            ExamPaper.query
            .filter_by(
                exam_id=exam.id,
                branch_id=branch.id,
                class_id=class_.id,
                stream=student.stream,
                subject_id=subject.id,
            )
            .first()
        )
        if not exam_paper:
            continue

        mark = (
            StudentExamMark.query
            .filter_by(
                exam_paper_id=exam_paper.id,
                student_id=student.id,
            )
            .first()
        )
        if not mark:
            continue

        _, points = resolve_844_grade(mark.marks, subject.category)
        point_rows.append(
            {
                "points": points,
                "category": subject.category,
            }
        )

    return point_rows


def get_student_844_exam_trend(student, current_exam_id, previous_count=3):
    """
    Return recent 8-4-4 exam summaries for trend display on report cards.
    Includes the current exam and up to `previous_count` earlier exams.
    """
    class_ = student.class_info
    if not class_ or not is_844_form(normalize_form_name(class_.grade_form)):
        return []

    exam_rows = (
        db.session.query(Exam)
        .join(ExamPaper, ExamPaper.exam_id == Exam.id)
        .join(StudentExamMark, StudentExamMark.exam_paper_id == ExamPaper.id)
        .filter(
            StudentExamMark.student_id == student.id,
            ExamPaper.branch_id == student.branch_id,
            ExamPaper.class_id == student.class_id,
        )
        .distinct()
        .all()
    )

    eligible_exams = list(exam_rows)
    if not eligible_exams:
        return []

    eligible_exams.sort(key=_exam_chronological_key)
    current_index = next(
        (idx for idx, exam in enumerate(eligible_exams) if exam.id == current_exam_id),
        None,
    )
    if current_index is None:
        return []

    start_index = max(0, current_index - previous_count)
    selected_exams = eligible_exams[start_index: current_index + 1]

    trend = []
    for exam in selected_exams:
        point_rows = _collect_844_point_rows(student, exam)
        if not point_rows:
            continue
        aggregate = compute_844_aggregate(point_rows)
        trend.append(
            {
                "exam_id": exam.id,
                "exam_name": exam.name,
                "term": exam.term,
                "year": exam.year,
                "label": f"{exam.name} T{exam.term} {exam.year}",
                "total_points": aggregate["total_points"],
                "grade": aggregate["mean_grade"],
                "is_current": exam.id == current_exam_id,
            }
        )

    return trend


def _stream_key(stream):
    return stream if stream not in (None, "") else ""


def _resolve_class_teacher(class_teachers_by_stream, student):
    if student.stream:
        teacher = class_teachers_by_stream.get(_stream_key(student.stream))
        if teacher:
            return teacher
    return class_teachers_by_stream.get("")


def _build_844_class_context(branch_id, class_id, exam_id, students):
    """Pre-load marks, papers, lessons, teachers, and trend data for a class."""
    branch = Branch.query.get(branch_id)
    class_ = BranchClasses.query.get(class_id)
    exam = Exam.query.get(exam_id)
    school_logo = build_static_image_path(branch.logo) if branch and branch.logo else None
    school_logo_data_uri = build_pdf_image_data_uri(school_logo) if school_logo else None

    mark_rows = (
        db.session.query(StudentExamMark, ExamPaper, Subject)
        .join(ExamPaper, StudentExamMark.exam_paper_id == ExamPaper.id)
        .join(Subject, ExamPaper.subject_id == Subject.id)
        .filter(
            ExamPaper.exam_id == exam_id,
            ExamPaper.branch_id == branch_id,
            ExamPaper.class_id == class_id,
        )
        .all()
    )

    marks_by_student_subject = {}
    papers_by_stream_subject = {}
    for mark, paper, subject in mark_rows:
        marks_by_student_subject[(mark.student_id, subject.id)] = mark.marks
        papers_by_stream_subject[(_stream_key(paper.stream), subject.id)] = paper

    lessons = (
        Lesson.query
        .filter_by(branch_id=branch_id, class_id=class_id)
        .options(joinedload(Lesson.teacher))
        .all()
    )
    lessons_by_stream_subject = {
        (_stream_key(lesson.stream), lesson.subject_id): lesson for lesson in lessons
    }

    class_teachers = (
        ClassTeacher.query
        .filter_by(branch_id=branch_id, class_id=class_id)
        .options(joinedload(ClassTeacher.teacher))
        .all()
    )
    class_teachers_by_stream = {
        _stream_key(ct.stream): ct for ct in class_teachers
    }

    student_ids = [student.id for student in students]
    marks_by_student_exam_subject = defaultdict(lambda: defaultdict(dict))
    exams_by_id = {}

    if student_ids:
        trend_rows = (
            db.session.query(StudentExamMark, ExamPaper, Exam, Subject)
            .join(ExamPaper, StudentExamMark.exam_paper_id == ExamPaper.id)
            .join(Exam, ExamPaper.exam_id == Exam.id)
            .join(Subject, ExamPaper.subject_id == Subject.id)
            .filter(
                StudentExamMark.student_id.in_(student_ids),
                ExamPaper.branch_id == branch_id,
                ExamPaper.class_id == class_id,
            )
            .all()
        )

        for mark, paper, exam_row, subject in trend_rows:
            exams_by_id[exam_row.id] = exam_row
            marks_by_student_exam_subject[mark.student_id][exam_row.id][subject.id] = {
                "marks": mark.marks,
                "category": subject.category,
            }

    return {
        "branch": branch,
        "class_": class_,
        "exam": exam,
        "school_logo": school_logo,
        "school_logo_data_uri": school_logo_data_uri,
        "marks_by_student_subject": marks_by_student_subject,
        "papers_by_stream_subject": papers_by_stream_subject,
        "lessons_by_stream_subject": lessons_by_stream_subject,
        "class_teachers_by_stream": class_teachers_by_stream,
        "marks_by_student_exam_subject": marks_by_student_exam_subject,
        "exams_by_id": exams_by_id,
    }


def _exam_trend_from_cache(student, current_exam_id, ctx, previous_count=3):
    class_ = student.class_info
    if not class_ or not is_844_form(normalize_form_name(class_.grade_form)):
        return []

    student_exams = ctx["marks_by_student_exam_subject"].get(student.id, {})
    if not student_exams:
        return []

    eligible_exams = [
        ctx["exams_by_id"][exam_id]
        for exam_id in student_exams
        if exam_id in ctx["exams_by_id"]
    ]
    if not eligible_exams:
        return []

    eligible_exams.sort(key=_exam_chronological_key)
    current_index = next(
        (idx for idx, exam in enumerate(eligible_exams) if exam.id == current_exam_id),
        None,
    )
    if current_index is None:
        return []

    start_index = max(0, current_index - previous_count)
    selected_exams = eligible_exams[start_index: current_index + 1]

    trend = []
    for exam in selected_exams:
        point_rows = []
        exam_subjects = student_exams.get(exam.id, {})
        for alloc in student.subject_allocations:
            if not alloc.subject_id:
                continue
            entry = exam_subjects.get(alloc.subject_id)
            if not entry:
                continue
            _, points = resolve_844_grade(entry["marks"], entry["category"])
            point_rows.append(
                {
                    "points": points,
                    "category": entry["category"],
                }
            )

        if not point_rows:
            continue

        aggregate = compute_844_aggregate(point_rows)
        trend.append(
            {
                "exam_id": exam.id,
                "exam_name": exam.name,
                "term": exam.term,
                "year": exam.year,
                "label": f"{exam.name} T{exam.term} {exam.year}",
                "total_points": aggregate["total_points"],
                "grade": aggregate["mean_grade"],
                "is_current": exam.id == current_exam_id,
            }
        )

    return trend


# =========================================================
# SINGLE STUDENT REPORT WITH AGGREGATE RULE
# =========================================================
def generate_student_report(student: Student, exam: Exam, ctx=None):
    if ctx is None:
        branch = student.branch
        class_ = student.class_info
    else:
        branch = ctx["branch"]
        class_ = ctx["class_"]
        exam = ctx["exam"]

    normalized_form = normalize_form_name(class_.grade_form)

    if not is_844_form(normalized_form):
        raise ValueError("This report generator is for Form 3 & 4 only")

    if ctx is None:
        class_teacher_query = ClassTeacher.query.filter_by(
            branch_id=branch.id,
            class_id=class_.id
        )

        if student.stream:
            class_teacher_query = class_teacher_query.filter_by(stream=student.stream)
        else:
            class_teacher_query = class_teacher_query.filter(
                or_(
                    ClassTeacher.stream.is_(None),
                    ClassTeacher.stream == ""
                )
            )

        class_teacher = class_teacher_query.first()
    else:
        class_teacher = _resolve_class_teacher(ctx["class_teachers_by_stream"], student)

    subjects = []
    all_subject_points = []
    stream_key = _stream_key(student.stream)

    for alloc in student.subject_allocations:
        subject = alloc.subject
        if not subject:
            continue

        if ctx is None:
            exam_paper = (
                ExamPaper.query
                .filter_by(
                    exam_id=exam.id,
                    branch_id=branch.id,
                    class_id=class_.id,
                    stream=student.stream,
                    subject_id=subject.id,
                )
                .first()
            )

            if not exam_paper:
                continue

            mark = (
                StudentExamMark.query
                .filter_by(
                    exam_paper_id=exam_paper.id,
                    student_id=student.id,
                )
                .first()
            )

            if not mark:
                continue

            marks = mark.marks

            lesson = (
                Lesson.query
                .filter_by(
                    branch_id=branch.id,
                    class_id=class_.id,
                    stream=student.stream,
                    subject_id=subject.id,
                )
                .first()
            )
        else:
            paper = ctx["papers_by_stream_subject"].get((stream_key, subject.id))
            if not paper:
                continue

            marks = ctx["marks_by_student_subject"].get((student.id, subject.id))
            if marks is None:
                continue

            lesson = ctx["lessons_by_stream_subject"].get((stream_key, subject.id))

        grade, points = resolve_844_grade(marks, subject.category)
        teacher = lesson.teacher if lesson else None

        subjects.append({
            "subject": subject.name,
            "code": subject.code,
            "category": subject.category,
            "marks": marks,
            "grade": grade,
            "points": points,
            "teacher": teacher.fullname if teacher else None,
            "teacher_initials": teacher_initials(teacher),
            "comment": subject_comment(marks),
        })

        all_subject_points.append({
            "subject": subject.name,
            "points": points,
            "category": subject.category,
        })

    # ==========================
    # AGGREGATE POINT CALCULATION
    # ==========================
    # 1. Include Mathematics
    math_points = [s["points"] for s in all_subject_points if s["category"].upper() == "MATHEMATICS"]
    math_points = math_points[0] if math_points else 0

    # 2. Highest language (English / Kiswahili)
    language_points = [s["points"] for s in all_subject_points if s["category"].upper() == "LANGUAGES"]
    language_points = max(language_points) if language_points else 0


    # 3. Remaining subjects → exclude ONLY the selected math and best language
    #  so the other language (if present) can still be counted

    # get math index
    math_index = next(
        (i for i, s in enumerate(all_subject_points) if s["category"].upper() == "MATHEMATICS"),
        None
    )

    # get best language index
    language_indices = [
        i for i, s in enumerate(all_subject_points)
        if s["category"].upper() == "LANGUAGES"
    ]

    best_language_index = None
    if language_indices:
        best_language_index = max(language_indices, key=lambda i: all_subject_points[i]["points"])

    # collect remaining subjects
    remaining_points = [
        s["points"]
        for i, s in enumerate(all_subject_points)
        if i not in (math_index, best_language_index)
    ]

    best_five = sorted(remaining_points, reverse=True)[:5]

    total_points = math_points + language_points + sum(best_five)

    # ==========================
    # FINAL GRADE
    # ==========================
    final_grade = aggregate_to_final_grade(total_points)

    # ==========================
    # MEAN SCORE (all subjects)
    # ==========================
    total_marks = sum(s["marks"] for s in subjects)
    mean_score = round(total_marks / len(subjects), 2) if subjects else 0

    if ctx is None:
        school_logo = build_pdf_image_data_uri(
            build_static_image_path(branch.logo) if branch.logo else None
        )
        exam_trend = get_student_844_exam_trend(student, exam.id)
        passport_path = build_pdf_image_data_uri(build_passport_path(student))
    else:
        school_logo = ctx.get("school_logo_data_uri")
        exam_trend = _exam_trend_from_cache(student, exam.id, ctx)
        passport_path = build_pdf_image_data_uri(build_passport_path(student))

    return {
        "student_id": student.id,
        "passport_path": passport_path,
        "name": student.fullname.upper(),
        "admission_number": student.admission_number,
        "gender": student.gender,
        "class": normalized_form,
        "stream": student.stream,
        "exam": {
            "id": exam.id,
            "name": exam.name,
            "year": exam.year,
            "term": exam.term,
        },
        "subjects": subjects,
        "summary": {
            "total_points": total_points,
            "mean_score": mean_score,
            "final_grade": final_grade,
            "remarks": performance_remark(total_points),
        },
        "class_teacher": class_teacher.teacher.fullname if class_teacher and class_teacher.teacher else None,
        "school_logo": school_logo,
        "branch_name": branch.branch_name.upper(),
        "exam_trend": exam_trend,
    }


def generate_class_reports(branch_id, class_id, stream, exam_id):
    exam = Exam.query.get(exam_id)

    all_students = (
        Student.query
        .options(
            joinedload(Student.subject_allocations).joinedload(StudentSubjectAllocation.subject),
            joinedload(Student.branch),
            joinedload(Student.class_info),
        )
        .filter_by(branch_id=branch_id, class_id=class_id)
        .all()
    )

    ctx = _build_844_class_context(branch_id, class_id, exam_id, all_students)
    all_reports = [generate_student_report(s, exam, ctx) for s in all_students]

    # -----------------------------
    # General ranking (across all streams)
    # -----------------------------
    all_reports.sort(key=lambda r: r["summary"]["total_points"], reverse=True)
    for idx, r in enumerate(all_reports, start=1):
        r["summary"]["general_position"] = idx
        r["summary"]["general_out_of"] = len(all_reports)

    # -----------------------------
    # Stream ranking (within the given stream)
    # -----------------------------
    stream_reports = [r for r in all_reports if r["stream"] == stream]
    stream_reports.sort(key=lambda r: r["summary"]["total_points"], reverse=True)
    for idx, r in enumerate(stream_reports, start=1):
        r["summary"]["position"] = idx
        r["summary"]["out_of"] = len(stream_reports)
        # final_grade stays the same
        r["summary"]["final_grade"] = aggregate_to_final_grade(r["summary"]["total_points"])

    return stream_reports


def compute_class_exam_rankings(branch_id, class_id, exam_id):
    """
    Lightweight class rankings for 8-4-4 exams.
    Returns a dict keyed by student_id with stream/overall positions.
    """
    from collections import defaultdict

    students = (
        Student.query
        .options(joinedload(Student.subject_allocations))
        .filter_by(branch_id=branch_id, class_id=class_id)
        .all()
    )

    mark_rows = (
        db.session.query(StudentExamMark, ExamPaper, Subject)
        .join(ExamPaper, StudentExamMark.exam_paper_id == ExamPaper.id)
        .join(Subject, ExamPaper.subject_id == Subject.id)
        .filter(
            ExamPaper.exam_id == exam_id,
            ExamPaper.branch_id == branch_id,
            ExamPaper.class_id == class_id,
        )
        .all()
    )

    mark_by_student_subject = {}
    for mark, paper, subject in mark_rows:
        mark_by_student_subject[(mark.student_id, subject.id)] = {
            "marks": mark.marks,
            "category": subject.category,
        }

    summaries = []
    for student in students:
        point_rows = []
        for alloc in student.subject_allocations:
            if not alloc.subject_id:
                continue
            entry = mark_by_student_subject.get((student.id, alloc.subject_id))
            if not entry:
                continue
            _, points = resolve_844_grade(entry["marks"], entry["category"])
            point_rows.append(
                {
                    "points": points,
                    "category": entry["category"],
                }
            )

        agg = compute_844_aggregate(point_rows)
        summaries.append(
            {
                "student_id": student.id,
                "stream": student.stream,
                "total_points": agg["total_points"],
            }
        )

    summaries.sort(key=lambda row: row["total_points"], reverse=True)
    ranking_map = {}
    class_total = len(summaries)

    for position, row in enumerate(summaries, start=1):
        ranking_map[row["student_id"]] = {
            "overall_position": position,
            "overall_total": class_total,
            "stream_position": None,
            "stream_total": None,
        }

    stream_groups = defaultdict(list)
    for row in summaries:
        stream_groups[row["stream"]].append(row)

    for group in stream_groups.values():
        group.sort(key=lambda item: item["total_points"], reverse=True)
        stream_total = len(group)
        for position, row in enumerate(group, start=1):
            ranking_map[row["student_id"]]["stream_position"] = position
            ranking_map[row["student_id"]]["stream_total"] = stream_total

    return ranking_map
