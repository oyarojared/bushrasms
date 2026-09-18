from datetime import date
import base64
import io
import re

import pytest
from PIL import Image

from ..bushra import create_app
from ..bushra import db as _db
from ..bushra.config import DevelopmentConfig
from ..bushra.modals.branches_db import Branch, BranchClasses
from ..bushra.modals.staff_db import SuperAdminBranch, Teacher
from ..bushra.modals.students_db import Student
from ..bushra.modules.admin.services.leaving_certificate import (
    HEADTEACHER_REPORTS,
    REPORT_MAX_LINES,
    REPORT_MAX_WORDS,
    branch_form_defaults,
    coat_of_arms_data_uri,
    date_in_words,
    headteacher_report_fits,
    is_leaving_certificate_eligible,
    leaving_certificate_context,
    report_word_count,
    reports_are_gender_neutral,
    school_name_for_certificate,
    split_headteacher_report,
    student_form_defaults,
    without_trailing_school,
    year_in_words,
)
from ..bushra.modules.admin.utils.teacher_utils import hash_staff_password


@pytest.fixture()
def app(tmp_path, monkeypatch):
    uri = "sqlite:///" + str(tmp_path / "leaving.db").replace("\\", "/")
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


def _class(db, branch, grade_form="Form 4"):
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
        "date_of_admission": date(2022, 1, 15),
        "dob": date(2008, 6, 15),
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


def _certificate_post_data(**overrides):
    payload = {
        "school_name": "Alpha High",
        "school_address": "P.O Box 10, office@alpha.ac.ke",
        "student_name": "Amina Hassan",
        "admission_number": "21",
        "date_of_birth": "2008-06-15",
        "date_of_admission": "2022-01-15",
        "form_enrolled": "ONE",
        "date_of_leaving": "2026-11-20",
        "issue_date": "2026-11-21",
        "headteacher_report": HEADTEACHER_REPORTS[0],
    }
    payload.update(overrides)
    return payload


def test_fourteen_gender_neutral_reports():
    assert len(HEADTEACHER_REPORTS) == 14
    assert len(set(HEADTEACHER_REPORTS)) == 14
    assert reports_are_gender_neutral() is True
    ranking = re.compile(
        r"\b(average|above-average|below-average|academically|reasonably able)\b",
        re.I,
    )
    ability = re.compile(r"\b(ability|able to|capacity|can )\b", re.I)
    for text in HEADTEACHER_REPORTS:
        assert text.count(".") == 2
        assert ranking.search(text) is None
        assert ability.search(text)
        assert "completed the course" not in text.lower()
        assert "completing the course" not in text.lower()


def test_headteacher_report_splits_without_losing_words():
    first, more, blanks = split_headteacher_report(HEADTEACHER_REPORTS[3])
    assert first
    assert "Headteacher" not in first
    assert " ".join([first, *more]) == HEADTEACHER_REPORTS[3]
    assert 1 + len(more) + blanks >= REPORT_MAX_LINES


def test_stock_reports_fit_the_certificate_word_limit():
    assert all(report_word_count(text) <= REPORT_MAX_WORDS for text in HEADTEACHER_REPORTS)
    assert all(headteacher_report_fits(text) for text in HEADTEACHER_REPORTS)


def test_long_custom_report_is_capped_to_three_lines():
    long_report = " ".join(["satisfactory"] * 40)
    assert report_word_count(long_report) > REPORT_MAX_WORDS
    assert headteacher_report_fits(long_report) is False
    first, more, blanks = split_headteacher_report(long_report)
    assert 1 + len(more) <= REPORT_MAX_LINES
    assert 1 + len(more) + blanks == REPORT_MAX_LINES
    assert first


def test_date_and_year_in_words():
    assert date_in_words(date(2008, 6, 15)) == "FIFTEENTH JUNE TWO THOUSAND AND EIGHT"
    assert date_in_words(date(1998, 1, 1)) == "FIRST JANUARY NINETEEN NINETY EIGHT"
    assert year_in_words(2026) == "two thousand and twenty six"


def test_coat_of_arms_prints_black_on_white(app):
    uri = coat_of_arms_data_uri()
    image = Image.open(io.BytesIO(base64.b64decode(uri.split(",", 1)[1]))).convert("L")
    width, height = image.size
    assert width > 800
    assert height > 800
    corners = (
        image.getpixel((2, 2)),
        image.getpixel((width - 3, 2)),
        image.getpixel((2, height - 3)),
        image.getpixel((width - 3, height - 3)),
    )
    assert min(corners) > 200
    assert image.getextrema()[0] < 55
    lion = image.getpixel((int(width * 0.22), int(height * 0.42)))
    shield = image.getpixel((width // 2, int(height * 0.48)))
    assert lion > shield + 40


def test_only_form_4_is_eligible(db):
    branch = _branch(db)
    form4 = _student(db, branch, _class(db, branch, "Form 4"), admission_number=41)
    form3 = _student(db, branch, _class(db, branch, "Form 3"), admission_number=31)
    grade10 = _student(db, branch, _class(db, branch, "Grade 10"), admission_number=10)
    assert is_leaving_certificate_eligible(form4) is True
    assert is_leaving_certificate_eligible(form3) is False
    assert is_leaving_certificate_eligible(grade10) is False


def test_certificate_html_matches_official_blank(app):
    context = leaving_certificate_context(
        {
            "school_name": "Alpha High School",
            "school_address": "P.O Box 10, office@alpha.ac.ke",
            "student_name": "Amina Hassan",
            "admission_number": "21",
            "date_of_birth": date(2008, 6, 15),
            "date_of_admission": date(2022, 1, 15),
            "form_enrolled": "ONE",
            "date_of_leaving": date(2026, 11, 20),
            "issue_date": date(2026, 11, 21),
            "headteacher_report": HEADTEACHER_REPORTS[3],
        }
    )
    html = app.jinja_env.get_template("student_templates/leaving_certificate.html").render(
        **context
    )
    lower = html.lower()
    assert context["coat_of_arms_uri"]
    assert context["coat_of_arms_uri"].startswith("data:image/png")
    assert 'class="arms"' in html
    assert "coat of arms of kenya" in lower
    assert "ed/b 100" in lower
    assert "ministry of education, science and technology" in lower
    assert 'class="doc-title doc-title-cert"' in html
    assert "rule-title" not in html
    assert "this is to certify that" in lower
    assert "admission/serial no" in lower
    assert "entered this school on" in lower
    assert "and was enrolled in" in lower
    assert "having satisfactorily completed the approved" in lower
    assert "date of birth (in admission register)" in lower
    assert "pupil's signature" in lower
    assert "gpk(l)" in lower
    assert 'class="page-footer"' in html
    assert "without any erasure or alteration whatsoever" in lower
    assert context["school_name"] == "ALPHA HIGH"
    assert "ALPHA HIGH" in html
    assert "SCHOOL" in html
    assert "P.O Box 10, office@alpha.ac.ke" in html
    assert "AMINA HASSAN" in html
    fill_css = html[html.find("table.line td.fill,") : html.find("table.line td.gap")]
    assert "font-size: 11pt" in fill_css
    report_css = html[html.find(".report-block td.fill {") : html.find(".sign-block {")]
    assert "font-size: 12.5pt" in report_css
    assert "font-weight: 600" in report_css
    legal_css = html[html.find(".legal {") : html.find(".legal {") + 140]
    gpk_css = html[html.find(".gpk {") : html.find(".gpk {") + 120]
    assert "font-weight: 700" in legal_css
    assert "font-weight: 700" in gpk_css
    joined_report = " ".join(
        [context["report_first"], *context["report_more"]]
    ).strip()
    assert joined_report == HEADTEACHER_REPORTS[3]
    assert context["report_first"] in html
    assert 'class="words report-label"' in html
    assert 'class="headteacher-sign"' in html
    assert "headteacher's report on the pupil's ability, industry and conduct" in lower
    assert "ONE" in html
    assert "FOUR" in html
    assert "passport" not in lower
    assert "school logo" not in lower
    assert "school stamp" not in lower
    assert "highest examination" not in lower
    assert "address:" not in lower
    assert "headteacher's name" not in lower
    assert "(in words)" not in lower
    assert "he/she" not in lower
    assert "his/her" not in lower


def test_teacher_cannot_issue_certificate(app, db):
    branch = _branch(db)
    teacher = _teacher(db, branch, "0700000201")
    student = _student(db, branch, _class(db, branch))
    client = app.test_client()
    _login(client, teacher.id)
    response = client.get(
        f"/admin/student/{student.id}/leaving-certificate",
        follow_redirects=False,
    )
    assert response.status_code == 302


def test_admin_cannot_issue_for_form_3(app, db):
    branch = _branch(db)
    admin = _teacher(db, branch, "0700000202", is_admin=True)
    student = _student(db, branch, _class(db, branch, "Form 3"))
    client = app.test_client()
    _login(client, admin.id)
    response = client.get(
        f"/admin/student/{student.id}/leaving-certificate",
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"id=\"leavingCertificateForm\"" not in response.data
    assert b"Form 4 students only" in response.data


def test_form_4_profile_shows_leaving_certificate_button(app, db):
    branch = _branch(db)
    admin = _teacher(db, branch, "0700000203", is_admin=True)
    student = _student(db, branch, _class(db, branch, "Form 4"))
    client = app.test_client()
    _login(client, admin.id)
    response = client.get(f"/admin/student_profile/{student.id}")
    assert response.status_code == 200
    assert b"Leaving certificate" in response.data
    assert b"Transfer letter" not in response.data


def test_admin_can_prefill_and_customize_without_changing_student(app, db):
    branch = _branch(db)
    admin = _teacher(db, branch, "0700000204", is_admin=True)
    student = _student(db, branch, _class(db, branch, "Form 4"))
    original_dob = student.dob
    original_name = student.fullname

    client = app.test_client()
    _login(client, admin.id)
    worksheet = client.get(f"/admin/student/{student.id}/leaving-certificate")
    assert worksheet.status_code == 200
    assert b"Amina Hassan" in worksheet.data
    assert b"id=\"leavingCertificateForm\"" in worksheet.data
    assert b'id="lcReportCount"' in worksheet.data
    assert f"Keep to {REPORT_MAX_WORDS} words".encode() in worksheet.data
    assert f'data-max-words="{REPORT_MAX_WORDS}"'.encode() in worksheet.data
    assert b"Edit the printed details." in worksheet.data
    assert b"Don't include SCHOOL. It's already printed." in worksheet.data
    assert b'id="lcSchoolHint"' in worksheet.data

    response = client.post(
        f"/admin/student/{student.id}/leaving-certificate",
        data=_certificate_post_data(
            student_name="Amina H. Hassan",
            date_of_birth="2008-03-12",
        ),
    )
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/pdf"
    assert response.data.startswith(b"%PDF")
    db.session.refresh(student)
    assert student.fullname == original_name
    assert student.dob == original_dob
    assert Student.query.count() == 1


def test_former_student_certificate_does_not_create_a_student(app, db):
    branch = _branch(db)
    admin = _teacher(db, branch, "0700000205", is_admin=True)
    assert Student.query.count() == 0

    client = app.test_client()
    _login(client, admin.id)
    worksheet = client.get("/admin/leaving-certificate")
    assert worksheet.status_code == 200
    assert b"former Form 4" in worksheet.data
    assert b"The date the pupil left, not today." in worksheet.data
    left_input = re.search(
        rb"<input[^>]*id=\"lcLeft\"[^>]*>|<input[^>]*id='lcLeft'[^>]*>",
        worksheet.data,
    )
    assert left_input
    assert not re.search(rb'value="\d{4}-\d{2}-\d{2}"', left_input.group(0))

    response = client.post(
        "/admin/leaving-certificate",
        data=_certificate_post_data(student_name="Former Pupil"),
    )
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/pdf"
    assert response.data.startswith(b"%PDF")
    assert Student.query.count() == 0


def test_certificate_allows_missing_date_of_birth(app, db):
    context = leaving_certificate_context(
        {
            "school_name": "Alpha High",
            "student_name": "Amina Hassan",
            "admission_number": "21",
            "date_of_birth": None,
            "date_of_admission": date(2022, 1, 15),
            "form_enrolled": "ONE",
            "date_of_leaving": date(2026, 11, 20),
            "issue_date": date(2026, 11, 21),
            "headteacher_report": HEADTEACHER_REPORTS[0],
        }
    )
    assert context["date_of_birth"] == ""
    html = app.jinja_env.get_template("student_templates/leaving_certificate.html").render(
        **context
    )
    assert "Date of Birth (in Admission Register)" in html

    branch = _branch(db)
    admin = _teacher(db, branch, "0700000208", is_admin=True)
    client = app.test_client()
    _login(client, admin.id)
    worksheet = client.get("/admin/leaving-certificate")
    assert b'for="lcDob"' in worksheet.data
    assert b'stu-label-required" for="lcDob"' not in worksheet.data
    assert b"Changes are not saved to the student record." in worksheet.data
    assert b"(optional)" in worksheet.data

    payload = _certificate_post_data()
    payload["date_of_birth"] = ""
    response = client.post("/admin/leaving-certificate", data=payload)
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/pdf"
    assert response.data.startswith(b"%PDF")


def test_invalid_dates_stay_on_the_form(app, db):
    branch = _branch(db)
    admin = _teacher(db, branch, "0700000206", is_admin=True)
    client = app.test_client()
    _login(client, admin.id)
    response = client.post(
        "/admin/leaving-certificate",
        data=_certificate_post_data(
            date_of_admission="2026-01-01",
            date_of_leaving="2025-01-01",
        ),
    )
    assert response.status_code == 200
    assert response.headers.get("Content-Type", "").startswith("text/html")
    assert b"cannot be before admission" in response.data


def test_missing_leaving_date_stays_on_the_form(app, db):
    branch = _branch(db)
    admin = _teacher(db, branch, "0700000210", is_admin=True)
    client = app.test_client()
    _login(client, admin.id)
    payload = _certificate_post_data()
    payload["date_of_leaving"] = ""
    response = client.post("/admin/leaving-certificate", data=payload)
    assert response.status_code == 200
    assert response.headers.get("Content-Type", "").startswith("text/html")
    assert b"Enter the date the pupil left school." in response.data


def test_overlong_custom_report_stays_on_the_form(app, db):
    branch = _branch(db)
    admin = _teacher(db, branch, "0700000209", is_admin=True)
    client = app.test_client()
    _login(client, admin.id)
    too_long = " ".join(["ability"] * (REPORT_MAX_WORDS + 1))
    response = client.post(
        "/admin/leaving-certificate",
        data=_certificate_post_data(headteacher_report=too_long),
    )
    assert response.status_code == 200
    assert response.headers.get("Content-Type", "").startswith("text/html")
    assert b"three lines on the certificate" in response.data
    assert too_long.encode() in response.data


def test_super_admin_without_school_access_cannot_issue_for_enrolled_student(app, db):
    home = _branch(db, "Home", "H001")
    other = _branch(db, "Other", "O001")
    super_admin = _teacher(db, home, "0700000207", is_admin=True, is_super_admin=True)
    db.session.add(SuperAdminBranch(teacher_id=super_admin.id, branch_id=home.id))
    student = _student(db, other, _class(db, other, "Form 4"))

    client = app.test_client()
    _login(client, super_admin.id)
    response = client.get(
        f"/admin/student/{student.id}/leaving-certificate",
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Student not found" in response.data


def test_school_name_drops_trailing_school(db):
    assert without_trailing_school("Alpha High School") == "Alpha High"
    assert without_trailing_school("Alpha High School School") == "Alpha High"
    assert without_trailing_school("School") == ""
    assert without_trailing_school("Alliance High") == "Alliance High"
    assert school_name_for_certificate("Alpha High School") == "ALPHA HIGH"
    branch = _branch(db, name="Alpha High School")
    assert branch_form_defaults(branch)["school_name"] == "Alpha High"


def test_student_defaults_keep_register_values(db):
    branch = _branch(db)
    student = _student(db, branch, _class(db, branch, "Form 4"))
    defaults = student_form_defaults(student, branch)
    assert defaults["student_name"] == "Amina Hassan"
    assert defaults["admission_number"] == "21"
    assert defaults["date_of_birth"] == date(2008, 6, 15)
    assert defaults["school_name"] == "Alpha High"
    assert defaults["school_address"] == "P.O Box 10, office@alpha.ac.ke"
    assert defaults["form_enrolled"] == "ONE"
    assert defaults["date_of_leaving"] is None
    assert defaults["issue_date"] == date.today()
    assert defaults["headteacher_report"] in HEADTEACHER_REPORTS

    student.dob = None
    db.session.flush()
    assert student_form_defaults(student, branch)["date_of_birth"] is None
