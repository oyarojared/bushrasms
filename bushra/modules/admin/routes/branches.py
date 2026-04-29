from flask import current_app, flash, redirect, render_template, url_for, jsonify, request
from ...admin import admin_bp

from ....modals import db
from ....modals.branches_db import BranchClasses, Branch
from .. import admin_bp
from ..forms.branches_forms import (AddBranchForm, BranchesList,
                                    ExtendedBranchForm)
from ..services.grades import create_class
from ..services.branches import (get_branch_classes, 
                                get_branch_data, delete_branch_service,
                                get_first_branch_id, update_branch_service, get_branch_academic_population)
from ..utils import load_branch_choices, load_teacher_choices
from ..services.subs import get_subjects_by_grade
from flask_login import login_required
from ..utils.file_utils import preprocess_image

from sqlalchemy.exc import SQLAlchemyError
from ....modals.students_db import Student, StudentSubjectAllocation 
from ....modals.assessment_db import ExamPaper, StudentExamMark, GradeGradingScheme
from ....modals.subjects_db import Lesson


@admin_bp.route("/add_school", methods=["POST"])
@login_required
def add_school():
    """
    Handle creation of a new school (branch).
    """
    form = AddBranchForm()
    form.branch_head.choices = load_teacher_choices()

    fallback_id = get_first_branch_id()

    target = (
        url_for("admin.branch_profile", branch_id=fallback_id)
        if fallback_id else url_for("admin.admin_dash")
    )
 
    if form.validate_on_submit():
        try:
            # Process logo if uploaded
            logo_filename = None
            if form.logo.data:
                logo_filename = preprocess_image(form.logo.data, size=(200, 200))
            
            # Create Branch object
            branch = Branch(
                branch_name=form.branch_name.data.strip(),
                school_code=form.school_code.data,
                branch_manager=form.branch_manager.data.strip(),
                branch_level=form.branch_level.data,
                branch_head=form.branch_head.data or None,
                school_gender=form.school_gender.data,
                school_type=form.school_type.data,
                email=form.email.data.strip() if form.email.data else None,
                logo=logo_filename,
                motto=form.motto.data.strip() if form.motto.data else None
            ) 
            
            db.session.add(branch)
            db.session.commit()

            flash(f"School {branch.branch_name.upper() } added successfully!", "success")
            return redirect(url_for("admin.branch_profile", branch_id=branch.id))
        
        except Exception as e:
            db.session.rollback() 
            current_app.logger.error(
                "Error adding school %s: %s",
                form.branch_name.data,
                e
            )
            flash("Oops! Something went wrong. Please try again later.", "danger")
            return redirect(target)

    # Form validation failed
    if form.errors:
        for field, errors in form.errors.items():
            for err in errors:
                flash(f"{field.capitalize()}: {err}", "danger")

    return redirect(target)

 
@admin_bp.route("/branch/<int:branch_id>")
@login_required
def branch_profile(branch_id):
    select_branch_form = BranchesList()
    select_branch_form.branches.choices = load_branch_choices()
    
    add_branch_form = AddBranchForm()
    add_branch_form.branch_head.choices = load_teacher_choices()

    data, error = get_branch_data(branch_id)

    if error: 
        # flash(error, 'warning')
        fallback_id = get_first_branch_id() 

        if fallback_id and fallback_id != branch_id:
            return redirect(url_for("admin.branch_profile", branch_id=fallback_id))

        # No branches at all
        branch_id=0

    return render_template(
        "schools.html",
        data=data,
        select_branch_form=select_branch_form,
        branch_id=branch_id,
        add_branch_form=add_branch_form,
    )


@admin_bp.route("/grades_forms", methods=["GET", "POST"])
@login_required
def grades_forms():
    form = ExtendedBranchForm()
    
    form.branches.choices = load_branch_choices() 

    # check availability of any branch 
    has_branch = get_first_branch_id()
   
    if form.validate_on_submit():
        cls, sms = create_class(form)
        if cls:
            flash(sms, "success") 
        if not cls:
            flash(sms, "danger")
        return redirect(url_for("admin.grades_forms"))

    else:
        # Handle validation errors.(form is invalid)
        for field, errors in form.errors.items():
            for err in errors:
                flash(f"{field}: {err}", "danger")

    branch_data = get_branch_classes()
    
    return render_template(
        "classes.html", 
        load_branches_form=form, 
        branch_data=branch_data,
        has_branch=has_branch
    )


@admin_bp.route("/delete_branch/<int:branch_id>", methods=["POST"])
@login_required
def delete_branch(branch_id):
    deleted, message = delete_branch_service(branch_id)

    if deleted:  
        flash(message, "success")
 
        fallback_id = get_first_branch_id()

        if fallback_id:
            return redirect(url_for("admin.branch_profile", branch_id=fallback_id))
        
        # If no branches remain
        return redirect(url_for("admin.admin_dash"))

    # Deletion failed → show error
    flash(message, "danger")

    # Redirect safely
    safe_branch_id = branch_id if Branch.query.get(branch_id) else get_first_branch_id()

    if safe_branch_id:
        return redirect(url_for("admin.branch_profile", branch_id=safe_branch_id))

    return redirect(url_for("admin.admin_dash"))


@admin_bp.route("/update_branch/<int:branch_id>", methods=["POST"])
@login_required
def update_branch(branch_id):
    form = AddBranchForm()

    form.branch_head.choices = load_teacher_choices()
    form.branch_id = branch_id
    fallback_id = get_first_branch_id()

    # ---- If form is valid → proceed to update ----
    if form.validate_on_submit():
        updated, message = update_branch_service(form, branch_id)

        if updated:
            flash(message, "success")
            return redirect(url_for("admin.branch_profile", branch_id=updated.id))

        flash(message, "warning")
        return redirect(url_for("admin.branch_profile", branch_id=fallback_id))

    # ---- If form has validation errors → flash them ----
    if form.errors:
        for field, errors in form.errors.items():
            for error in errors:   
                flash(f"{field.replace('_', ' ').title()}: {error}", "danger")

    return redirect(url_for("admin.branch_profile", branch_id=fallback_id))



@admin_bp.route("/branches/<int:branch_id>/academic-data", methods=["GET"])
@login_required
def branch_academic_data(branch_id):
    """
    Returns academic population data for a branch:
    - Grades / Forms
    - Gender counts
    - Stream breakdowns (if applicable)
    """

    data, error = get_branch_academic_population(branch_id)

    if error:
        return jsonify({
            "status": "error",
            "message": error
        }), 404
        
    # return "Hello flask"

    return jsonify({
        "status": "success",
        "data": data
    }), 200



@admin_bp.route("/grades/force-delete", methods=["POST"]) 
@login_required
def force_delete_grade():
    data = request.get_json(silent=True)
    branch_id = data.get("branch_id")
    grade_id = data.get("grade_id")

    if not branch_id or not grade_id:
        return jsonify({"error": "branch_id and grade_id are required"}), 400

    try:
        grade = BranchClasses.query.filter_by(id=grade_id, branch_id=branch_id).first()
        if not grade:
            return jsonify({"error": "Grade not found"}), 404

        # -----------------------------
        # 0️⃣ Delete related grading schemes
        # ----------------------------- 
        GradeGradingScheme.query.filter_by(grade_id=grade_id).delete()
        db.session.flush()

        # -----------------------------
        # 1️⃣ Delete dependent exam marks
        # -----------------------------
        exam_papers = ExamPaper.query.filter_by(class_id=grade_id).all()
        for paper in exam_papers:
            StudentExamMark.query.filter_by(exam_paper_id=paper.id).delete()
        db.session.flush()

        # -----------------------------
        # 2️⃣ Delete exam papers
        # -----------------------------
        ExamPaper.query.filter_by(class_id=grade_id).delete()
        db.session.flush()

        # -----------------------------
        # 3️⃣ Delete lessons
        # -----------------------------
        Lesson.query.filter_by(class_id=grade_id).delete()
        db.session.flush()

        # -----------------------------
        # 4️⃣ Delete student subject allocations
        # -----------------------------
        students = Student.query.filter_by(class_id=grade_id).all()
        for student in students:
            StudentSubjectAllocation.query.filter_by(student_id=student.id).delete()
        db.session.flush()

        # -----------------------------
        # 5️⃣ Delete students
        # -----------------------------
        Student.query.filter_by(class_id=grade_id).delete()
        db.session.flush()

        # -----------------------------
        # 6️⃣ Delete the grade itself
        # -----------------------------
        db.session.delete(grade)
        db.session.commit()

        return jsonify({"message": f"Grade '{grade.grade_form}' and all related data deleted successfully"}), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(str(e))
        return jsonify({"error": "Failed to force delete grade"}), 500


@admin_bp.route("/streams/force-delete", methods=["POST"])
@login_required
def force_delete_stream():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON payload"}), 400

    branch_id = data.get("branch_id")
    grade_id = data.get("grade_id")
    stream_name = data.get("stream_name")

    if not all([branch_id, grade_id, stream_name]):
        return jsonify({"error": "branch_id, grade_id, and stream_name are required"}), 400

    try:
        grade = BranchClasses.query.filter_by(id=grade_id, branch_id=branch_id).first()
        if not grade:
            return jsonify({"error": "Grade not found"}), 404

        # -----------------------------
        # 1️⃣ Delete dependent exam marks
        # -----------------------------
        exam_papers = ExamPaper.query.filter_by(class_id=grade_id, stream=stream_name).all()
        for paper in exam_papers:
            StudentExamMark.query.filter_by(exam_paper_id=paper.id).delete()
        db.session.flush()

        # -----------------------------
        # 2️⃣ Delete exam papers
        # -----------------------------
        ExamPaper.query.filter_by(class_id=grade_id, stream=stream_name).delete()
        db.session.flush()

        # -----------------------------
        # 3️⃣ Delete lessons
        # -----------------------------
        Lesson.query.filter_by(class_id=grade_id, stream=stream_name).delete()
        db.session.flush()

        # -----------------------------
        # 4️⃣ Delete students in stream
        # -----------------------------
        students = Student.query.filter_by(class_id=grade_id, stream=stream_name).all()
        for student in students:
            StudentSubjectAllocation.query.filter_by(student_id=student.id).delete()
        Student.query.filter_by(class_id=grade_id, stream=stream_name).delete()
        db.session.flush()

        # -----------------------------
        # 5️⃣ Remove stream from grade JSON
        # -----------------------------
        if grade.streams and stream_name in grade.streams:
            grade.streams.remove(stream_name)

        db.session.commit()

        return jsonify({"message": f"Stream '{stream_name}' and all related data deleted successfully"}), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(str(e))
        return jsonify({"error": "Failed to force delete stream"}), 500
