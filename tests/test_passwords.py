from types import SimpleNamespace

import pytest
from werkzeug.security import check_password_hash

from ..bushra import create_app
from ..bushra import db as _db
from ..bushra.config import DevelopmentConfig
from ..bushra.modals.branches_db import Branch
from ..bushra.modals.staff_db import Teacher
from ..bushra.modules.admin.utils.teacher_utils import (
    can_reset_teacher_password,
    hash_staff_password,
    last_four_phone_digits,
)


@pytest.fixture()
def app(tmp_path, monkeypatch):
    uri = "sqlite:///" + str(tmp_path / "passwords.db").replace("\\", "/")
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


@pytest.fixture()
def client(app):
    return app.test_client()


def _branch(db, name="Test School", code="TS001"):
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
    phone="0712345678",
    username=None,
    password="secret12",
    is_admin=False,
    is_super_admin=False,
    fullname="Test Teacher",
):
    teacher = Teacher(
        branch_id=branch.id,
        employer="TSC",
        fullname=fullname,
        gender="M",
        title="Mr.",
        phone=phone,
        username=username or f"user{phone[-4:]}",
        password_hash=hash_staff_password(password),
        is_admin=is_admin,
        is_super_admin=is_super_admin,
    )
    db.session.add(teacher)
    db.session.commit()
    return teacher


def _login(client, teacher):
    with client.session_transaction() as sess:
        sess["_user_id"] = str(teacher.id)
        sess["_fresh"] = True


def test_last_four_phone_digits():
    assert last_four_phone_digits("0712345678") == "5678"
    assert last_four_phone_digits("+254712345678") == "5678"
    assert last_four_phone_digits("123") is None
    assert last_four_phone_digits(None) is None
    assert last_four_phone_digits(712345678) is None


def test_hash_staff_password_verifies():
    hashed = hash_staff_password("secret12")
    assert hashed.startswith("pbkdf2:sha256")
    assert check_password_hash(hashed, "secret12")


def test_can_reset_teacher_password_rules():
    school_admin = SimpleNamespace(
        id=1, is_admin=True, is_super_admin=False, branch_id=10
    )
    other_admin = SimpleNamespace(
        id=2, is_admin=True, is_super_admin=False, branch_id=20
    )
    teacher_same = SimpleNamespace(
        id=3, is_admin=False, is_super_admin=False, branch_id=10
    )
    teacher_other = SimpleNamespace(
        id=4, is_admin=False, is_super_admin=False, branch_id=20
    )
    super_admin = SimpleNamespace(
        id=5, is_admin=True, is_super_admin=True, branch_id=10
    )
    plain_teacher = SimpleNamespace(
        id=6, is_admin=False, is_super_admin=False, branch_id=10
    )

    assert can_reset_teacher_password(school_admin, teacher_same) is True
    assert can_reset_teacher_password(school_admin, teacher_other) is False
    assert can_reset_teacher_password(school_admin, super_admin) is False
    assert can_reset_teacher_password(school_admin, school_admin) is False
    assert can_reset_teacher_password(plain_teacher, teacher_same) is False
    assert can_reset_teacher_password(super_admin, teacher_other) is True
    assert can_reset_teacher_password(super_admin, other_admin) is True
    assert can_reset_teacher_password(super_admin, super_admin) is False


def test_change_password_page_renders_for_admin(client, db):
    branch = _branch(db, code="AD001")
    admin = _teacher(
        db,
        branch,
        phone="0700000099",
        username="admin0099",
        password="oldpass",
        is_admin=True,
    )
    _login(client, admin)

    response = client.get("/admin/change_password")
    assert response.status_code == 200
    assert b"Current password" in response.data
    assert b"studentSearchInput" in response.data


def test_change_password_success(client, db):
    branch = _branch(db)
    teacher = _teacher(db, branch, password="oldpass")
    _login(client, teacher)

    response = client.post(
        "/admin/change_password",
        data={
            "current_password": "oldpass",
            "new_password": "newpass",
            "confirm_password": "newpass",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Password updated" in response.data

    db.session.refresh(teacher)
    assert check_password_hash(teacher.password_hash, "newpass")


def test_change_password_rejects_wrong_current(client, db):
    branch = _branch(db)
    teacher = _teacher(db, branch, password="oldpass")
    original_hash = teacher.password_hash
    _login(client, teacher)

    response = client.post(
        "/admin/change_password",
        data={
            "current_password": "wrongpass",
            "new_password": "newpass",
            "confirm_password": "newpass",
        },
    )
    assert response.status_code == 200
    assert b"Current password is incorrect" in response.data
    db.session.refresh(teacher)
    assert teacher.password_hash == original_hash


def test_change_password_rejects_mismatch(client, db):
    branch = _branch(db)
    teacher = _teacher(db, branch, password="oldpass")
    _login(client, teacher)

    response = client.post(
        "/admin/change_password",
        data={
            "current_password": "oldpass",
            "new_password": "newpass",
            "confirm_password": "other12",
        },
    )
    assert response.status_code == 200
    assert b"New passwords must match" in response.data


def test_admin_reset_password_sets_last_four_digits(client, db):
    branch = _branch(db)
    admin = _teacher(
        db,
        branch,
        phone="0700000001",
        username="admin0001",
        password="oldpass",
        is_admin=True,
        fullname="School Admin",
    )
    teacher = _teacher(
        db,
        branch,
        phone="0712345678",
        username="teacher5678",
        password="oldpass",
        fullname="Class Teacher",
    )
    _login(client, admin)

    response = client.post(
        f"/admin/reset_teacher_password/{teacher.id}",
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Temporary password: 5678" in response.data

    db.session.refresh(teacher)
    assert check_password_hash(teacher.password_hash, "5678")


def test_teacher_cannot_reset_another_password(client, db):
    branch = _branch(db)
    teacher = _teacher(
        db, branch, phone="0700000002", username="teacher0002", password="oldpass"
    )
    other = _teacher(
        db, branch, phone="0700000003", username="teacher0003", password="oldpass"
    )
    original_hash = other.password_hash
    _login(client, teacher)

    response = client.post(
        f"/admin/reset_teacher_password/{other.id}",
        follow_redirects=False,
    )
    assert response.status_code == 302
    db.session.refresh(other)
    assert other.password_hash == original_hash


def test_school_admin_cannot_reset_other_branch(client, db):
    branch_a = _branch(db, name="School A", code="SA001")
    branch_b = _branch(db, name="School B", code="SB001")
    admin = _teacher(
        db,
        branch_a,
        phone="0700000011",
        username="admin0011",
        password="oldpass",
        is_admin=True,
    )
    other = _teacher(
        db,
        branch_b,
        phone="0700000012",
        username="teacher0012",
        password="oldpass",
    )
    original_hash = other.password_hash
    _login(client, admin)

    response = client.post(
        f"/admin/reset_teacher_password/{other.id}",
        follow_redirects=True,
    )
    assert b"You cannot reset this account" in response.data
    db.session.refresh(other)
    assert other.password_hash == original_hash


def test_admin_cannot_reset_own_password(client, db):
    branch = _branch(db)
    admin = _teacher(
        db,
        branch,
        phone="0700000021",
        username="admin0021",
        password="oldpass",
        is_admin=True,
    )
    original_hash = admin.password_hash
    _login(client, admin)

    response = client.post(
        f"/admin/reset_teacher_password/{admin.id}",
        follow_redirects=True,
    )
    assert b"You cannot reset this account" in response.data
    db.session.refresh(admin)
    assert admin.password_hash == original_hash
