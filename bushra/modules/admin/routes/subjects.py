from flask import render_template,request,flash, redirect, url_for, jsonify, current_app
from ...admin import admin_bp 

from ..forms.branches_forms import GradeSelectForm
from ..forms.subject_forms import SubjectForm, DeleteSubjectForm, BranchGradeSelectionForm
from ..services.grades import load_grades
from ..utils import load_branch_choices 
from ....modals.branches_db import BranchClasses, db
from ....modals.subjects_db import Lesson

from ..services.subs import get_subjects, delete_subject_service, add_subject, update_subject_service,get_subjects_by_grade
from flask_login import login_required

from ..utils.route_protect import admin_required

@admin_bp.route("/subjects_dash", methods=["GET", "POST"])
@login_required
@admin_required
def subjects_dash(): 
    del_subject_form = DeleteSubjectForm()
    grade_form = GradeSelectForm()
    subject_form = SubjectForm()
    branch_grade_selection_form = BranchGradeSelectionForm()
    
    grade_form.grade_select.choices = load_grades()
    branch_grade_selection_form.branches.choices = load_branch_choices()
    branch_grade_selection_form.grades.choices = load_grades()
    
    # Load subject data for display.
    subjects, error_sms = get_subjects() 
    if error_sms: flash (error_sms, "danger")
    
    subject_id_flag = request.form.get("subject_id")
    
    if subject_form.validate_on_submit():
        selected_grades = request.form.getlist("subject_grades")

        if subject_id_flag:
            updated, msg = update_subject_service(
                subject_id=int(subject_id_flag),
                form=subject_form,
                selected_grades=selected_grades
            )
            
            flash(msg, "success" if updated else "danger")
            return redirect(url_for("admin.subjects_dash"))

        success, err = add_subject(subject_form, selected_grades)

        if success:
            flash("Subject added successfully.", "success")
        else:
            error_map = {
                "NO_GRADES": "Failed to add subject! You did not assign the subject you entered to any class.",
                "DUPLICATE": "A subject with this name or code already exists.",
                "DB_ERROR": "Database error occurred.",
                "SYSTEM_ERROR": "Unexpected system error occurred."
            }
            flash(error_map.get(err, "Operation failed."), "danger")

        return redirect(url_for("admin.subjects_dash"))
    
    form_has_errors = False

    if subject_form.errors:
        form_has_errors = True

        
    return render_template(
        "academics/base.html",
        form_has_errors=form_has_errors,
        grade_form=grade_form,
        subject_form=subject_form,
        grades=load_grades()[1:],
        subjects=subjects,
        del_subject_form=del_subject_form,
        branch_grade_selection_form=branch_grade_selection_form,
        active_page="subjects",
    )


@admin_bp.route("/delete_subject/<int:subject_id>", methods=["POST"])
@login_required
@admin_required
def delete_subject(subject_id):
    success, error = delete_subject_service(subject_id)

    if success:
        flash("Subject deleted successfully.", "success")
    else:
        flash(error or "Delete failed.", "danger")

    return redirect(url_for("admin.subjects_dash"))



@admin_bp.route("/subjects/by-grade")
@login_required
def subjects_by_grade():
    grade_form = request.args.get("grade_form")

    if not grade_form:
        return "", 400

    subjects = get_subjects_by_grade(grade_form)

    return render_template(
        "academics/_subjects_table.html",
        subjects_data=subjects
    )



@admin_bp.route("/subjects/by-grade-json")
@login_required
def subjects_by_grade_json():
    grade_form = request.args.get("grade_form")

    if not grade_form:
        return jsonify([])  # return empty list if no grade

    subjects = get_subjects_by_grade(grade_form)

    # Convert to JSON-serializable format
    subjects_data = [{"id": s.id, "name": s.name} for s in subjects]

    return jsonify(subjects_data)

    

@admin_bp.route("/api/save-teacher-assignments", methods=["POST"])
@login_required
@admin_required
def save_teacher_assignments():
    data = request.get_json(silent=True) or {}

    branch_id = data.get("branch_id")
    class_id = data.get("class_id")
    stream = data.get("stream")
    assignments = data.get("assignments", [])

    if not branch_id or not class_id or not assignments:
        return jsonify({"success": False, "error": "Missing required data"}), 400

    try:
        for a in assignments:
            subject_id = a.get("subject_id")
            teacher_id = a.get("teacher_id")  # can be None
                
            # Find existing lesson
            lesson = Lesson.query.filter_by(
                branch_id=branch_id,
                class_id=class_id,
                stream=stream,
                subject_id=subject_id
            ).first()

            if lesson:
                # Remove assignment- previous teacher removed.
                if not teacher_id:
                    db.session.delete(lesson)
                    
                # Update assigned teacher
                lesson.teacher_id = teacher_id
            else:
                # Create new lesson assignment only if teacher selected
                if teacher_id:
                    new_lesson = Lesson(
                        branch_id=branch_id,
                        class_id=class_id,
                        stream=stream,
                        subject_id=subject_id,
                        teacher_id=teacher_id
                    )
                    db.session.add(new_lesson)

        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error saving teacher assignments")
        return jsonify({"success": False, "error": "Internal server error"}), 500
