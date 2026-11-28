from datetime import date
from io import BytesIO
from types import SimpleNamespace

from openpyxl import load_workbook

from ..bushra import db as _db
from ..bushra.modals.assessment_db import Exam, ExamBranch, ExamPaper, StudentExamMark
from ..bushra.modals.branches_db import Branch, BranchClasses
from ..bushra.modals.staff_db import Teacher
from ..bushra.modals.students_db import Student, StudentSubjectAllocation
from ..bushra.modals.subjects_db import Subject
from ..bushra.modules.admin.services.subject_marks_excel import (
    build_subject_marks_workbook,
    match_subject_mark_rows,
    parse_subject_marks_workbook,
)
from ..bushra.modules.admin.utils.teacher_utils import hash_staff_password


def _learner(student_id, admission, name):
    return SimpleNamespace(id=student_id, admission_number=admission, fullname=name)


def test_subject_sheet_round_trip_keeps_admission_name_and_marks():
    students = [
        _learner(2, 14, "Benta Kariuki"),
        _learner(1, 10, "Amina Otieno"),
    ]
    workbook = build_subject_marks_workbook(students, {1: 78, 2: None})
    rows = parse_subject_marks_workbook(workbook)

    assert rows == [
        {"admission_number": "10", "marks": 78},
        {"admission_number": "14", "marks": None},
    ]
    workbook.seek(0)
    sheet = load_workbook(workbook).active
    assert [cell.value for cell in sheet[1]] == ["Adm No", "Full name", "Marks"]
    assert sheet["A2"].value == 10
    assert sheet["B2"].value == "Amina Otieno"


def test_upload_matches_admission_numbers_and_rejects_a_mark_over_the_limit():
    students = [_learner(1, 10, "Amina Otieno")]
    updates, skipped, errors = match_subject_mark_rows(
        students,
        [
            {"admission_number": "10", "marks": 45},
            {"admission_number": "99", "marks": 10},
        ],
        60,
    )
    assert updates == [{"student_id": 1, "marks": 45}]
    assert skipped == ["99"]
    assert errors == []

    _updates, _skipped, errors = match_subject_mark_rows(
        students,
        [{"admission_number": "10", "marks": 61}],
        60,
    )
    assert errors == ["Admission 10 has 61, which is outside 0 to 60."]


def test_sheet_rejects_a_repeated_admission_number():
    students = [_learner(1, 10, "Amina Otieno")]
    workbook = build_subject_marks_workbook(students, {1: 40})
    sheet = load_workbook(workbook)
    sheet.active.append([10, "Amina Otieno", 50])
    payload = __import__("io").BytesIO()
    sheet.save(payload)
    payload.seek(0)

    try:
        parse_subject_marks_workbook(payload)
    except ValueError as error:
        assert "more than once" in str(error)
    else:
        raise AssertionError("A repeated admission number should be refused.")


def _login(client, username="marksadmin"):
    response = client.post(
        "/auth/login",
        data={"username": username, "password": "secret12", "submit": "Login"},
        follow_redirects=False,
    )
    assert response.status_code in (302, 303)


def test_download_then_upload_saves_and_a_blank_mark_clears(app, client, db):
    school = Branch(
        branch_name="Primary",
        school_code="MK01",
        branch_manager="Head",
        branch_level="primary",
        school_gender="Co-ed",
        school_type="Day",
        email="marks@example.com",
    )
    db.session.add(school)
    db.session.flush()
    school_class = BranchClasses(
        branch_id=school.id,
        grade_form="Grade 4",
        class_year="2026",
    )
    subject = Subject(name="Mathematics MK", code="MKMAT", category="Core")
    exam = Exam(name="Opener", year=2026, term="I")
    db.session.add_all([school_class, subject, exam])
    db.session.flush()
    db.session.add(ExamBranch(exam_id=exam.id, branch_id=school.id))
    kept = Student(
        branch_id=school.id,
        class_id=school_class.id,
        admission_number=10,
        fullname="Amina Otieno",
        date_of_admission=date(2026, 1, 10),
    )
    cleared = Student(
        branch_id=school.id,
        class_id=school_class.id,
        admission_number=14,
        fullname="Benta Kariuki",
        date_of_admission=date(2026, 1, 10),
    )
    db.session.add_all([kept, cleared])
    db.session.flush()
    db.session.add_all([
        StudentSubjectAllocation(student_id=kept.id, subject_id=subject.id),
        StudentSubjectAllocation(student_id=cleared.id, subject_id=subject.id),
    ])
    teacher = Teacher(
        branch_id=school.id,
        employer="BOM",
        fullname="Marks Admin",
        gender="F",
        title="Mrs.",
        phone="0711999001",
        username="marksadmin",
        password_hash=hash_staff_password("secret12"),
        is_admin=True,
    )
    db.session.add(teacher)
    db.session.commit()

    _login(client)
    page = client.get(f"/admin/exams/{exam.id}/marks")
    assert page.status_code == 200
    assert b"downloadSubjectMarksBtn" in page.data
    assert b"uploadSubjectMarksBtn" in page.data

    query = {
        "branch_id": school.id,
        "class_id": school_class.id,
        "subject_id": subject.id,
        "exam_id": exam.id,
    }
    downloaded = client.get("/admin/api/subject-marks/excel", query_string=query)
    assert downloaded.status_code == 200
    sheet = load_workbook(BytesIO(downloaded.data)).active
    assert [cell.value for cell in sheet[1]] == ["Adm No", "Full name", "Marks"]
    sheet["C2"] = 45
    sheet["C3"] = 30
    filled = BytesIO()
    sheet.parent.save(filled)
    filled.seek(0)

    uploaded = client.post(
        "/admin/api/subject-marks/excel",
        data={
            **query,
            "marks_out_of": "60",
            "file": (filled, "marks.xlsx"),
        },
        content_type="multipart/form-data",
    )
    assert uploaded.status_code == 200
    assert uploaded.get_json()["saved"] == 2
    paper = ExamPaper.query.filter_by(subject_id=subject.id).one()
    assert paper.marks_out_of == 60
    stored = {
        row.student_id: row.marks
        for row in StudentExamMark.query.filter_by(exam_paper_id=paper.id)
    }
    assert stored[kept.id] == 45
    assert stored[cleared.id] == 30

    downloaded = client.get("/admin/api/subject-marks/excel", query_string=query)
    sheet = load_workbook(BytesIO(downloaded.data)).active
    sheet["C3"] = None
    cleared_file = BytesIO()
    sheet.parent.save(cleared_file)
    cleared_file.seek(0)
    cleared_upload = client.post(
        "/admin/api/subject-marks/excel",
        data={**query, "file": (cleared_file, "marks.xlsx")},
        content_type="multipart/form-data",
    )
    assert cleared_upload.status_code == 200
    body = cleared_upload.get_json()
    assert body["cleared"] == 1
    assert StudentExamMark.query.filter_by(student_id=cleared.id).count() == 0
    assert ExamPaper.query.get(paper.id).marks_out_of == 60

    too_high = BytesIO()
    sheet["C2"] = 80
    sheet.parent.save(too_high)
    too_high.seek(0)
    rejected = client.post(
        "/admin/api/subject-marks/excel",
        data={**query, "file": (too_high, "marks.xlsx")},
        content_type="multipart/form-data",
    )
    assert rejected.status_code == 400
    assert StudentExamMark.query.filter_by(student_id=kept.id).one().marks == 45
    _db.session.rollback()
