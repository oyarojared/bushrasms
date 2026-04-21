import re

from flask import (current_app, flash, redirect, render_template, request,
                   send_file, session, url_for, jsonify)
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from ....modals import db
from ....modals.branches_db import Branch, BranchClasses
from ....modals.staff_db import Teacher, ClassTeacher
from ....modals.subjects_db import Lesson
from .. import admin_bp

from ..data import lessons_data
from ..forms.branches_forms import BranchesList
from ..forms.staff_forms import AddTeacherForm, TeacherPassportUploadForm
from ..utils import (check_unique_teacher_fields, generate_excel_file,
                     generate_initial_password, generate_username,
                     is_phone_correct_format, load_branch_choices,
                     preprocess_image)

from flask_login import login_required, current_user


@admin_bp.route("/school_staff", methods=["GET", "POST"])
@login_required
def school_staff():
    add_teacher_form = AddTeacherForm()
    filter_branches_form = BranchesList()

    add_teacher_form.branches.choices = load_branch_choices()
    filter_branches_form.branches.choices = load_branch_choices()

    # -------------------------------------------------
    # PROCESS POST → Add Teacher
    # -------------------------------------------------
    if request.method == "POST" and add_teacher_form.validate_on_submit():

        # Clean & normalize inputs
        fullname = (add_teacher_form.fullname.data or "").strip()
        title = add_teacher_form.title.data
        employer = add_teacher_form.employer.data
        gender = add_teacher_form.gender.data
        phone = (add_teacher_form.phone.data or "").strip()
        staff_id = (add_teacher_form.staff_id.data or "").strip()
        tsc_no = (add_teacher_form.tsc_no.data or "").strip()
        email = (add_teacher_form.email.data or "").strip().lower()
        id_no = add_teacher_form.id_no.data
        branch_id = add_teacher_form.branches.data

        if not branch_id or not branch_id.isdigit():
            flash("Invalid branch selected.", "danger")
            return redirect(url_for("admin.school_staff"))

        branch_id_int = int(branch_id)

        if not Branch.query.get(branch_id_int):
            flash("Selected branch does not exist.", "danger")
            return redirect(url_for("admin.school_staff"))

        if staff_id:
            existing_staff = Teacher.query.filter(
                Teacher.staff_id == staff_id, Teacher.branch_id == branch_id_int
            ).first()

            if existing_staff:
                flash(
                    f"Teacher Code '{staff_id}' already exists in this branch.",
                    "danger",
                )
                return redirect(url_for("admin.school_staff"))

        if not is_phone_correct_format(phone):
            flash(
                "Invalid phone number format. Use 0712345678 or +254712345678 phone formats.",
                "danger",
            )
            return redirect(url_for("admin.school_staff"))


        duplicate = check_unique_teacher_fields(
            phone=phone, email=email, tsc_no=tsc_no, id_no=id_no
        )

        if duplicate:
            field = duplicate.get("field")
            messages = {
                "phone": f"Teacher with this phone Number '{phone}' already exist!",
                "email": f"Teacher with this email '{email}' already exist!",
                "tsc_no": f"Teacher with this TSC No '{tsc_no}' already exist!",
                "id_no": f"Teacher with this ID Number '{id_no}' already exist!",
                "unknown": "Duplicate data detected!",
            }

            flash(messages[field], "danger")
            return redirect(url_for("admin.school_staff"))

        # SAVE TEACHER
        try:
            new_teacher = Teacher(
                fullname=fullname,
                title=title,
                employer=employer,
                gender=gender,
                phone=phone or None,
                email=email or None,
                staff_id=staff_id.upper() or None,
                tsc_no=tsc_no or None,
                id_no=id_no or None,
                branch_id=branch_id_int,
                username=generate_username(fullname, str(phone)),
                password_hash=generate_initial_password(str(phone)),
            )

            db.session.add(new_teacher)
            db.session.commit()

            flash(f"Teacher added successfully!", "success")
            return redirect(url_for("admin.school_staff"))

        except Exception as e:
            db.session.rollback()
            flash("An error occurred while saving teacher.", "danger")
            return redirect(url_for("admin.school_staff"))

    if request.method == "POST" and "add-teacher" in request.form and not add_teacher_form.validate_on_submit():
        # Catch form related errors that wasn't caught above.
        flash(
            "Oop! There is something wrong with the data you entered.",
            "danger"
        )
        return redirect(url_for("admin.school_staff"))

    # -------------------------------------------------
    # GET REQUEST → FILTER TEACHERS
    # -------------------------------------------------
    branch_filter = request.args.get("branches", "")

    if branch_filter and branch_filter.isdigit():
        teachers = (
            Teacher.query
            .filter(
                Teacher.branch_id == int(branch_filter), 
            )
            .order_by(Teacher.created_at.desc())
            .all()
        )
        filter_branches_form.branches.data = branch_filter

    else:
        query = Teacher.query
        # Load only teachers who belong to admin's branch
        if current_user.is_admin and not current_user.is_super_admin:
            teachers = (
                query.filter(current_user.branch_id==Teacher.branch_id)
                .order_by(Teacher.created_at.desc())
                .all()
            )
        else:
            # Load all teachers across all branches for super_admin.
            teachers = query.order_by(Teacher.created_at.desc()).all()
            
    # -------------------------------------------------
    # RENDER PAGE
    # -------------------------------------------------
    return render_template(
        "staff_templates/staff.html",
        add_teacher_form=add_teacher_form,
        filter_branches_form=filter_branches_form,
        teachers=teachers,
        title="School Staff",
        active_page="school_staff",
    )


@admin_bp.route("/teacher_profile/<int:teacher_id>", methods=["GET", "POST"])
@login_required
def teacher_profile(teacher_id):
    move_form = BranchesList()
    move_form.branches.choices = load_branch_choices()

    try:
        teacher = Teacher.query.get(teacher_id)
        if not teacher:
            flash("Teacher not found!", "danger")
            return redirect(url_for("admin.school_staff"))

        branch = Branch.query.get(teacher.branch_id)
        if not branch:
            flash("Branch not found!", "danger")
            return redirect(url_for("admin.school_staff"))

    except Exception as e:
        flash("Unknown error occurred!", "danger")
        return redirect(url_for("admin.school_staff"))

    return render_template(
        "staff_templates/teacher_profile.html",
        title="Teacher Profile",
        teacher=teacher,
        branch_name=branch.branch_name,
        lessons=lessons_data,
        move_form=move_form,
        active_page="school_staff",
    )


@admin_bp.route("/upload_teacher_passport", methods=["POST"])
@login_required
def upload_teacher_passport():
    passport_form = TeacherPassportUploadForm()
    previous = request.headers.get("Referer")

    # Default fallback redirect
    fallback_redirect = (
        redirect(previous) if previous else redirect(url_for("admin.admin_dash"))
    )

    # 2. FORM VALIDATION CHECK
    if not passport_form.validate_on_submit():
        flash("Invalid image file. Please try again.", "warning")
        return fallback_redirect

    # 3. MAIN PROCESS
    try:
        image = passport_form.passport.data
        filename = preprocess_image(image, size=(150, 150))
        current_user.passport_url = filename
        db.session.commit()

        flash("Profile photo updated successfully!", "success")
        return fallback_redirect

    except Exception as e:
        current_app.logger.error(f"[UPLOAD_PASSPORT_ERROR] {e}")
        db.session.rollback()
        flash("Unexpected server error while saving image!", "danger")
        return fallback_redirect


@admin_bp.route("/delete_teacher/<int:teacher_id>", methods=["POST"])
@login_required
def delete_teacher(teacher_id):
    prev_url = request.headers.get("Referer") or url_for("admin.school_staff")

    try:
        target_teacher = Teacher.query.get(teacher_id)
        if not target_teacher:
            flash("Teacher not found.", "warning")
            return redirect(prev_url)

        db.session.delete(target_teacher)
        db.session.commit()

        flash("Teacher deleted successfully.", "success")

    except Exception as e:
        db.session.rollback()
        flash("Teacher could not be deleted due to a system error.", "danger")
        current_app.logger.error(f"Teacher deletion FAILED: {e}")

    return redirect(prev_url)


@admin_bp.route("/move_teacher/<int:teacher_id>", methods=["POST"])
@login_required
def move_teacher(teacher_id):
    move_form = BranchesList()
    move_form.branches.choices = load_branch_choices()

    prev_url = request.headers.get("Referer") or url_for("admin.school_staff")

    teacher = Teacher.query.get(teacher_id)
    if not teacher:
        flash("Teacher not found.", "warning")
        return redirect(prev_url)

    if not move_form.validate_on_submit():
        flash("Invalid submission. Please try again.", "danger")
        return redirect(prev_url)

    #  Check if user is choosing the same branch (no unnecessary DB change)
    new_branch = move_form.branches.data
    if teacher.branch_id == int(new_branch):
        flash("Teacher is already in this branch.", "warning")
        return redirect(prev_url)

    teacher.branch_id = new_branch
    try:
        # Remove all lessons allocation in previous branch.
        lessons = Lesson.query.filter_by(teacher_id=teacher.id).all()
        if lessons:
           for l in lessons:
               db.session.delete(l)

        # Remove class teacher role in previous branch.
        heading_classes = ClassTeacher.query.filter_by(teacher_id=teacher.id).all()
        if heading_classes:
            for kls in heading_classes:
                db.session.delete(kls)

        db.session.commit()
        flash("Teacher moved successfully.", "success")

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to move teacher {teacher_id}: {e}")
        flash("Something went wrong. Please try again later.", "danger")

    return redirect(prev_url)



@admin_bp.route("/update_teacher/<int:teacher_id>", methods=["POST"])
@login_required
def update_teacher(teacher_id):
    update_form = AddTeacherForm()
    update_form.branches.choices = load_branch_choices()

    if not update_form.validate_on_submit():
        flash("Invalid data submitted.", "danger")
        return redirect(url_for("admin.school_staff"))

    teacher = Teacher.query.get_or_404(teacher_id)

    # ---------------------------------------
    # CLEAN + NORMALIZE INPUTS
    # ---------------------------------------
    fullname = (update_form.fullname.data or "").strip()
    title = update_form.title.data
    employer = update_form.employer.data
    gender = update_form.gender.data

    phone = (update_form.phone.data or "").replace(" ", "")
    staff_id = (update_form.staff_id.data or "").strip()
    tsc_no = (update_form.tsc_no.data or "").strip()
    email = (update_form.email.data or "").strip().lower()
    id_no = (update_form.id_no.data or "")
    branch_id = update_form.branches.data

    # Branch validation
    if not branch_id or not str(branch_id).isdigit():
        flash("Invalid branch selected.", "danger")
        return redirect(url_for("admin.school_staff"))

    branch_id = int(branch_id)

    if not Branch.query.get(branch_id):
        flash("Selected branch does not exist.", "danger")
        return redirect(url_for("admin.school_staff"))

    # ---------------------------------------
    # STAFF ID (unique per branch)
    # ---------------------------------------
    if staff_id:
        existing_staff = Teacher.query.filter(
            Teacher.staff_id == staff_id,
            Teacher.branch_id == branch_id,
            Teacher.id != int(teacher_id)   # ignore current teacher
        ).first()

        if existing_staff:
            flash(
                f"Teacher Code '{staff_id}' already exists in this branch.",
                "danger",
            )
            return redirect(url_for("admin.school_staff"))

    if not is_phone_correct_format(phone):
        flash(
            "Invalid phone number format. Use 0712345678 or +254712345678.",
            "danger",
        )
        return redirect(url_for("admin.school_staff"))

    # ---------------------------------------
    # DUPLICATE CHECKS (IGNORE CURRENT TEACHER)
    # ---------------------------------------
    duplicate = check_unique_teacher_fields(
        phone=phone,
        email=email,
        tsc_no=tsc_no,
        id_no=id_no,
        exclude_id=int(teacher_id)
    )

    if duplicate:
        field = duplicate.get("field")
        messages = {
            "phone": f"Teacher with this phone '{phone}' already exists!",
            "email": f"Teacher with this email '{email}' already exists!",
            "tsc_no": f"Teacher with this TSC No '{tsc_no}' already exists!",
            "id_no": f"Teacher with this ID '{id_no}' already exists!",
            "unknown": "Duplicate data detected.",
        }
        flash(messages[field], "danger")
        return redirect(url_for("admin.school_staff"))


    # ---------------------------------------
    # UPDATE TEACHER SAFELY
    # ---------------------------------------
    try:
        teacher.fullname = fullname
        teacher.title = title or ""
        teacher.employer = employer
        teacher.gender = gender
        teacher.phone = phone
        teacher.email = email or None
        teacher.staff_id = staff_id or None
        teacher.tsc_no = tsc_no or None
        teacher.id_no = id_no or None
        teacher.branch_id = branch_id

        db.session.commit()

        flash("Teacher updated successfully!", "success")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating teacher: {e}")
        flash("An error occurred while updating teacher.", "danger")
    return redirect(url_for("admin.school_staff"))



@admin_bp.route("/api/save-class-teacher", methods=["POST"])
@login_required
def save_class_teacher():
    data = request.get_json()

    # Extract data
    branch_id = data.get("branch_id")
    class_id = data.get("class_id")
    stream = data.get("stream")
    teacher_id = data.get("teacher_id")

    # --- Validation ---
    if not branch_id or not class_id or not teacher_id:
        return jsonify({"success": False, "message": "Branch, class, and teacher are required"}), 400

    # Check if branch exists
    branch = Branch.query.get(branch_id)
    if not branch:
        return jsonify({"success": False, "message": "Invalid branch"}), 404

    # Check if class exists
    class_obj = BranchClasses.query.filter_by(id=class_id, branch_id=branch_id).first()
    if not class_obj:
        return jsonify({"success": False, "message": "Class does not exist in this branch"}), 404

    # Check if teacher exists
    teacher = Teacher.query.get(teacher_id)
    if not teacher:
        return jsonify({"success": False, "message": "Teacher does not exist"}), 404

    # Optional: Check if stream exists for this class
    if stream:
        if stream not in class_obj.streams:  # assuming class_obj.streams is a list/JSON column
            return jsonify({"success": False, "message": "Invalid stream for this class"}), 400

    # --- Save / Update ---
    try:
        class_teacher = ClassTeacher.query.filter_by(
            branch_id=branch_id, class_id=class_id, stream=stream
        ).first()

        if class_teacher:
            class_teacher.teacher_id = teacher_id
        else:
            class_teacher = ClassTeacher(
                branch_id=branch_id,
                class_id=class_id,
                stream=stream,
                teacher_id=teacher_id
            )
            db.session.add(class_teacher)

        db.session.commit()

        return jsonify({"success": True, "teacher_name": f"{teacher.fullname}"})

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"success": False, "message": "Database error occurred"}), 500
