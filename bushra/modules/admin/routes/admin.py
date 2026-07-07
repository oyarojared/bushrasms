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
    branches_list = []
    for b in branches_meta:
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

    # allow BOTH admin and super admin
    if current_user.is_admin or current_user.is_super_admin:

        return render_template(
            "admin_templates/accounts.html",
            teachers=teachers,
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

    classes_info = []
    for lesson in lessons:
        # Count students only in the stream this teacher is teaching
        if lesson.stream:
            num_students = (
                db.session.query(Student)
                .filter(
                    Student.class_id == lesson.class_id,
                    Student.branch_id == lesson.branch_id,
                    Student.stream == lesson.stream
                )
                .count()
            )
        else:
            num_students = len(lesson.class_.students)

        classes_info.append({
            "grade_form": lesson.class_.grade_form,
            "streams": [lesson.stream] if lesson.stream else lesson.class_.streams,
            "subject_name": lesson.subject.name,
            "num_students": num_students
        })

    branch = current_user.branch

    return render_template(
        "staff_templates/teacher.html",
        lessons=classes_info,
        branch=branch,
        teacher=current_user
    )
