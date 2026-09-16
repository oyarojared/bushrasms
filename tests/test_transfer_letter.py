from datetime import date

import pytest

from ..bushra import create_app
from ..bushra import db as _db
from ..bushra.config import DevelopmentConfig
from ..bushra.modals.branches_db import Branch, BranchClasses
from ..bushra.modals.staff_db import SuperAdminBranch, Teacher
from ..bushra.modals.students_db import Student
from ..bushra.modules.admin.services.transfer_letter import (
    default_release_sentence,
    gender_terms,
    is_transfer_letter_eligible,
    transfer_letter_context,
)
from ..bushra.modules.admin.utils.branch_utils import can_issue_official_letters
from ..bushra.modules.admin.utils.teacher_utils import hash_staff_password


@pytest.fixture()
def app(tmp_path, monkeypatch):
    uri = "sqlite:///" + str(tmp_path / "transfer.db").replace("\\", "/")
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


def _branch(db, name="Alpha High", code="P.O Box 10"):
    branch = Branch(
        branch_name=name,
        school_code=code,
        branch_manager="Manager",
        branch_level="Secondary",
        school_gender="Mixed",
        school_type="Day School",
        email="office@alpha.ac.ke",
        motto="Strive to excel",
    )
    db.session.add(branch)
    db.session.flush()
    return branch


def _class(db, branch, grade_form="Grade 10"):
    cls = BranchClasses(
        branch_id=branch.id,
        grade_form=grade_form,
        streams=["A"],
        class_year="2026",
    )
    db.session.add(cls)
    db.session.flush()
    return cls


def _teacher(
    db,
    branch,
    phone,
    *,
    is_admin=False,
    is_super_admin=False,
    is_system_admin=False,
):
    teacher = Teacher(
        branch_id=branch.id,
        employer="TSC",
        fullname="Staff Member",
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


def _student(db, branch, cls, **kwargs):
    values = {
        "fullname": "Amina Hassan",
        "admission_number": 21,
        "branch_id": branch.id,
        "class_id": cls.id,
        "stream": "A",
        "date_of_admission": date(2024, 1, 15),
    }
    values.update(kwargs)
    student = Student(**values)
    db.session.add(student)
    db.session.commit()
    return student


def _login(client, teacher_id):
    with client.session_transaction() as sess:
        sess["_user_id"] = str(teacher_id)
        sess["_fresh"] = True


def test_gender_terms_are_neutral_when_missing():
    terms = gender_terms("")
    assert terms["known"] is False
    assert terms["choice"] == "his or her"
    sentence = default_release_sentence("Alpha High", terms)
    assert "Alpha High" in sentence
    assert "his or her choice" in sentence
    assert "unavoidable circumstances" in sentence


def test_gender_terms_for_male_and_female():
    assert gender_terms("Male")["choice"] == "his"
    assert gender_terms("F")["choice"] == "her"


def test_default_letter_omits_next_school_and_uses_neutral_wording(db):
    branch = _branch(db)
    cls = _class(db, branch)
    student = _student(db, branch, cls, gender=None, knec_assessment_no="ASS001")
    context = transfer_letter_context(student, branch, "")
    assert "next school" not in context["body"].lower()
    assert "his or her choice" in context["body"]
    assert context["gender_label"] is None
    assert context["assessment_number"] == "ASS001"


def test_custom_reason_replaces_default_wording(db):
    branch = _branch(db)
    cls = _class(db, branch)
    student = _student(db, branch, cls, gender="Female", knec_assessment_no="ASS002")
    context = transfer_letter_context(student, branch, "Family relocation")
    assert "Family relocation" in context["body"]
    assert "unavoidable circumstances" not in context["body"]
    assert context["gender_label"] == "Female"


def test_teacher_cannot_issue_letter(app, db):
    branch = _branch(db)
    cls = _class(db, branch)
    teacher = _teacher(db, branch, "0700000101")
    student = _student(db, branch, cls, knec_assessment_no="ASS100")
    assert can_issue_official_letters(teacher) is False

    client = app.test_client()
    _login(client, teacher.id)
    response = client.post(
        f"/admin/student/{student.id}/transfer-letter",
        data={"knec_assessment_no": "ASS100"},
        follow_redirects=False,
    )
    assert response.status_code == 302


def test_admin_must_enter_assessment_number(app, db):
    branch = _branch(db)
    cls = _class(db, branch)
    admin = _teacher(db, branch, "0700000102", is_admin=True)
    student = _student(db, branch, cls, knec_assessment_no=None)

    client = app.test_client()
    _login(client, admin.id)
    response = client.post(
        f"/admin/student/{student.id}/transfer-letter",
        data={"knec_assessment_no": "  ", "reason": ""},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"assessment number" in response.data.lower()
    db.session.refresh(student)
    assert not student.knec_assessment_no


def test_admin_can_download_letter_and_saves_assessment_number(app, db):
    branch = _branch(db)
    cls = _class(db, branch)
    admin = _teacher(db, branch, "0700000103", is_admin=True)
    student = _student(db, branch, cls, knec_assessment_no=None)

    client = app.test_client()
    _login(client, admin.id)
    response = client.post(
        f"/admin/student/{student.id}/transfer-letter",
        data={
            "knec_assessment_no": "KNEC-7788",
            "reason": "Parent requested a transfer",
        },
    )
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/pdf"
    assert response.data.startswith(b"%PDF")
    db.session.refresh(student)
    assert student.knec_assessment_no == "KNEC-7788"


def test_letter_table_uses_grade_not_class(app, db):
    branch = _branch(db)
    cls = _class(db, branch)
    student = _student(db, branch, cls, gender="Female", knec_assessment_no="ASS010")
    context = transfer_letter_context(student, branch, "")
    assert context["grade_line"] == "Grade 10 A"
    html = app.jinja_env.get_template(
        "student_templates/transfer_letter.html"
    ).render(**context)
    assert "<th>Grade</th>" in html
    assert "<th>Class</th>" not in html
    assert "<th>Full name</th>" not in html
    start = html.find('<table class="particulars">')
    end = html.find("</table>", start)
    assert start != -1
    assert html[start:end].count("<tr>") == 2
    title_at = html.lower().find("student transfer letter")
    concern_at = html.lower().find("to whom it may concern")
    date_at = html.lower().find("date:")
    assert 0 <= title_at < concern_at < date_at
    assert 'class="doc-title"' in html
    assert 'class="salutation"' in html
    assert 'class="letter-date"' in html


def test_form_3_and_form_4_are_not_eligible(db):
    branch = _branch(db)
    form3 = _student(db, branch, _class(db, branch, "Form 3"), admission_number=31)
    form4 = _student(db, branch, _class(db, branch, "Form 4"), admission_number=41)
    grade10 = _student(db, branch, _class(db, branch, "Grade 10"), admission_number=10)
    assert is_transfer_letter_eligible(form3) is False
    assert is_transfer_letter_eligible(form4) is False
    assert is_transfer_letter_eligible(grade10) is True


def test_admin_cannot_issue_letter_for_form_4(app, db):
    branch = _branch(db)
    cls = _class(db, branch, "Form 4")
    admin = _teacher(db, branch, "0700000105", is_admin=True)
    student = _student(db, branch, cls, knec_assessment_no="ASS300")

    client = app.test_client()
    _login(client, admin.id)
    response = client.post(
        f"/admin/student/{student.id}/transfer-letter",
        data={"knec_assessment_no": "ASS300"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert response.headers.get("Content-Type", "").startswith("text/html")
    assert b"not issued" in response.data.lower()
    assert b"data-bs-target=\"#transferLetterModal\"" not in response.data


def test_super_admin_without_school_access_cannot_issue(app, db):
    home = _branch(db, "Home", "H001")
    other = _branch(db, "Other", "O001")
    cls = _class(db, other)
    super_admin = _teacher(db, home, "0700000104", is_admin=True, is_super_admin=True)
    db.session.add(SuperAdminBranch(teacher_id=super_admin.id, branch_id=home.id))
    student = _student(db, other, cls, knec_assessment_no="ASS200")

    client = app.test_client()
    _login(client, super_admin.id)
    response = client.post(
        f"/admin/student/{student.id}/transfer-letter",
        data={"knec_assessment_no": "ASS200"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Student not found" in response.data
