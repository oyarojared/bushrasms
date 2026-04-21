from sqlalchemy import or_
from sqlalchemy.orm import joinedload
from ....modals.students_db import Student
from ....modals.staff_db import Teacher, ClassTeacher
from ....modals.subjects_db import Lesson
from ....modals.assessment_db import Exam, ExamPaper, StudentExamMark
from ....modals.branches_db import Branch 
from .report import build_passport_path, build_static_image_path 


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
    (74, 80, "A-"), 
    (81, 84, "A"), 
]

def aggregate_to_final_grade(points):
    for min_p, max_p, grade in AGGREGATE_POINT_SCALE:
        if min_p <= points <= max_p:
            return grade
    return "E"


# =========================================================
# Automatic comment based on marks
# =========================================================
def subject_comment(marks):
    if marks >= 75:
        return "Excellent work!"
    elif marks >= 65:
        return "Very good. Keep it up."
    elif marks >= 50:
        return "Good effort. Can improve."
    elif marks >= 40:
        return "Fair performance. Needs more practice."
    else:
        return "Below average. Work harder."


# =========================================================
# SINGLE STUDENT REPORT WITH AGGREGATE RULE
# =========================================================
def generate_student_report(student: Student, exam: Exam):
    branch = student.branch 
    class_ = student.class_info
    normalized_form = normalize_form_name(class_.grade_form)

    if not is_844_form(normalized_form):
        raise ValueError("This report generator is for Form 3 & 4 only")

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

    subjects = []
    all_subject_points = []

    for alloc in student.subject_allocations:
        subject = alloc.subject

        exam_paper = (
            ExamPaper.query
            .filter_by(
                exam_id=exam.id,
                branch_id=branch.id,
                class_id=class_.id,
                stream=student.stream,
                subject_id=subject.id
            )
            .first()
        )

        if not exam_paper:
            continue

        mark = (
            StudentExamMark.query
            .filter_by(
                exam_paper_id=exam_paper.id,
                student_id=student.id
            )
            .first()
        )

        if not mark:
            continue

        grade, points = resolve_844_grade(mark.marks, subject.category)

        lesson = (
            Lesson.query
            .filter_by(
                branch_id=branch.id,
                class_id=class_.id,
                stream=student.stream,
                subject_id=subject.id
            )
            .first()
        )

        teacher = lesson.teacher if lesson else None

        subjects.append({
            "subject": subject.name,
            "code": subject.code,
            "category": subject.category,
            "marks": mark.marks,
            "grade": grade,
            "points": points,
            "teacher": teacher.fullname if teacher else None,
            "teacher_initials": teacher_initials(teacher),
            "comment": subject_comment(mark.marks),
        })

        all_subject_points.append({
            "subject": subject.name,
            "points": points,
            "category": subject.category
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

    return {
        "student_id": student.id,
        "passport_path": build_passport_path(student), 
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
        "school_logo": build_static_image_path(branch.logo) if branch.logo else None,
        "branch_name": branch.branch_name.upper(),
    }

 

def generate_class_reports(branch_id, class_id, stream, exam_id):
    exam = Exam.query.get(exam_id)

    # -----------------------------
    # Get all students in the class (all streams)
    # -----------------------------
    all_students = (
        Student.query
        .options(joinedload(Student.subject_allocations))
        .filter_by(branch_id=branch_id, class_id=class_id)
        .all()
    )

    # Generate reports for all students
    all_reports = [generate_student_report(s, exam) for s in all_students]

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
