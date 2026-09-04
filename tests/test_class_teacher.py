import pytest

from ..bushra import create_app
from ..bushra import db as _db
from ..bushra.config import DevelopmentConfig
from ..bushra.modals.branches_db import Branch, BranchClasses
from ..bushra.modals.staff_db import ClassTeacher, Teacher
from ..bushra.modules.admin.utils.class_teacher import (
    find_class_teacher_assignment,
    upsert_class_teacher_assignment,
)
from ..bushra.modules.admin.utils.teacher_utils import hash_staff_password


@pytest.fixture()
def app(tmp_path, monkeypatch):
    uri = "sqlite:///" + str(tmp_path / "class_teacher.db").replace("\\", "/")
    monkeypatch.setattr(DevelopmentConfig, "SQLALCHEMY_DATABASE_URI", uri)
    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
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


def _class(db, branch, streams=None):
    cls = BranchClasses(
        branch_id=branch.id,
        grade_form="Form 1",
        streams=streams or ["East", "West"],
        class_year="2026",
    )
    db.session.add(cls)
    db.session.flush()
    return cls


def _teacher(db, branch, phone, fullname, is_admin=False):
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
    )
    db.session.add(teacher)
    db.session.flush()
    return teacher


def test_changing_class_teacher_updates_existing_class_level_row(app, db):
    branch = _branch(db)
    cls = _class(db, branch)
    old = _teacher(db, branch, "0711111111", "Old Teacher")
    new = _teacher(db, branch, "0722222222", "New Teacher")
    db.session.add(
        ClassTeacher(
            branch_id=branch.id,
            class_id=cls.id,
            stream=None,
            teacher_id=old.id,
        )
    )
    db.session.commit()

    upsert_class_teacher_assignment(branch.id, cls.id, "East", new)
    db.session.commit()

    rows = ClassTeacher.query.filter_by(class_id=cls.id).all()
    assert len(rows) == 1
    assert rows[0].teacher_id == new.id
    assert rows[0].stream == "East"


def test_changing_class_teacher_updates_empty_string_stream_row(app, db):
    branch = _branch(db)
    cls = _class(db, branch, streams=[])
    old = _teacher(db, branch, "0711111113", "Old Teacher")
    new = _teacher(db, branch, "0722222224", "New Teacher")
    db.session.add(
        ClassTeacher(
            branch_id=branch.id,
            class_id=cls.id,
            stream="",
            teacher_id=old.id,
        )
    )
    db.session.commit()

    upsert_class_teacher_assignment(branch.id, cls.id, None, new)
    db.session.commit()

    rows = ClassTeacher.query.filter_by(class_id=cls.id).all()
    assert len(rows) == 1
    assert rows[0].teacher_id == new.id


def test_changing_class_teacher_collapses_duplicate_rows(app, db):
    branch = _branch(db)
    cls = _class(db, branch)
    old = _teacher(db, branch, "0711111115", "Old Teacher")
    new = _teacher(db, branch, "0722222226", "New Teacher")
    db.session.add_all(
        [
            ClassTeacher(
                branch_id=branch.id,
                class_id=cls.id,
                stream=None,
                teacher_id=old.id,
            ),
            ClassTeacher(
                branch_id=branch.id,
                class_id=cls.id,
                stream="East",
                teacher_id=old.id,
            ),
        ]
    )
    db.session.commit()

    upsert_class_teacher_assignment(branch.id, cls.id, "East", new)
    db.session.commit()

    rows = ClassTeacher.query.filter_by(class_id=cls.id).all()
    assert len(rows) == 1
    assert rows[0].teacher_id == new.id
    assert rows[0].stream == "East"
    found = find_class_teacher_assignment(branch.id, cls.id, "East")
    assert found.teacher_id == new.id


def test_save_class_teacher_endpoint_replaces_old_teacher(app, db, client):
    branch = _branch(db)
    cls = _class(db, branch)
    admin = _teacher(db, branch, "0700000001", "Admin Teacher", is_admin=True)
    old = _teacher(db, branch, "0711111117", "Old Teacher")
    new = _teacher(db, branch, "0722222228", "New Teacher")
    db.session.add(
        ClassTeacher(
            branch_id=branch.id,
            class_id=cls.id,
            stream=None,
            teacher_id=old.id,
        )
    )
    db.session.commit()

    with client.session_transaction() as sess:
        sess["_user_id"] = str(admin.id)
        sess["_fresh"] = True

    response = client.post(
        "/admin/api/save-class-teacher",
        json={
            "branch_id": branch.id,
            "class_id": cls.id,
            "stream": "East",
            "teacher_id": new.id,
        },
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True

    rows = ClassTeacher.query.filter_by(class_id=cls.id).all()
    assert len(rows) == 1
    assert rows[0].teacher_id == new.id

    context = client.get(
        f"/admin/api/class-teacher-context?branch_id={branch.id}&class_id={cls.id}&stream=East"
    )
    assert context.status_code == 200
    assert context.get_json()["current_teacher"]["id"] == new.id
