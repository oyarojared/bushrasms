from flask import flash, render_template, request, url_for, redirect
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from ....modals.branches_db import Branch, BranchClasses, db
from ....modals.staff_db import ClassTeacher, SuperAdminBranch, Teacher
from ....modals.students_db import Student
from .. import admin_bp

from flask_login import current_user, login_required
from sqlalchemy.orm import aliased

from ..utils.route_protect import admin_required
from ..utils.class_teacher import dashboard_class_performance
from ..utils.teacher_utils import can_reset_teacher_password
from ..utils.branch_utils import (
    accessible_branch_ids,
    get_accessible_branches_query,
    is_system_admin,
    user_can_access_branch,
    user_can_select_branch,
)
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

    accessible_ids = {b.id for b in get_accessible_branches_query().all()}
    total_teachers = sum(
        teacher_count_map.get(branch_id, 0) for branch_id in accessible_ids
    )

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
        if b.id not in accessible_ids:
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

    total_students = sum(b["population"] for b in branches_list)
    show_all_accessible = user_can_select_branch()
    single_branch = []
    if not show_all_accessible:
        for b in branches_list:
            if b["id"] == current_user.branch_id:
                single_branch.append(b)
        total_students = single_branch[0]["population"] if single_branch else 0

    # ==========================================================
    # 6. RENDER
    # ==========================================================
    return render_template(
        "admin_templates/admin_dash.html",
        branches=branches_list if show_all_accessible else single_branch,
        tot_students=total_students,
        total_teachers=total_teachers, 
    )


def _clear_teaching_duties(teacher):
    Lesson.query.filter_by(teacher_id=teacher.id).delete(synchronize_session=False)
    ClassTeacher.query.filter_by(teacher_id=teacher.id).update(
        {ClassTeacher.teacher_id: None}, synchronize_session=False
    )


def _accounts_teacher_query():
    query = Teacher.query
    if is_system_admin():
        return query
    ids = accessible_branch_ids()
    if not ids:
        return query.filter(Teacher.id == -1)
    return query.filter(Teacher.branch_id.in_(ids))


def _can_toggle_admin(actor, target):
    if target.id == actor.id:
        return False
    if is_system_admin(target) or getattr(target, "is_super_admin", False):
        return False
    if is_system_admin(actor):
        return True
    if getattr(actor, "is_super_admin", False):
        return user_can_access_branch(target.branch_id, actor)
    if getattr(actor, "is_admin", False):
        return actor.branch_id == target.branch_id
    return False


@admin_bp.route("/manage_accounts")
@login_required
@admin_required
def manage_accounts():
    if not (current_user.is_admin or current_user.is_super_admin or is_system_admin()):
        flash("Access denied: Admin or Super Admin only", "danger")
        return redirect(url_for("admin.admin_dash"))

    teachers = _accounts_teacher_query().order_by(Teacher.fullname.asc()).all()
    resettable_ids = {
        teacher.id
        for teacher in teachers
        if can_reset_teacher_password(current_user, teacher)
    }
    assigned_schools = {
        teacher.id: {row.branch_id for row in teacher.school_access}
        for teacher in teachers
        if teacher.is_super_admin and not teacher.is_system_admin
    }
    all_branches = []
    if is_system_admin():
        all_branches = Branch.query.order_by(Branch.branch_name.asc()).all()

    return render_template(
        "admin_templates/accounts.html",
        teachers=teachers,
        resettable_ids=resettable_ids,
        all_branches=all_branches,
        assigned_schools=assigned_schools,
    )


@admin_bp.route("/toggle-super-admin/<int:teacher_id>", methods=["POST"])
@login_required
@admin_required
def toggle_super_admin(teacher_id):
    if not is_system_admin():
        flash("Only a system admin can change super admin status.", "danger")
        return redirect(url_for("admin.manage_accounts"))

    teacher = Teacher.query.get_or_404(teacher_id)

    if teacher.id == current_user.id or teacher.is_system_admin:
        flash("You cannot change this account's super admin status.", "warning")
        return redirect(url_for("admin.manage_accounts"))

    teacher.is_super_admin = not teacher.is_super_admin
    if teacher.is_super_admin:
        teacher.is_admin = True
        _clear_teaching_duties(teacher)
        flash(
            f"{teacher.fullname} is now a super admin. Assign schools before they can open any.",
            "success",
        )
    else:
        SuperAdminBranch.query.filter_by(teacher_id=teacher.id).delete(
            synchronize_session=False
        )
        flash(f"Super admin rights removed from {teacher.fullname}.", "warning")

    db.session.commit()
    return redirect(url_for("admin.manage_accounts"))


@admin_bp.route("/teachers/<int:teacher_id>/schools", methods=["POST"])
@login_required
@admin_required
def assign_super_admin_schools(teacher_id):
    if not is_system_admin():
        flash("Only a system admin can assign schools to a super admin.", "danger")
        return redirect(url_for("admin.manage_accounts"))

    teacher = Teacher.query.get_or_404(teacher_id)
    if teacher.is_system_admin or not teacher.is_super_admin:
        flash("Schools can only be assigned to a super admin.", "warning")
        return redirect(url_for("admin.manage_accounts"))

    selected = set()
    for raw in request.form.getlist("branch_ids"):
        try:
            selected.add(int(raw))
        except (TypeError, ValueError):
            continue

    valid_ids = {
        branch.id
        for branch in Branch.query.filter(Branch.id.in_(selected or [-1])).all()
    }
    SuperAdminBranch.query.filter_by(teacher_id=teacher.id).delete(
        synchronize_session=False
    )
    for branch_id in sorted(valid_ids):
        db.session.add(SuperAdminBranch(teacher_id=teacher.id, branch_id=branch_id))
    db.session.commit()

    if valid_ids:
        flash(f"Updated school access for {teacher.fullname}.", "success")
    else:
        flash(
            f"{teacher.fullname} has no schools assigned and cannot see school data.",
            "warning",
        )
    return redirect(url_for("admin.manage_accounts"))


@admin_bp.route("/teachers/<int:teacher_id>/toggle-admin", methods=["POST"])
@admin_required
def toggle_admin(teacher_id):
    teacher = Teacher.query.get_or_404(teacher_id)

    if not _can_toggle_admin(current_user, teacher):
        flash("You cannot change admin rights for this user.", "danger")
        return redirect(url_for("admin.manage_accounts"))

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
