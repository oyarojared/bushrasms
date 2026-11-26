import os
import tempfile

import pytest

from ..bushra import create_app
from ..bushra import db as _db
from ..bushra.config import DevelopmentConfig
from ..bushra.modals.branches_db import Branch, BranchClasses
from ..bushra.modals.staff_db import Teacher
from ..bushra.modals.students_db import Student


class TestConfig(DevelopmentConfig):
    TESTING = True
    WTF_CSRF_ENABLED = False
    PROMOTION_ENABLED = True


@pytest.fixture()
def app():
    handle, path = tempfile.mkstemp(suffix=".sqlite")
    os.close(handle)
    TestConfig.SQLALCHEMY_DATABASE_URI = "sqlite:///" + path
    app = create_app(TestConfig)
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.engine.dispose()
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def test_student(db):
    # Create a branch and class (required foreign keys)
    branch = Branch(
        branch_name="Primary",
        school_code="PR001",
        branch_manager="John Doe",
        branch_level="primary",
        branch_head="Mrs Smith",
        school_gender="Co-ed",
        school_type="Day",
        email="primary@example.com",
    )
    db.session.add(branch)
    db.session.commit()

    cls = BranchClasses(
        branch_id=branch.id, grade_form="Grade 1", streams=["A", "B"], class_year="2025"
    )
    db.session.add(cls)
    db.session.commit()

    # Create student
    student = Student(
        fullname="Test Student",
        gender="Male",
        admission_number=4,
        branch_id=branch.id,
        class_id=cls.id,
        stream="A",
    )
    db.session.add(student)
    db.session.commit()

    yield student

    # Cleanup after test
    db.session.delete(student)
    db.session.delete(cls)
    db.session.delete(branch)
    db.session.commit()

@pytest.fixture
def sample_teacher(app):
    teacher = Teacher(
        fullname="Test Teacher",
        phone="0712345678",
        email="test@example.com",
        tsc_no="TSC001",
        id_no="12345678"
    )
    
    db.session.add(teacher)
    db.session.commit()
    return teacher

@pytest.fixture
def db(app):
    """Return the database instance for tests."""
    return _db


@pytest.fixture()
def client(app):
    return app.test_client()


# @pytest.fixture()
# def runner(app):
#     return app.test_cli_runner()
