from .. import admin_bp
from flask import render_template, flash, redirect, url_for, jsonify, request, current_app
from ..forms.assessment_forms import ExamCreateForm
from ....modals.branches_db import Branch, BranchClasses 
from ....modals.assessment_db import GradingSystem, GradingScheme, GradeGradingScheme, GradingBoundary
from ....modals.assessment_db import Exam, ExamBranch, ExamPaper, db
from ....modals.students_db import Student
from datetime import datetime
from ...admin.services.report import get_report_card_data
from ...admin.services.assessment_services import get_exams_for_user

from flask import Blueprint, request, make_response, render_template
from weasyprint import HTML 
from flask_login import login_required, current_user
from ...admin.utils.route_protect import admin_required

from ..services.grading_844 import generate_class_reports, normalize_form_name

from urllib.parse import quote
import traceback
from sqlalchemy.orm import joinedload

from flask import render_template, make_response
import weasyprint

 
@admin_bp.route("assessments/dash", methods=["GET", "POST"])
@login_required
def assessment_dash():
    exam_form = ExamCreateForm()

    grades = BranchClasses.query.all()
    
    query = get_exams_for_user(current_user)
    exams_list = query.all()

    # Branch choices
    if current_user.is_super_admin:
        branches = Branch.query.order_by(Branch.branch_name).all()
        exam_form.branch_id.choices = [(b.id, b.branch_name) for b in branches]
    else:
        branch = Branch.query.get(current_user.branch_id)
        if branch:
            exam_form.branch_id.choices = [(branch.id, branch.branch_name)]
        else:
            exam_form.branch_id.choices = []

    exam_form.year.choices = [
        (str(y), str(y)) for y in list(range(2026, 2036))
    ]

    if exam_form.validate_on_submit():

        # Selected branch
        selected_branch_id = exam_form.branch_id.data

        # --- DUPLICATE CHECKd ---
        exists = (
            db.session.query(Exam.id)
            .join(ExamBranch)
            .filter(
                Exam.name == exam_form.name.data.strip(),
                Exam.year == int(exam_form.year.data),
                Exam.term == exam_form.term.data,
                ExamBranch.branch_id == selected_branch_id
            )
            .first()
        )

        if exists:
            flash(
                "An exam with the same name, year, term, and branch already exists.",
                "danger",
            )
            return redirect(url_for("admin.assessment_dash"))

        # --- CREATE EXAM ---
        exam = Exam(
            name=exam_form.name.data.strip(),
            year=int(exam_form.year.data),
            term=exam_form.term.data,
            is_locked=False,
        )
        db.session.add(exam)
        db.session.flush()  # get exam.id

        # Assign to selected branch
        db.session.add(
            ExamBranch(
                exam_id=exam.id,
                branch_id=selected_branch_id
            )
        )

        db.session.commit()
        flash("Exam created successfully.", "success")
        return redirect(url_for("admin.assessment_dash"))
    
    return render_template(
        "academics/assessment_dash.html", 
        exam_form=exam_form,
        exams_list=exams_list,
        grades=grades,
    )


@admin_bp.route("/exams/<int:exam_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_exam(exam_id):
    exam = Exam.query.get(exam_id)

    if not exam:
        flash("Exam not found.", "danger")
        return redirect(url_for("admin.assessment_dash"))
    
    if not current_user.is_admin:
        flash("You have no admin rights to delete exams!", "warning")
        return redirect(url_for("admin.assessment_dash"))

    # 🔒 FUTURE-SAFE CHECK: Prevent deletion if marks exist
    if hasattr(exam, "marks") and exam.marks:
         flash(
            "This exam already has marks and cannot be deleted.",
            "warning"
        )
         return redirect(url_for("admin.assessment_dash"))
    
    if exam.is_locked:
        flash(
            "Locked exams cannot be deleted. Unlock the exam first.",
            "warning"
        )
        return redirect(url_for("admin.assessment_dash"))

    try:
        # Soft delete i.e make exam inactive
        exam.is_inactive = True
        db.session.commit() 

        flash("Exam deleted successfully.", "success")

    except Exception as e:
        db.session.rollback()
        flash(
            "An error occurred while deleting the exam.",
            "danger"
        )

    return redirect(url_for("admin.assessment_dash"))



@admin_bp.route("/exams/<int:exam_id>/lock", methods=["POST"])
@admin_required
@login_required
def lock_exam(exam_id):
    exam = Exam.query.get(exam_id)

    if not exam:
        flash("Exam not found.", "danger")
        return redirect(url_for("admin.exams"))

    if exam.is_locked:
        flash("This exam is already locked.", "info")
        return redirect(url_for("admin.exams"))

    try:
        exam.is_locked = True
        db.session.commit()

        flash("Exam locked successfully. Marks entry is now closed.", "success")

    except Exception:
        db.session.rollback()
        flash("Failed to lock the exam. Please try again.", "danger")

    return redirect(url_for("admin.assessment_dash"))


@admin_bp.route("/exams/<int:exam_id>/unlock", methods=["POST"]) 
@admin_required
@login_required
def unlock_exam(exam_id):
    exam = Exam.query.get(exam_id)

    if not exam:
        flash("Exam not found.", "danger")
        return redirect(url_for("admin.assessment_dash"))

    if not exam.is_locked:
        flash("This exam is already open.", "info")
        return redirect(url_for("admin.assessment_dash"))

    # 🔮 Future-proof rule (no results published)
    if hasattr(exam, "results_published") and exam.results_published:
        flash(
            "Published exams cannot be unlocked.",
            "warning"
        )
        return redirect(url_for("admin.assessment_dash"))

    try:
        exam.is_locked = False
        db.session.commit()

        flash("Exam unlocked. Marks entry is now open.", "success")

    except Exception:
        db.session.rollback()
        flash("Failed to unlock the exam. Please try again.", "danger")

    return redirect(url_for("admin.assessment_dash"))


@admin_bp.route("/exams/<int:exam_id>/marks", methods=["GET"]) 
@login_required
def marks_entry(exam_id):
    exam = Exam.query.get_or_404(exam_id)

    if exam.is_locked:
        flash(
            "This exam is locked. Marks entry is not allowed.",
            "warning"
        )
        return redirect(url_for("admin.assessment_dash"))

    return render_template(
        "academics/marks_entry.html",
        exam=exam
    )


@admin_bp.route("/generate-reportcards-pdf", methods=["POST"])
@login_required
@admin_required
def generate_reportcards_pdf():
    data = request.get_json()

    branch_id = data.get("branch_id")
    class_id = data.get("class_id")
    exam_id = data.get("exam_id")
    stream = data.get("stream", None)
    student_id = data.get("student_id", None)

    if not branch_id or not class_id or not exam_id:
        return {"error": "branch_id, class_id, and exam_id are required"}, 400

    # Defensive initialization (prevents UnboundLocalError)
    report_data = None

    try:
        # 🔹 Fetch class info first
        class_obj = BranchClasses.query.get_or_404(class_id)

        # ✅ SAFE normalization (handles Form 3, FORM3, Form 3 North, etc.)
        normalized_form = normalize_form_name(class_obj.grade_form)
        is_844 = normalized_form in ("Form 3", "Form 4", "IGCSE")

        # 🔹 1️⃣ Fetch data (CBC or 8-4-4)
        if is_844:
            report_data = generate_class_reports(
                branch_id=branch_id,
                class_id=class_id,
                exam_id=exam_id,
                stream=stream
            )
            template = "academics/report_card_844.html"
        else:
            report_data = get_report_card_data(   # existing CBC function
                branch_id=branch_id,
                class_id=class_id,
                exam_id=exam_id,
                stream=stream,
                student_id=student_id
            )
            template = "academics/report_card.html"

        # 🛡️ Extra safety: ensure data was actually generated
        if not report_data:
            raise ValueError("No report data generated")

        # 🔹 2️⃣ Render HTML
        rendered_html = render_template(template, data=report_data)

        # 🔹 3️⃣ Generate PDF
        pdf = HTML(string=rendered_html).write_pdf()

        class_name = class_obj.grade_form
        if stream:
            class_name += f" {stream}"      
        
        student_name = Student.query.get(student_id).full_name if student_id else ""    
        # 🔹 4️⃣ Send response
        response = make_response(pdf)
        response.headers["Content-Type"] = "application/pdf"
        if student_id:
            filename = f"{student_name}_assessment.pdf"
        else:
            filename = f"{class_name}_Assessment_Reports.pdf"
        
        safe_filename = quote(filename)

        response.headers["Content-Disposition"] = f'attachment; filename="{safe_filename}"'
        return response

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "error": "Failed to generate PDF",
            "details": str(e)
        }, 500



@admin_bp.route("/save_grading_config", methods=["POST"])
@login_required
@admin_required
def save_grading_config():
    data = request.get_json()

    system_name = data.get("system")
    boundaries = data.get("boundaries")
    selected_classes = data.get("selected_classes")  # still class IDs

    if not all([system_name, boundaries, selected_classes]):
        return jsonify({"error": "Missing required data"}), 400

    try:
        # 1️⃣ Resolve or create grading system
        system = GradingSystem.query.filter_by(name=system_name).first()
        if not system:
            system = GradingSystem(
                name=system_name,
                created_at=datetime.utcnow()
            )
            db.session.add(system)
            db.session.flush()

        # 2️⃣ Determine grade_form names from selected class IDs
        grade_forms = (
            BranchClasses.query
            .filter(BranchClasses.id.in_(selected_classes))
            .with_entities(BranchClasses.grade_form)
            .distinct()
            .all()
        )
        # Extract grade_form strings from tuples
        grade_forms = [gf[0] for gf in grade_forms]

        # 3️⃣ Apply boundaries to all classes with these grade_forms
        for grade_form in grade_forms:
            classes = BranchClasses.query.filter_by(grade_form=grade_form).all()

            for cls in classes:
                grade_id = cls.id

                # Delete old mappings and boundaries for this class
                old_mappings = GradeGradingScheme.query.filter_by(grade_id=grade_id).all()
                for m in old_mappings:
                    GradingBoundary.query.filter_by(scheme_id=m.scheme_id).delete()
                    db.session.delete(m)
                db.session.flush()

                # Create new scheme
                scheme = GradingScheme(
                    system_id=system.id,
                    name=f"{system_name} Scheme {datetime.utcnow().year}",
                    is_active=True,
                    created_at=datetime.utcnow()
                )
                db.session.add(scheme)
                db.session.flush()

                # Link scheme to class
                mapping = GradeGradingScheme(
                    grade_id=grade_id,
                    scheme_id=scheme.id
                )
                db.session.add(mapping)
                db.session.flush()

                # Insert new boundaries
                for b in boundaries:
                    try:
                        boundary = GradingBoundary(
                            scheme_id=scheme.id,
                            min_score=int(b.get("min_score", 0)),
                            max_score=int(b.get("max_score", 100)),
                            performance_level=b.get("performance_level"),
                            points=int(b["points"]) if b.get("points") else None,
                            descriptor=b.get("descriptor")
                        )
                        db.session.add(boundary)
                    except (ValueError, TypeError):
                        continue

        # 4️⃣ Commit all changes
        db.session.commit()
        return jsonify({"success": True})

    except Exception:
        db.session.rollback()
        current_app.logger.error("Saving grading config failed", exc_info=True)
        return jsonify({"error": "Failed to save grading configuration"}), 500





@admin_bp.route("/api/class-reports", methods=["GET"])
def class_reports_api():
    branch_id = request.args.get("branch_id", type=int)
    class_id = request.args.get("class_id", type=int)
    stream = request.args.get("stream", type=str)
    exam_id = request.args.get("exam_id", type=int)

    if not all([branch_id, class_id, exam_id]):
        return jsonify({"error": "Missing required parameters"}), 400

    # Generate reports
    reports = generate_class_reports(branch_id, class_id, stream, exam_id)

    # Only send essential info for PDF
    for r in reports:
        r.pop("subjects")  # remove subject-level details if unnecessary

    return jsonify(reports)

@admin_bp.route("/api/class-reports/pdf", methods=["GET"])
def class_reports_pdf():
    branch_id = request.args.get("branch_id", type=int)
    class_id = request.args.get("class_id", type=int)
    stream = request.args.get("stream", type=str)
    exam_id = request.args.get("exam_id", type=int)

    if not all([branch_id, class_id, exam_id]):
        return "Missing parameters", 400

    # Generate reports
    reports = generate_class_reports(branch_id, class_id, stream, exam_id)

    # Only keep essential info
    for r in reports:
        r.pop("subjects", None)
 
    # Render HTML template
    html = render_template("academics/class_ranking.html", reports=reports)
    pdf = weasyprint.HTML(string=html).write_pdf()

    # Send PDF response
    response = make_response(pdf)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f"inline; filename=Class_Ranking_{class_id}_{exam_id}.pdf"
    return response

