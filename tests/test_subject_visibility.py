from types import SimpleNamespace

import pytest

from ..bushra import create_app
from ..bushra import db as _db
from ..bushra.config import DevelopmentConfig
from ..bushra.modals.subjects_db import SubjectEligibility
from ..bushra.modules.admin.services.grades import (
    get_branch_grade_names,
    load_grades,
)
from ..bushra.modules.admin.services.subs import (
    apply_visible_grades,
    get_subjects,
    update_subject_service,
)
from .test_subject_allocation import _make_branch, _make_class, _make_subject


@pytest.fixture
def db(tmp_path, monkeypatch):
    uri = "sqlite:///" + str(tmp_path / "subjects.db").replace("\\", "/")
    monkeypatch.setattr(DevelopmentConfig, "SQLALCHEMY_DATABASE_URI", uri)
    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.remove()
        _db.drop_all()


def _names(subjects):
    return sorted(subject.name for subject in subjects)


def _form(**overrides):
    values = {
        "name": "English",
        "code": "101",
        "category": "Languages",
        "is_examinable": True,
        "is_compulsory": False,
    }
    values.update(overrides)
    return SimpleNamespace(
        **{key: SimpleNamespace(data=value) for key, value in values.items()}
    )


def test_school_catalog_hides_subjects_for_other_levels(db):
    primary = _make_branch(db, "Primary School", "PR01")
    secondary = _make_branch(db, "High School", "HS01")
    _make_class(db, primary, "Grade 4")
    _make_class(db, secondary, "Form 2")

    _make_subject(db, "Environmental Activities", "ENV", ["Grade 4"])
    _make_subject(db, "Physics", "PHY", ["Form 2"])
    english = _make_subject(db, "English", "ENG", ["Grade 4", "Form 2"])
    db.session.commit()

    primary_subjects, error = get_subjects(
        grade_names=get_branch_grade_names(primary.id)
    )
    secondary_subjects, error2 = get_subjects(
        grade_names=get_branch_grade_names(secondary.id)
    )
    all_subjects, error3 = get_subjects()

    assert error is None and error2 is None and error3 is None
    assert _names(primary_subjects) == ["English", "Environmental Activities"]
    assert _names(secondary_subjects) == ["English", "Physics"]
    assert _names(all_subjects) == [
        "English",
        "Environmental Activities",
        "Physics",
    ]

    apply_visible_grades(
        secondary_subjects, get_branch_grade_names(secondary.id)
    )
    english_row = next(s for s in secondary_subjects if s.id == english.id)
    assert english_row.visible_grades == ["Form 2"]


def test_mixed_school_sees_both_levels(db):
    mixed = _make_branch(db, "Mixed School", "MX01")
    _make_class(db, mixed, "Grade 6")
    _make_class(db, mixed, "Form 1")
    _make_subject(db, "Creative Arts", "ART", ["Grade 6"])
    _make_subject(db, "Chemistry", "CHE", ["Form 1"])
    db.session.commit()

    subjects, error = get_subjects(grade_names=get_branch_grade_names(mixed.id))
    assert error is None
    assert _names(subjects) == ["Chemistry", "Creative Arts"]


def test_school_with_no_classes_sees_no_subjects(db):
    branch = _make_branch(db, "Empty School", "EM01")
    _make_subject(db, "Physics", "PHY", ["Form 2"])
    db.session.commit()

    subjects, error = get_subjects(grade_names=get_branch_grade_names(branch.id))
    assert error is None
    assert subjects == []


def test_load_grades_can_be_limited_to_one_school(db):
    primary = _make_branch(db, "Primary School", "PR02")
    secondary = _make_branch(db, "High School", "HS02")
    _make_class(db, primary, "Grade 3")
    _make_class(db, secondary, "Form 4")
    db.session.commit()

    primary_grades = [name for value, name in load_grades(branch_id=primary.id)[1:]]
    secondary_grades = [
        name for value, name in load_grades(branch_id=secondary.id)[1:]
    ]
    all_grades = [name for value, name in load_grades()[1:]]

    assert primary_grades == ["Grade 3"]
    assert secondary_grades == ["Form 4"]
    assert "Grade 3" in all_grades
    assert "Form 4" in all_grades


def test_school_admin_update_does_not_strip_other_schools_grades(db):
    primary = _make_branch(db, "Primary School", "PR03")
    secondary = _make_branch(db, "High School", "HS03")
    _make_class(db, primary, "Grade 4")
    _make_class(db, secondary, "Form 2")
    english = _make_subject(db, "English", "ENG", ["Grade 4", "Form 2"])
    db.session.commit()

    updated, msg = update_subject_service(
        subject_id=english.id,
        form=_form(name="English", code="ENG"),
        selected_grades=["Form 2"],
        mutable_grade_names=["Form 2"],
    )
    assert updated is not None
    assert "successfully" in msg.lower()

    grades = {
        row.grade_form
        for row in SubjectEligibility.query.filter_by(subject_id=english.id).all()
    }
    assert grades == {"Grade 4", "Form 2"}


def test_school_admin_can_add_and_remove_own_grades_only(db):
    secondary = _make_branch(db, "High School", "HS04")
    _make_class(db, secondary, "Form 1")
    _make_class(db, secondary, "Form 2")
    english = _make_subject(db, "English", "ENG", ["Grade 4", "Form 1"])
    db.session.commit()

    updated, _ = update_subject_service(
        subject_id=english.id,
        form=_form(name="English", code="ENG"),
        selected_grades=["Form 2"],
        mutable_grade_names=["Form 1", "Form 2"],
    )
    assert updated is not None

    grades = {
        row.grade_form
        for row in SubjectEligibility.query.filter_by(subject_id=english.id).all()
    }
    assert grades == {"Grade 4", "Form 2"}
