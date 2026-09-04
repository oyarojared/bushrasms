from flask import flash, render_template, url_for, redirect
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from ....modals.branches_db import Branch, BranchClasses, db
from ....modals.staff_db import Teacher
from ....modals.students_db import Student
from .. import admin_bp

from flask_login import current_user, login_required
from sqlalchemy.orm import aliased

from ..utils.route_protect import admin_required
from ..utils.class_teacher import dashboard_class_performance
from ..utils.teacher_utils import can_reset_teacher_password
from ..services.grades import live_class_name, sort_grade_list
from ....modals.subjects_db import Lesson


@admin_bp.route("/admin_dash")
@login_required
@admin_required
def admin_dash():

    # Alias Teacher for school head join
    HeadTeacher = aliased(Teacher)

    # ==========================================================
    # 1. BRANCH METADATA + SCHOOL HEAD NAME
    # ==========================================================
    branches_meta = (
        db.session.query(
            Branch.id.label("id"),
            Branch.branch_name.label("name"),
            Branch.branch_manager.label("manager"),
            Branch.branch_level.label("level"),
            HeadTeacher.fullname.label("head_name"),
            Branch.school_gender.label("gender"),
            Branch.school_type.label("type"), 
            Branch.email.label("email"),
            Branch.motto.label("motto"),
            Branch.school_code.label("code"),
            Branch.created_at.label("created_at"),
            Branch.updated_at.label("updated_at"),
        )
        .outerjoin(HeadTeacher, HeadTeacher.id == Branch.branch_head)
        .all()
    )

    # ==========================================================
    # 2. STUDENT COUNT PER BRANCH
    # ==========================================================
    branch_counts = (
        db.session.query(
            Branch.id.label("branch_id"),
            func.count(Student.id).label("population")
        )
        .outerjoin(Student, Branch.id == Student.branch_id)
        .group_by(Branch.id)
        .all()
    )

    branch_pop_map = {r.branch_id: r.population for r in branch_counts}

    # ==========================================================
    # 3. TEACHER COUNT PER BRANCH
    # ==========================================================
    teacher_counts = (
        db.session.query(
            Branch.id.label("branch_id"),
            func.count(Teacher.id).label("teacher_count")
        )
        .outerjoin(Teacher, Branch.id == Teacher.branch_id)
        .group_by(Branch.id)
        .all()
    )

    teacher_count_map = {r.branch_id: r.teacher_count for r in teacher_counts}

    total_teachers = None
    if current_user.is_super_admin:
        total_teachers = sum(teacher_count_map.values())
    else:
        total_teachers = teacher_count_map[current_user.branch_id]

    # ==========================================================
    # 4. STUDENTS PER CLASS
    # ==========================================================
    class_counts = (
        db.session.query(
            BranchClasses.id.label("class_id"),
            BranchClasses.branch_id.label("branch_id"),
            BranchClasses.grade_form.label("grade_form"),
            BranchClasses.class_year.label("class_year"),
            BranchClasses.streams.label("streams"),
            func.count(Student.id).label("population"),
        )
        .outerjoin(Student, BranchClasses.id == Student.class_id)
        .group_by(BranchClasses.id)
        .all()
    )

    class_map = {}
    for r in class_counts:
        class_map.setdefault(r.branch_id, []).append(
            {
                "class_id": r.class_id,
                "grade_form": r.grade_form,
                "class_year": r.class_year,
                "streams": r.streams,
                "population": r.population,
            }
        )

    # ==========================================================
    # 5. FINAL BRANCH STRUCTURE
    # ==========================================================
    is_developer = (
        current_user.username == "omongare782"
        and current_user.phone == "0701948782"
        and current_user.is_super_admin
    )

    is_just_admin = (
        current_user.is_admin
        and not current_user.is_super_admin
    )
    
    branches_list = []
    for b in branches_meta:
        # Load all schools if user is super admin

        if is_just_admin:
            pass
        elif not is_developer and b.id > 10:
            continue

        branches_list.append(
            {
                "id": b.id,
                "name": b.name,
                "manager": b.manager, 
                "level": b.level,
                "motto": b.motto,
                "head": b.head_name or "Not Assigned",
                "gender": b.gender,
                "type": b.type,
                "email": b.email,
                "code": b.code,
                "created_at": b.created_at,
                "updated_at": b.updated_at,
                "population": branch_pop_map.get(b.id, 0),
                "teacher_count": teacher_count_map.get(b.id, 0),
                "staff_count": 0,
                "classes": class_map.get(b.id, []),
            }
        )

    total_students = None
    single_branch = [] 

    if current_user.is_super_admin:
        # Return all students across all branches
        total_students = sum(b["population"] for b in branches_list)
    else:
        for b in branches_list:
            if b["id"] == current_user.branch_id:
                total_students = b["population"] # Only students of the user branch
                single_branch.append(b) 

    # ==========================================================
    # 6. RENDER
    # ==========================================================
    return render_template(
        "admin_templates/admin_dash.html",
        branches=branches_list if current_user.is_super_admin else single_branch,
        tot_students=total_students,
        total_teachers=total_teachers, 
    )


@admin_bp.route("/manage_accounts")
@login_required
@admin_required
def manage_accounts():

    teachers = Teacher.query.all()
    resettable_ids = {
        teacher.id
        for teacher in teachers
        if can_reset_teacher_password(current_user, teacher)
    }

    # allow BOTH admin and super admin
    if current_user.is_admin or current_user.is_super_admin:

        return render_template(
            "admin_templates/accounts.html",
            teachers=teachers,
            resettable_ids=resettable_ids,
        )

    flash(
        "Access denied: Admin or Super Admin only",
        "danger"
    )
    return redirect(url_for("admin.admin_dash"))


@admin_bp.route("/toggle-super-admin/<int:teacher_id>", methods=["POST"])
@login_required
@admin_required
def toggle_super_admin(teacher_id):

    # ONLY SUPER ADMIN CAN ASSIGN SUPER ADMIN PREVILLAGES
    if not current_user.is_super_admin:
        flash("Only Super Admin can modify super admin status", "danger")
        return redirect(url_for("admin.manage_accounts"))

    teacher = Teacher.query.get_or_404(teacher_id)

    # OPTIONAL SAFETY: prevent self-lockout mistakes
    if teacher.id == current_user.id:
        flash("You cannot modify your own super admin status", "warning")
        return redirect(url_for("admin.manage_accounts"))

    teacher.is_super_admin = not teacher.is_super_admin
    # Toggle admin previlleges for super admin.
    if not teacher.is_admin and teacher.is_super_admin:
        teacher.is_admin = True
    db.session.commit()

    flash("Super admin status updated", "success")
    return redirect(url_for("admin.manage_accounts"))


@admin_bp.route("/teachers/<int:teacher_id>/toggle-admin", methods=["POST"])
@admin_required
def toggle_admin(teacher_id):
    teacher = Teacher.query.get_or_404(teacher_id)

    # Prevent accidental lockout logic (optional later)
    teacher.is_admin = not teacher.is_admin

    db.session.commit()

    if teacher.is_admin:
        flash(f"{teacher.fullname} is now an admin.", "success")
    else:
        flash(f"Admin rights removed from {teacher.fullname}.", "warning")

    return redirect(url_for("admin.manage_accounts"))


@admin_bp.route("/teacher")
@login_required
def teacher_dash():
    lessons = (
        db.session.query(Lesson)
        .join(Lesson.class_)
        .join(Lesson.subject)
        .filter(Lesson.teacher_id == current_user.id)
        .all()
    )

    grouped = {}
    for lesson in lessons:
        class_obj = lesson.class_
        if not class_obj:
            continue
        entry = grouped.get(lesson.class_id)
        if not entry:
            entry = {
                "class_id": lesson.class_id,
                "branch_id": lesson.branch_id,
                "grade_form": live_class_name(class_obj.grade_form)
                or class_obj.grade_form,
                "streams": [],
                "subjects": [],
                "covers_whole_class": False,
            }
            grouped[lesson.class_id] = entry

        stream = (lesson.stream or "").strip()
        if stream:
            if stream not in entry["streams"]:
                entry["streams"].append(stream)
        else:
            entry["covers_whole_class"] = True
            class_streams = class_obj.streams or []
            if isinstance(class_streams, list):
                for item in class_streams:
                    name = (item or "").strip()
                    if name and name not in entry["streams"]:
                        entry["streams"].append(name)

        subject_name = lesson.subject.name if lesson.subject else ""
        if subject_name and subject_name not in entry["subjects"]:
            entry["subjects"].append(subject_name)

    classes_info = []
    for entry in grouped.values():
        query = Student.query.filter_by(
            branch_id=entry["branch_id"],
            class_id=entry["class_id"],
        )
        if entry["streams"] and not entry["covers_whole_class"]:
            query = query.filter(Student.stream.in_(entry["streams"]))
        classes_info.append(
            {
                "grade_form": entry["grade_form"],
                "streams": entry["streams"],
                "subjects": sorted(entry["subjects"], key=str.lower),
                "num_students": query.count(),
            }
        )

    sorted_keys = sort_grade_list(
        [(index, row["grade_form"]) for index, row in enumerate(classes_info)],
        dedupe=False,
    )
    classes_info = [classes_info[index] for index, _ in sorted_keys]

    branch = current_user.branch

    return render_template(
        "staff_templates/teacher.html",
        lessons=classes_info,
        branch=branch,
        teacher=current_user,
        class_performance=dashboard_class_performance(current_user),
    )


@admin_bp.route("/messages")
@login_required
@admin_required
def messages():
    return render_template("admin_templates/messages.html")
