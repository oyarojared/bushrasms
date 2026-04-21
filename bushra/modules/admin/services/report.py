from ....modals.assessment_db import *
from ....modals.branches_db import Branch, BranchClasses
from ....modals.staff_db import ClassTeacher, Teacher
from ....modals.students_db import Student
from ....modals.subjects_db import * 
from ..utils import resolve_grade 
from ....modals.students_db import StudentSubjectAllocation

from pathlib import Path
import os
from flask import current_app
from ..services.grading import get_max_points_for_class

from pathlib import Path
from flask import current_app

def build_static_image_path(filename, folder="uploads/passports", default="default-logo.PNG"):
    """
    Returns a file URI for WeasyPrint to use.
    If filename is None or file doesn't exist, uses a default image.
    """
    base = Path(current_app.root_path, "static", folder)

    if filename:
        path = base / filename
        if path.exists():
            return path.resolve().as_uri()

    # fallback
    return (base / default).resolve().as_uri()


def build_passport_path(student):
    base = Path(
        current_app.root_path,
        "static",
        "uploads",
        "passports"
    )

    if student.passport:
        path = base / student.passport
        if path.exists():
            return path.resolve().as_uri()

    return (base / "default.JPG").resolve().as_uri()



def get_report_card_data(branch_id, class_id, exam_id, stream=None, student_id=None):
    """
    Fetch all necessary data to generate a report card PDF,
    including grading reference for the class.
    """
    # 1️⃣ Branch info
    branch = Branch.query.get(branch_id)
    if not branch:
        raise ValueError("Branch not found")

    # 2️⃣ Class info
    class_ = BranchClasses.query.get(class_id)
    if not class_:
        raise ValueError("Class not found")
    
    class_name = class_.grade_form

    # 3️⃣ Exam info
    exam_data = Exam.query.get(exam_id)

    # 4️⃣ Class teacher
    class_teacher_query = ClassTeacher.query.filter_by(branch_id=branch_id, class_id=class_id)
    if stream:
        class_teacher_query = class_teacher_query.filter_by(stream=stream)
    class_teacher_obj = class_teacher_query.first()
    class_teacher_name = class_teacher_obj.teacher.fullname if class_teacher_obj and class_teacher_obj.teacher else None

    # 5️⃣ Students
    query = Student.query.filter_by(branch_id=branch_id, class_id=class_id)
    if stream:
        query = query.filter_by(stream=stream)
    if student_id:
        query = query.filter_by(id=student_id)
    students = query.all()

    student_list = []
    for s in students:
        student_data = {
            "id": s.id,
            "fullname": s.fullname.upper(),
            "assessment_no": s.knec_assessment_no,
            "admission_number": s.admission_number,
            "pathway": s.pathway,
            "gender": s.gender,
            "stream": s.stream,
            "passport_path": build_passport_path(s),  # ✅ rename
            "class_teacher": class_teacher_name,
            "subjects": []
        }
 
        for alloc in s.subject_allocations:
            subject = alloc.subject
            if not subject:
                continue

            # Get lesson to find teacher initials
            lesson = Lesson.query.filter_by(
                branch_id=branch_id,
                class_id=class_id,
                stream=stream,
                subject_id=subject.id
            ).first()

            teacher_initials = None
            if lesson and lesson.teacher:
                names = lesson.teacher.fullname.strip().split()
                teacher_initials = ".".join([n[0].upper() for n in names])

            # Get student's marks
            exam_paper = ExamPaper.query.filter_by(
                exam_id=exam_id,
                branch_id=branch_id,
                class_id=class_id,
                stream=stream,
                subject_id=subject.id
            ).first()

            marks = None
            if exam_paper:
                mark_obj = StudentExamMark.query.filter_by(
                    exam_paper_id=exam_paper.id,
                    student_id=s.id
                ).first()
                if mark_obj:
                    marks = mark_obj.marks

            # Resolve performance
            grade_info = resolve_grade(class_id, marks) if marks is not None else {
                "performance_level": None,
                "points": None,
                "descriptor": None
            }

            student_data["subjects"].append({
                "subject_code": subject.code,
                "subject_name": subject.name,
                "teacher_initials": teacher_initials,
                "marks": marks,
                "performance_level": grade_info["performance_level"],
                "points": grade_info["points"],
                "descriptor": grade_info["descriptor"]
            })

        student_list.append(student_data)

    # 6️⃣ Grading boundaries for this grade
    grading_boundaries = []
    scheme_link = GradeGradingScheme.query.filter_by(grade_id=class_id).first()
    if scheme_link and scheme_link.scheme:
        grading_boundaries = scheme_link.scheme.boundaries

    school_logo_path = None
    if branch.logo:
        school_logo_path = build_static_image_path(branch.logo)

    result = {
        "branch": {
            "name": branch.branch_name.upper(),
            "code": branch.school_code,
            "class_name": class_name,
            "logo": school_logo_path,
            "motto": branch.motto,
        },
        "exam": {
            "name": exam_data.name,
            "year": exam_data.year,
            "term": exam_data.term
        },
        "class": {
            "grade_form": class_.grade_form,
            "class_year": class_.class_year,
            "streams": class_.streams
        },
        "exam_id": exam_id,
        "students": student_list,
        "grading_boundaries": grading_boundaries,
        "school_logo": None,
        "stamp_placeholder": True,
        "max_points": get_max_points_for_class(class_id)
    }

    return result



def build_broadsheet_data(branch_id, class_id, exam_id, stream=None):
    """
    Service function that builds and returns broadsheet data.
    Returns a dict identical to what the route currently returns.
    """

    if not all([branch_id, class_id, exam_id]):
        raise ValueError("branch_id, class_id, and exam_id are required")

    if stream in ("", "null"):
        stream = None

    try:
        # -------------------- 1. Class & Exam --------------------
        class_obj = db.session.get(BranchClasses, class_id)
        class_name = class_obj.grade_form if class_obj else "N/A"

        exam_obj = ExamPaper.query.filter_by(exam_id=exam_id).first()
        exam_name = exam_obj.exam.name if exam_obj and exam_obj.exam else "N/A"

        branch = db.session.get(Branch, branch_id)
        branch_name = branch.branch_name if branch else "N/A"

        # -------------------- 2. Students --------------------
        students_query = Student.query.filter_by(branch_id=branch_id, class_id=class_id)
        if stream:
            students_query = students_query.filter_by(stream=stream)

        students = students_query.order_by(Student.fullname).all()
        student_ids = [s.id for s in students]

        if not students:
            return {
                "subjects": [],
                "students": [],
                "class_name": class_name,
                "exam_name": exam_name,
                "total_learners": 0,
                "branch_name": branch_name
            }

        # -------------------- 3. Subjects --------------------
        allocations = StudentSubjectAllocation.query.filter(
            StudentSubjectAllocation.student_id.in_(student_ids)
        ).all()

        subject_ids = set(a.subject_id for a in allocations)

        subjects = Subject.query.filter(Subject.id.in_(subject_ids)).all()
        subject_map = {s.id: s for s in subjects}

        # -------------------- 4. Exam Papers --------------------
        papers_query = ExamPaper.query.filter_by(
            exam_id=exam_id,
            branch_id=branch_id,
            class_id=class_id
        ).filter(ExamPaper.subject_id.in_(subject_ids))

        if stream:
            papers_query = papers_query.filter_by(stream=stream)
        else:
            papers_query = papers_query.filter(ExamPaper.stream.is_(None))

        papers = papers_query.all()
        paper_map = {p.subject_id: p for p in papers}

        # -------------------- 5. Marks --------------------
        paper_ids = [p.id for p in papers]

        marks = StudentExamMark.query.filter(
            StudentExamMark.exam_paper_id.in_(paper_ids),
            StudentExamMark.student_id.in_(student_ids)
        ).all()

        marks_map = {(m.student_id, m.exam_paper_id): m.marks for m in marks}

        # -------------------- 6. Teachers --------------------
        lessons_query = Lesson.query.filter_by(branch_id=branch_id, class_id=class_id)
        lessons_query = lessons_query.filter(Lesson.subject_id.in_(subject_ids))

        if stream:
            lessons_query = lessons_query.filter_by(stream=stream)

        lessons = lessons_query.all()
        lesson_map = {l.subject_id: l for l in lessons}

        teacher_ids = [l.teacher_id for l in lessons if l.teacher_id]
        teachers = Teacher.query.filter(Teacher.id.in_(teacher_ids)).all()
        teacher_map = {t.id: t for t in teachers}

        # -------------------- 6B. Class Teacher --------------------
        class_teacher = None
        class_teacher_obj = ClassTeacher.query.filter_by(
            class_id=class_id,
            branch_id=branch_id
        ).first()

        if class_teacher_obj:
            teacher = teacher_map.get(class_teacher_obj.teacher_id) or db.session.get(Teacher, class_teacher_obj.teacher_id)
            if teacher:
                class_teacher = f"{teacher.title} {teacher.fullname}"

        # -------------------- 7. Subjects Info --------------------
        subjects_data = []

        for s in subjects:
            lesson = lesson_map.get(s.id)
            teacher_name = "N/A"

            if lesson and lesson.teacher_id:
                teacher = teacher_map.get(lesson.teacher_id)
                if teacher:
                    teacher_name = f"{teacher.title} {teacher.fullname}"

            subjects_data.append({
                "id": s.id,
                "name": s.name,
                "code": s.code,
                "teacher": teacher_name
            })

        # -------------------- 8. Build Students + Analytics --------------------
        students_data = []

        subject_analysis = {subj.id: {} for subj in subjects}
        subject_totals = {subj.id: [] for subj in subjects}
        at_risk_learners = []

        for s in students:
            marks_per_subject = {}

            for subj in subjects:
                paper = paper_map.get(subj.id)

                mark_value = "-"
                grade_value = None

                if paper:
                    mark_value = marks_map.get((s.id, paper.id), "-")

                    if mark_value != "-":
                        if class_name not in ("Form 3", "Form 4", "form 3", "form 4"):
                            grade_info = resolve_grade(class_id, mark_value)
                            grade_value = grade_info.get("performance_level") if grade_info else None

                            # Subject analysis
                            if grade_value:
                                subject_analysis[subj.id][grade_value] = \
                                    subject_analysis[subj.id].get(grade_value, 0) + 1

                        # Collect for averages
                        subject_totals[subj.id].append(mark_value)

                marks_per_subject[subj.id] = {
                    "marks": mark_value,
                    "grade": grade_value
                }

            # Identify at-risk learners
            low_count = sum(
                1 for v in marks_per_subject.values()
                if v["grade"] in ("BE",)
            )

            if low_count >= 3:
                at_risk_learners.append({
                    "id": s.id,
                    "name": s.fullname.upper(),
                    "low_subjects": low_count
                })

            students_data.append({
                "id": s.id,
                "admission_number": s.admission_number,
                "full_name": s.fullname.upper(),
                "marks": marks_per_subject
            })

        # -------------------- 9. Additional Analytics --------------------
        subject_averages = {}

        for subj in subjects:
            values = subject_totals[subj.id]
            subject_averages[subj.id] = sum(values) / len(values) if values else None

        subject_participation = {
            subj.id: len(subject_totals[subj.id])
            for subj in subjects
        }

        # Missing marks per student
        missing_marks_list = []

        for s in students_data:
            missing_subjects = [
                subj.name
                for subj in subjects
                if s["marks"][subj.id]["marks"] == "-"
            ]
            if missing_subjects:
                missing_marks_list.append({
                    "student": s["full_name"],
                    "subjects": missing_subjects
                })

        # -------------------- 10. Final Data --------------------
        return {
            "class_name": class_name,
            "stream": stream,
            "exam_name": exam_name,
            "subjects": subjects_data,
            "students": students_data,
            "total_learners": len(students),
            "class_teacher": class_teacher,
            "subject_analysis": subject_analysis,
            "subject_averages": subject_averages,
            "subject_participation": subject_participation,
            "at_risk_learners": at_risk_learners,
            "missing_marks": missing_marks_list,
            "branch_name": branch_name
        }

    except Exception:
        current_app.logger.exception("Error building broadsheet (service)")
        raise