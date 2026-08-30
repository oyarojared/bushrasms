from flask import flash, make_response, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from urllib.parse import quote
from ..services.report_pdf import build_report_bundle, render_bundle_pdf

from ....modals.assessment_db import Exam
from ....modals.students_db import Student
from .. import admin_bp
from ..services.grades import live_class_name
from ..services import studs as studs_service
from ..utils import safe_date
from ..utils.class_teacher import (
    assignment_covers_student,
    assignment_has_exam,
    assignment_label,
    class_exam_overview,
    class_exam_performance,
    exams_for_assignment,
    get_assignment_for_teacher,
    kenya_whatsapp_number,
    learner_has_photo,
    learner_initials,
    list_class_teacher_assignments,
    missing_learner_fields,
    sitting_filters,
    students_for_assignment,
    teacher_owns_student,
)


def _assignment_payload(assignment):
    school = assignment.branch.branch_name if assignment.branch else ""
    return {
        "id": assignment.id,
        "label": assignment_label(assignment),
        "school": school,
        "stream": (assignment.stream or "").strip(),
    }


def _learner_row(student):
    phone = (student.parent_phone or "").strip()
    name = (student.fullname or "").strip()
    return {
        "id": student.id,
        "fullname": name,
        "initials": learner_initials(name),
        "has_photo": learner_has_photo(student),
        "admission_number": student.admission_number,
        "gender": student.gender or "",
        "stream": student.stream or "",
        "boarding_status": student.boarding_status or "",
        "parent_fullname": (student.parent_fullname or "").strip(),
        "parent_phone": phone,
        "whatsapp": kenya_whatsapp_number(phone),
        "passport": student.passport or "default.jpg",
        "pathway": student.pathway or "",
        "missing": missing_learner_fields(student),
    }


def _selected_assignment(assignments):
    selected_id = request.args.get("assignment", type=int)
    selected = None
    if selected_id:
        selected = get_assignment_for_teacher(current_user, selected_id)
    if not selected and assignments:
        selected = assignments[0]
    return selected


def _render_student_report_pdf(student, exam_id):
    bundle = build_report_bundle(
        branch_id=student.branch_id,
        class_id=student.class_id,
        exam_id=exam_id,
        stream=student.stream or None,
        student_id=student.id,
    )
    return render_bundle_pdf(bundle, lite=True)


@admin_bp.route("/my-class")
@login_required
def my_class():
    assignments = list_class_teacher_assignments(current_user)
    assignment_views = [_assignment_payload(row) for row in assignments]
    school_names = {item["school"] for item in assignment_views if item["school"]}
    selected = _selected_assignment(assignments)

    students = students_for_assignment(selected) if selected else []
    learner_rows = [_learner_row(student) for student in students]
    missing_phone = sum(1 for row in learner_rows if not row["parent_phone"])

    exams = exams_for_assignment(selected) if selected else []
    exam_id = request.args.get("exam", type=int)
    selected_exam = next((exam for exam in exams if exam.id == exam_id), None)
    if not selected_exam and exams:
        selected_exam = exams[0]

    tab = (request.args.get("tab") or "learners").strip().lower()
    if tab not in ("learners", "results", "performance"):
        tab = "learners"

    overview = None
    performance = None
    filter_years = []
    filter_terms = []
    selected_year = None
    selected_term = None
    sitting_exams = exams

    if tab == "performance":
        year = request.args.get("year", type=int)
        term = (request.args.get("term") or "").strip() or None
        if year is None and selected_exam:
            year = selected_exam.year
        if not term and selected_exam:
            term = selected_exam.term
        filter_years, filter_terms, sitting_exams, selected_year, selected_term = (
            sitting_filters(exams, year, term)
        )
        selected_exam = next(
            (exam for exam in sitting_exams if exam.id == exam_id),
            None,
        )
        if not selected_exam and sitting_exams:
            selected_exam = sitting_exams[0]
        if selected and selected_exam:
            try:
                performance = class_exam_performance(selected, selected_exam.id)
            except Exception:
                performance = {
                    "error": "Could not load performance for this exam yet.",
                }
    elif tab == "results" and selected and selected_exam:
        try:
            overview = class_exam_overview(selected, selected_exam.id)
        except Exception:
            overview = {
                "exam_name": selected_exam.name,
                "subjects": [],
                "rows": [],
                "error": "Could not load results for this exam yet.",
            }

    return render_template(
        "class_teacher/my_class.html",
        assignments=assignment_views,
        selected_assignment=_assignment_payload(selected) if selected else None,
        show_schools=len(school_names) > 1,
        learners=learner_rows,
        learner_count=len(learner_rows),
        missing_phone_count=missing_phone,
        exams=exams,
        sitting_exams=sitting_exams,
        selected_exam=selected_exam,
        exam_overview=overview,
        performance=performance,
        filter_years=filter_years,
        filter_terms=filter_terms,
        selected_year=selected_year,
        selected_term=selected_term,
        active_tab=tab,
    )


@admin_bp.route("/my-class/students/<int:student_id>")
@login_required
def my_class_student(student_id):
    student = Student.query.get(student_id)
    if not student or not teacher_owns_student(current_user, student):
        flash("That learner is not in your class.", "warning")
        return redirect(url_for("admin.my_class"))

    phone = (student.parent_phone or "").strip()
    class_info = student.class_info
    grade = live_class_name(class_info.grade_form) if class_info else ""
    class_label = f"{grade} {student.stream or ''}".strip() or "—"

    assignment_id = request.args.get("assignment", type=int)
    selected = get_assignment_for_teacher(current_user, assignment_id)
    if not selected or not assignment_covers_student(selected, student):
        selected = next(
            (
                row
                for row in list_class_teacher_assignments(current_user)
                if assignment_covers_student(row, student)
            ),
            None,
        )

    academic_history = studs_service.get_student_academic_history(student.id)

    return render_template(
        "class_teacher/learner.html",
        learner={
            "id": student.id,
            "assignment_id": selected.id if selected else None,
            "fullname": (student.fullname or "").strip(),
            "admission_number": student.admission_number,
            "gender": student.gender or "—",
            "stream": student.stream or "",
            "class_label": class_label,
            "school": student.branch.branch_name if student.branch else "—",
            "boarding_status": student.boarding_status or "—",
            "pathway": student.pathway or "—",
            "dob": safe_date(student.dob),
            "parent_fullname": student.parent_fullname or "—",
            "parent_phone": phone,
            "whatsapp": kenya_whatsapp_number(phone),
            "nemis_number": student.nemis_number or "—",
            "knec_assessment_no": student.knec_assessment_no or "—",
            "birth_cert_no": student.birth_cert_no or "—",
            "passport": student.passport or "default.jpg",
            "subjects": student.subjects_taken,
            "missing": missing_learner_fields(student),
        },
        academic_history=academic_history,
    )


@admin_bp.route("/my-class/students/<int:student_id>/report-pdf")
@login_required
def my_class_student_report_pdf(student_id):
    student = Student.query.get(student_id)
    if not student or not teacher_owns_student(current_user, student):
        flash("That learner is not in your class.", "warning")
        return redirect(url_for("admin.my_class"))

    exam_id = request.args.get("exam", type=int)
    assignment_id = request.args.get("assignment", type=int)
    selected = get_assignment_for_teacher(current_user, assignment_id)
    if not selected or not assignment_covers_student(selected, student):
        selected = next(
            (
                row
                for row in list_class_teacher_assignments(current_user)
                if assignment_covers_student(row, student)
            ),
            None,
        )

    if not exam_id or not selected or not assignment_has_exam(selected, exam_id):
        flash("Choose an exam for this learner's class.", "warning")
        return redirect(
            url_for(
                "admin.my_class_student",
                student_id=student.id,
                assignment=selected.id if selected else None,
            )
        )

    try:
        pdf = _render_student_report_pdf(student, exam_id)
    except Exception:
        flash(
            "Could not generate that report card. Marks or grading may still be incomplete.",
            "warning",
        )
        return redirect(
            url_for(
                "admin.my_class_student",
                student_id=student.id,
                assignment=selected.id if selected else None,
            )
        )

    exam = Exam.query.get(exam_id)
    filename = f"{student.fullname}_{exam.name if exam else 'report'}.pdf"
    response = make_response(pdf)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = (
        f'attachment; filename="{quote(filename)}"'
    )
    return response
