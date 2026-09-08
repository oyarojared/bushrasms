from flask import current_app
from flask_login import current_user
from sqlalchemy import false
from sqlalchemy.exc import SQLAlchemyError

from ....modals.branches_db import Branch
from ....modals.staff_db import Teacher


def _user(user=None):
    return current_user if user is None else user


def is_system_admin(user=None):
    person = _user(user)
    return bool(getattr(person, "is_system_admin", False))


def is_super_admin_role(user=None):
    """True super admin, including a system admin who also carries that flag."""
    person = _user(user)
    return bool(getattr(person, "is_super_admin", False) or is_system_admin(person))


def can_teach(user=None):
    person = _user(user)
    return not (
        is_system_admin(person) or getattr(person, "is_super_admin", False)
    )


def accessible_branch_ids(user=None):
    """None = every school (system admin). [] = no schools."""
    person = _user(user)
    if is_system_admin(person):
        return None
    if getattr(person, "is_super_admin", False):
        rows = getattr(person, "school_access", None) or []
        try:
            return [int(row.branch_id) for row in rows]
        except TypeError:
            return []
    branch_id = getattr(person, "branch_id", None)
    try:
        return [int(branch_id)] if branch_id is not None else []
    except (TypeError, ValueError):
        return []


def user_can_select_branch(user=None):
    """System admins and super admins pick among schools they may see."""
    person = _user(user)
    return bool(
        getattr(person, "is_authenticated", False)
        and is_super_admin_role(person)
    )


def locked_branch_id(user=None):
    """School-scoped users are bound to this branch. Platform roles are not locked."""
    person = _user(user)
    if user_can_select_branch(person):
        return None
    if not getattr(person, "is_authenticated", False):
        return None
    return getattr(person, "branch_id", None)


def apply_locked_branch(*fields):
    """Force school-scoped users onto their own branch in WTForms fields."""
    branch_id = locked_branch_id()
    if branch_id is None:
        return
    value = str(branch_id)
    for field in fields:
        if field is not None:
            field.data = value


def get_accessible_branches_query(user=None):
    person = _user(user)
    query = Branch.query
    ids = accessible_branch_ids(person)
    if ids is None:
        return query
    if not ids:
        return query.filter(false())
    return query.filter(Branch.id.in_(ids))


def load_branch_choices(user=None):
    try:
        query = (
            get_accessible_branches_query(user)
            .with_entities(Branch.id, Branch.branch_name)
            .order_by(Branch.created_at.desc())
        )
        rows = query.all()
        options = [(str(b.id), b.branch_name) for b in rows]

        if locked_branch_id(user):
            return options or [("", "--- No Branches Available ---")]

        return [("", "--- Select a Branch ---")] + options

    except SQLAlchemyError as e:
        current_app.logger.error(f"[DB ERROR] load_branch_choices: {e}")
        return [("", "--- No Branches Available ---")]


def user_can_access_branch(branch_id, user=None):
    """True when the logged-in user may see this school's data."""
    try:
        branch_id = int(branch_id)
    except (TypeError, ValueError):
        return False
    return (
        get_accessible_branches_query(user)
        .filter(Branch.id == branch_id)
        .first()
        is not None
    )


def teachable_teachers_for_branch(branch_id):
    return (
        Teacher.query.filter_by(branch_id=branch_id)
        .filter(Teacher.is_super_admin.is_(False))
        .filter(Teacher.is_system_admin.is_(False))
        .order_by(Teacher.fullname.asc())
        .all()
    )
