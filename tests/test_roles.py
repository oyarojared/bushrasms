from types import SimpleNamespace

import pytest

from ..bushra import create_app
from ..bushra import db as _db
from ..bushra.config import DevelopmentConfig
from ..bushra.modals.branches_db import Branch
from ..bushra.modals.staff_db import SuperAdminBranch, Teacher
from ..bushra.modules.admin.utils.branch_utils import (
    accessible_branch_ids,
    can_teach,
    get_accessible_branches_query,
    is_system_admin,
    teachable_teachers_for_branch,
    user_can_access_branch,
)
from ..bushra.modules.admin.utils.teacher_utils import (
    can_reset_teacher_password,
    hash_staff_password,
)


@pytest.fixture()
def app(tmp_path, monkeypatch):
    uri = "sqlite:///" + str(tmp_path / "roles.db").replace("\\", "/")
    monkeypatch.setattr(DevelopmentConfig, "SQLALCHEMY_DATABASE_URI", uri)
    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def db(app):
    return _db


def _branch(db, name, code):
    branch = Branch(
        branch_name=name,
        school_code=code,
        branch_manager="Manager",
        branch_level="secondary",
        school_gender="Co-ed",
        school_type="Day",
        email=f"{code.lower()}@example.com",
    )
    db.session.add(branch)
    db.session.flush()
    return branch


def _teacher(
    db,
    branch,
    phone,
    *,
    is_admin=False,
    is_super_admin=False,
    is_system_admin=False,
    fullname="Staff Member",
):
    teacher = Teacher(
        branch_id=branch.id,
        employer="TSC",
        fullname=fullname,
        gender="M",
        title="Mr.",
        phone=phone,
        username=f"user{phone[-4:]}",
        password_hash=hash_staff_password("secret12"),
        is_admin=is_admin,
        is_super_admin=is_super_admin,
        is_system_admin=is_system_admin,
    )
    db.session.add(teacher)
    db.session.flush()
    return teacher


def test_system_admin_sees_every_school(app, db):
    first = _branch(db, "Alpha", "AL001")
    second = _branch(db, "Beta", "BE001")
    owner = _teacher(
        db,
        first,
        "0700000001",
        is_admin=True,
        is_super_admin=True,
        is_system_admin=True,
    )
    db.session.commit()

    with app.test_request_context():
        from flask_login import login_user

        login_user(owner)
        ids = {branch.id for branch in get_accessible_branches_query().all()}
        assert ids == {first.id, second.id}
        assert user_can_access_branch(second.id) is True
        assert can_teach(owner) is False


def test_super_admin_with_no_schools_sees_nothing(app, db):
    first = _branch(db, "Alpha", "AL002")
    _branch(db, "Beta", "BE002")
    super_admin = _teacher(
        db,
        first,
        "0700000002",
        is_admin=True,
        is_super_admin=True,
    )
    db.session.commit()

    with app.test_request_context():
        from flask_login import login_user

        login_user(super_admin)
        assert accessible_branch_ids() == []
        assert get_accessible_branches_query().all() == []
        assert user_can_access_branch(first.id) is False
        assert can_teach(super_admin) is False


def test_super_admin_only_sees_assigned_schools(app, db):
    first = _branch(db, "Alpha", "AL003")
    second = _branch(db, "Beta", "BE003")
    super_admin = _teacher(
        db,
        first,
        "0700000003",
        is_admin=True,
        is_super_admin=True,
    )
    db.session.add(SuperAdminBranch(teacher_id=super_admin.id, branch_id=second.id))
    db.session.commit()

    with app.test_request_context():
        from flask_login import login_user

        login_user(super_admin)
        ids = {branch.id for branch in get_accessible_branches_query().all()}
        assert ids == {second.id}
        assert user_can_access_branch(first.id) is False
        assert user_can_access_branch(second.id) is True


def test_school_admin_stays_on_own_school(app, db):
    first = _branch(db, "Alpha", "AL004")
    second = _branch(db, "Beta", "BE004")
    admin = _teacher(db, first, "0700000004", is_admin=True)
    db.session.commit()

    with app.test_request_context():
        from flask_login import login_user

        login_user(admin)
        ids = {branch.id for branch in get_accessible_branches_query().all()}
        assert ids == {first.id}
        assert user_can_access_branch(second.id) is False
        assert can_teach(admin) is True


def test_super_admins_are_not_listed_as_teachers(app, db):
    branch = _branch(db, "Alpha", "AL005")
    teacher = _teacher(db, branch, "0700000005", fullname="Class Teacher")
    _teacher(
        db,
        branch,
        "0700000006",
        is_admin=True,
        is_super_admin=True,
        fullname="Super Person",
    )
    db.session.commit()

    names = [row.fullname for row in teachable_teachers_for_branch(branch.id)]
    assert "Class Teacher" in names
    assert "Super Person" not in names


def test_password_reset_scope_for_new_roles():
    system_admin = SimpleNamespace(
        id=1, is_admin=True, is_super_admin=True, is_system_admin=True, branch_id=10
    )
    super_admin = SimpleNamespace(
        id=2,
        is_admin=True,
        is_super_admin=True,
        is_system_admin=False,
        branch_id=10,
        school_access=[SimpleNamespace(branch_id=20)],
    )
    empty_super = SimpleNamespace(
        id=3,
        is_admin=True,
        is_super_admin=True,
        is_system_admin=False,
        branch_id=10,
        school_access=[],
    )
    teacher_assigned = SimpleNamespace(
        id=4, is_admin=False, is_super_admin=False, is_system_admin=False, branch_id=20
    )
    teacher_other = SimpleNamespace(
        id=5, is_admin=False, is_super_admin=False, is_system_admin=False, branch_id=30
    )

    assert is_system_admin(system_admin) is True
    assert can_reset_teacher_password(system_admin, teacher_other) is True
    assert can_reset_teacher_password(super_admin, teacher_assigned) is True
    assert can_reset_teacher_password(super_admin, teacher_other) is False
    assert can_reset_teacher_password(empty_super, teacher_assigned) is False
    assert can_reset_teacher_password(super_admin, system_admin) is False


def _school_form(name, code, manager="Updated Manager"):
    return {
        "branch_name": name,
        "school_code": code,
        "branch_manager": manager,
        "branch_level": "Secondary",
        "school_gender": "Mixed",
        "school_type": "Day School",
    }


def _login(client, teacher_id):
    with client.session_transaction() as sess:
        sess["_user_id"] = str(teacher_id)
        sess["_fresh"] = True


def test_super_admin_cannot_add_school(app, db):
    branch = _branch(db, "Alpha", "AL010")
    super_admin = _teacher(
        db, branch, "0700000010", is_admin=True, is_super_admin=True
    )
    db.session.add(SuperAdminBranch(teacher_id=super_admin.id, branch_id=branch.id))
    db.session.commit()

    client = app.test_client()
    _login(client, super_admin.id)
    before = Branch.query.count()
    response = client.post(
        "/admin/add_school",
        data=_school_form("Rogue School", "RG001"),
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert Branch.query.count() == before
    assert Branch.query.filter_by(branch_name="Rogue School").first() is None


def test_system_admin_can_add_school(app, db):
    home = _branch(db, "Alpha", "AL011")
    owner = _teacher(
        db,
        home,
        "0700000011",
        is_admin=True,
        is_super_admin=True,
        is_system_admin=True,
    )
    db.session.commit()

    client = app.test_client()
    _login(client, owner.id)
    response = client.post(
        "/admin/add_school",
        data=_school_form("New Campus", "NC001", "Campus Manager"),
        follow_redirects=False,
    )
    assert response.status_code == 302
    created = Branch.query.filter_by(branch_name="New Campus").first()
    assert created is not None
    assert created.branch_manager == "Campus Manager"


def test_super_admin_can_edit_school_but_not_rename(app, db):
    branch = _branch(db, "Alpha", "AL012")
    super_admin = _teacher(
        db, branch, "0700000012", is_admin=True, is_super_admin=True
    )
    db.session.add(SuperAdminBranch(teacher_id=super_admin.id, branch_id=branch.id))
    db.session.commit()

    client = app.test_client()
    _login(client, super_admin.id)
    response = client.post(
        f"/admin/update_branch/{branch.id}",
        data=_school_form("Renamed Alpha", "AL012", "New Manager"),
        follow_redirects=False,
    )
    assert response.status_code == 302
    db.session.refresh(branch)
    assert branch.branch_name == "Alpha"
    assert branch.branch_manager == "New Manager"
