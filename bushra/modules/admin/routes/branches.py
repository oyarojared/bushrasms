from flask import current_app, flash, redirect, render_template, url_for, jsonify, request
from ...admin import admin_bp

from ....modals import db
from ....modals.branches_db import BranchClasses, Branch
from .. import admin_bp
from ..forms.branches_forms import (AddBranchForm, BranchesList,
                                    ExtendedBranchForm)
from ..services.grades import (
    create_class,
    is_archived_class_name,
    live_class_name,
    make_archived_class_name,
)
from ..services.branches import (get_branch_classes, 
                                get_branch_data, delete_branch_service,
                                get_first_branch_id, update_branch_service, get_branch_academic_population)
from ..utils import load_branch_choices, load_teacher_choices, apply_locked_branch, locked_branch_id
from ..services.subs import get_subjects_by_grade
from flask_login import login_required
from ..utils.file_utils import preprocess_image

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm.attributes import flag_modified
from ....modals.students_db import Student
from ....modals.assessment_db import ExamPaper, GradeGradingScheme
from ....modals.subjects_db import Lesson
from ....modals.staff_db import ClassTeacher
from flask_login import current_user


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
    form.branches.label.text = "School"
    apply_locked_branch(form.branches)

    # School-scoped users auto-load their own school; others keep previous first-branch fallback
    has_branch = locked_branch_id() or get_first_branch_id()
   
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
    if not getattr(current_user, "is_super_admin", False):
        flash("Only Super Admin can delete a branch!", "danger")
        fallback_id = get_first_branch_id()
        return redirect(
            url_for("admin.branch_profile", branch_id=fallback_id)
            if fallback_id else url_for("admin.admin_dash")
        )

    deleted, message = delete_branch_service(branch_id)

    if deleted:
        flash(message, "success")

        # recompute AFTER deletion
        fallback_id = get_first_branch_id()

        return redirect(
            url_for("admin.branch_profile", branch_id=fallback_id)
            if fallback_id else url_for("admin.admin_dash")
        )

    flash(message, "danger")

    safe_branch_id = branch_id if db.session.get(Branch, branch_id) else get_first_branch_id()

    return redirect(
        url_for("admin.branch_profile", branch_id=safe_branch_id)
        if safe_branch_id else url_for("admin.admin_dash")
    )


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



def _user_can_manage_branch(branch_id):
    if not getattr(current_user, "is_admin", False):
        return False
    if current_user.is_super_admin:
        return True
    return current_user.branch_id == int(branch_id)


def _class_student_count(class_id, stream=None):
    query = Student.query.filter_by(class_id=class_id)
    if stream:
        query = query.filter_by(stream=stream)
    return query.count()


def _class_paper_count(class_id, stream=None):
    query = ExamPaper.query.filter_by(class_id=class_id)
    if stream:
        query = query.filter_by(stream=stream)
    return query.count()


def _delete_blocked_payload(grade_name, stream_name=None, student_count=0, paper_count=0):
    if not student_count and not paper_count:
        return None

    target = f"{grade_name} · {stream_name}" if stream_name else grade_name
    unit = "stream" if stream_name else "class"

    if student_count:
        return {
            "error": f"{student_count} student(s) are still in {target}.",
            "detail": (
                f"Move those learners first. This {unit} will not be removed, "
                "and students are not deleted."
            ),
            "target": target,
            "grade_form": grade_name,
            "stream": stream_name,
            "reason": "students",
            "student_count": student_count,
            "paper_count": paper_count,
        }

    return {
        "error": f"{paper_count} exam paper(s) still belong to {target}.",
        "detail": (
            f"Results for this {unit} must be kept, so it cannot be removed yet."
        ),
        "target": target,
        "grade_form": grade_name,
        "stream": stream_name,
        "reason": "papers",
        "student_count": student_count,
        "paper_count": paper_count,
    }


@admin_bp.route("/grades/force-delete", methods=["POST"])
@login_required
def force_delete_grade():
    data = request.get_json(silent=True) or {}
    branch_id = data.get("branch_id")
    grade_id = data.get("grade_id")

    if not branch_id or not grade_id:
        return jsonify({"error": "branch_id and grade_id are required"}), 400

    if not _user_can_manage_branch(branch_id):
        return jsonify({
            "error": "Only an admin of this school can delete a class."
        }), 403

    grade = BranchClasses.query.filter_by(id=grade_id, branch_id=branch_id).first()
    if not grade:
        return jsonify({"error": "Grade not found"}), 404

    student_count = _class_student_count(grade_id)
    paper_count = _class_paper_count(grade_id)

    if student_count:
        blocked = _delete_blocked_payload(
            grade.grade_form,
            student_count=student_count,
            paper_count=paper_count,
        )
        return jsonify(blocked), 409

    original_name = live_class_name(grade.grade_form) or grade.grade_form

    if paper_count:
        if is_archived_class_name(grade.grade_form):
            return jsonify({
                "archived": True,
                "message": f"{original_name} is already hidden.",
                "target": original_name,
            }), 200
        try:
            grade.grade_form = make_archived_class_name(original_name, grade.id)
            db.session.commit()
            return jsonify({
                "archived": True,
                "message": (
                    f"{original_name} was hidden. Exam papers were kept, "
                    f"and {original_name} can be used again."
                ),
                "target": original_name,
            }), 200
        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.exception("Failed to archive empty grade")
            return jsonify({"error": "Failed to hide class"}), 500

    try:
        GradeGradingScheme.query.filter_by(grade_id=grade_id).delete()
        Lesson.query.filter_by(class_id=grade_id).delete()
        ClassTeacher.query.filter_by(class_id=grade_id).delete()
        db.session.delete(grade)
        db.session.commit()
        return jsonify({
            "message": f"{original_name} was deleted.",
            "target": original_name,
        }), 200
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Failed to delete empty grade")
        return jsonify({"error": "Failed to delete grade"}), 500


@admin_bp.route("/streams/force-delete", methods=["POST"])
@login_required
def force_delete_stream():
    data = request.get_json(silent=True) or {}
    if not data:
        return jsonify({"error": "Invalid JSON payload"}), 400

    branch_id = data.get("branch_id")
    grade_id = data.get("grade_id")
    stream_name = data.get("stream_name")

    if not all([branch_id, grade_id, stream_name]):
        return jsonify({
            "error": "branch_id, grade_id, and stream_name are required"
        }), 400

    if not _user_can_manage_branch(branch_id):
        return jsonify({
            "error": "Only an admin of this school can delete a stream."
        }), 403

    grade = BranchClasses.query.filter_by(id=grade_id, branch_id=branch_id).first()
    if not grade:
        return jsonify({"error": "Grade not found"}), 404

    student_count = _class_student_count(grade_id, stream=stream_name)
    paper_count = _class_paper_count(grade_id, stream=stream_name)

    blocked = _delete_blocked_payload(
        grade.grade_form,
        stream_name=stream_name,
        student_count=student_count,
        paper_count=paper_count,
    )
    if blocked:
        return jsonify(blocked), 409

    try:
        Lesson.query.filter_by(class_id=grade_id, stream=stream_name).delete()
        ClassTeacher.query.filter_by(class_id=grade_id, stream=stream_name).delete()

        if grade.streams and stream_name in grade.streams:
            grade.streams.remove(stream_name)
            flag_modified(grade, "streams")

        db.session.commit()
        return jsonify({
            "message": f"{grade.grade_form} · {stream_name} was removed.",
            "target": f"{grade.grade_form} · {stream_name}",
        }), 200
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Failed to delete empty stream")
        return jsonify({"error": "Failed to delete stream"}), 500


def _clean_label(value):
    return " ".join(str(value or "").split())


def _load_managed_class(posted):
    branch_id = posted.get("branch_id")
    grade_id = posted.get("grade_id")

    if not branch_id or not grade_id:
        return None, (jsonify({
            "error": "branch_id and grade_id are required"
        }), 400)

    if not _user_can_manage_branch(branch_id):
        return None, (jsonify({
            "error": "Only an admin of this school can edit a class."
        }), 403)

    grade = BranchClasses.query.filter_by(
        id=grade_id,
        branch_id=branch_id,
    ).first()
    if not grade:
        return None, (jsonify({"error": "Grade not found"}), 404)

    return grade, None


@admin_bp.route("/grades/rename", methods=["POST"])
@login_required
def rename_grade():
    posted = request.get_json(silent=True) or {}
    grade, error = _load_managed_class(posted)
    if error:
        return error

    new_name = _clean_label(posted.get("new_name"))
    if not new_name:
        return jsonify({"error": "Enter a new class name."}), 400

    if is_archived_class_name(new_name):
        return jsonify({
            "error": "That name is reserved for hidden classes.",
            "target": grade.grade_form,
        }), 400

    if is_archived_class_name(grade.grade_form):
        return jsonify({
            "error": "Hidden classes cannot be renamed.",
            "target": live_class_name(grade.grade_form),
        }), 409

    if new_name.lower() == (grade.grade_form or "").strip().lower():
        return jsonify({
            "error": f"{grade.grade_form} already has that name.",
            "target": grade.grade_form,
        }), 409

    duplicate = next(
        (
            row for row in BranchClasses.query.filter(
                BranchClasses.branch_id == grade.branch_id,
                BranchClasses.class_year == grade.class_year,
                BranchClasses.id != grade.id,
            ).all()
            if not is_archived_class_name(row.grade_form)
            and (row.grade_form or "").strip().lower() == new_name.lower()
        ),
        None,
    )
    if duplicate:
        return jsonify({
            "error": (
                f"{new_name} already exists in this school for "
                f"{grade.class_year}."
            ),
            "target": grade.grade_form,
        }), 409

    old_name = grade.grade_form
    try:
        grade.grade_form = new_name
        db.session.commit()
        return jsonify({
            "message": f"{old_name} is now {new_name}.",
            "target": new_name,
            "old_name": old_name,
        }), 200
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Failed to rename grade")
        return jsonify({"error": "Failed to rename class."}), 500


@admin_bp.route("/streams/rename", methods=["POST"])
@login_required
def rename_stream():
    posted = request.get_json(silent=True) or {}
    grade, error = _load_managed_class(posted)
    if error:
        return error

    old_name = _clean_label(posted.get("old_name"))
    new_name = _clean_label(posted.get("new_name"))

    if not old_name or not new_name:
        return jsonify({"error": "Current and new stream names are required."}), 400

    streams = list(grade.streams or [])
    has_stream_label = old_name in streams
    has_stream_students = _class_student_count(grade.id, stream=old_name) > 0
    if not has_stream_label and not has_stream_students:
        return jsonify({
            "error": f"{grade.grade_form} has no stream named {old_name}.",
            "target": f"{grade.grade_form} · {old_name}",
        }), 404

    if new_name == old_name:
        return jsonify({
            "error": f"{grade.grade_form} · {old_name} already has that name.",
            "target": f"{grade.grade_form} · {old_name}",
        }), 409

    for stream in streams:
        if stream == old_name:
            continue
        if stream.strip().lower() == new_name.lower():
            return jsonify({
                "error": f"{grade.grade_form} already has a stream named {stream}.",
                "target": f"{grade.grade_form} · {old_name}",
            }), 409

    try:
        if old_name in streams:
            streams[streams.index(old_name)] = new_name
        else:
            streams.append(new_name)
        grade.streams = streams
        flag_modified(grade, "streams")

        Student.query.filter_by(class_id=grade.id, stream=old_name).update(
            {Student.stream: new_name},
            synchronize_session=False,
        )
        ExamPaper.query.filter_by(class_id=grade.id, stream=old_name).update(
            {ExamPaper.stream: new_name},
            synchronize_session=False,
        )
        Lesson.query.filter_by(class_id=grade.id, stream=old_name).update(
            {Lesson.stream: new_name},
            synchronize_session=False,
        )
        ClassTeacher.query.filter_by(class_id=grade.id, stream=old_name).update(
            {ClassTeacher.stream: new_name},
            synchronize_session=False,
        )

        db.session.commit()
        return jsonify({
            "message": f"{grade.grade_form} · {old_name} is now {new_name}.",
            "target": f"{grade.grade_form} · {new_name}",
            "old_name": f"{grade.grade_form} · {old_name}",
        }), 200
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Failed to rename stream")
        return jsonify({"error": "Failed to rename stream."}), 500
