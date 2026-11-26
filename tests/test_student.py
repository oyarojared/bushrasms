from datetime import date

import pytest
from flask import url_for

from ..bushra.modals.branches_db import Branch, BranchClasses
from ..bushra.modals.staff_db import SuperAdminBranch, Teacher
from ..bushra.modals.students_db import Student
from ..bushra.modules.admin.utils.teacher_utils import hash_staff_password


##### Test ---- STUDENT DELETE OPERATION ----- #####
def test_delete_student_success(client, db, test_student):
    student_id = test_student.id

    response = client.post(f"admin/delete_student/{student_id}", follow_redirects=True)

    # Student should be deleted
    deleted = Student.query.get(student_id)
    assert deleted is None

    # Should redirect to student_dash
    assert b"Student deleted successfully" in response.data


def test_delete_student_not_found(client, db):
    # Use an ID that doesn't exist
    response = client.post("admin/delete_student/9999", follow_redirects=True)

    # Should redirect with "Student not found"
    assert b"Student not found" in response.data


##### ----- TEST STUDENT PROFILE OPERATION ----- #####
def test_student_profile_get(client, test_student):
    "Test if this route returns the correctly in case of a get request."
    student_id = test_student.id

    response = client.get(f"/admin/student_profile/{student_id}")
    assert response.status_code == 200


def _school(db, name, code):
    branch = Branch(
        branch_name=name,
        school_code=code,
        branch_manager="Head",
        branch_level="Mixed",
        school_gender="Co-ed",
        school_type="Day",
        email=f"{code.lower()}@example.com",
    )
    db.session.add(branch)
    db.session.flush()
    return branch


def _class(db, branch, grade_form):
    school_class = BranchClasses(
        branch_id=branch.id,
        grade_form=grade_form,
        streams=["A"],
        class_year="2026",
    )
    db.session.add(school_class)
    db.session.flush()
    return school_class


def _learner(db, branch, school_class, fullname, admission_number):
    student = Student(
        fullname=fullname,
        admission_number=admission_number,
        branch_id=branch.id,
        class_id=school_class.id,
        stream="A",
        current_year=2026,
        gender="F",
        date_of_admission=date(2026, 1, 10),
    )
    db.session.add(student)
    db.session.flush()
    return student


def _login(client, teacher):
    with client.session_transaction() as sess:
        sess["_user_id"] = str(teacher.id)
        sess["_fresh"] = True


def test_super_admin_can_move_students_to_another_school(db, client):
    primary = _school(db, "Primary Move", "PM001")
    senior = _school(db, "Senior Move", "SM001")
    grade8 = _class(db, primary, "Grade 8")
    grade9 = _class(db, senior, "Grade 9")
    first = _learner(db, primary, grade8, "Amina Otieno", 4)
    second = _learner(db, primary, grade8, "Benta Kariuki", 5)
    already = _learner(db, senior, grade9, "Cate Njeri", 4)
    admin = Teacher(
        branch_id=primary.id,
        employer="TSC",
        fullname="Two School Admin",
        gender="F",
        title="Mrs.",
        phone="0711000001",
        username="moveschools",
        password_hash=hash_staff_password("secret12"),
        is_admin=True,
        is_super_admin=True,
    )
    db.session.add(admin)
    db.session.flush()
    db.session.add(SuperAdminBranch(teacher_id=admin.id, branch_id=primary.id))
    db.session.add(SuperAdminBranch(teacher_id=admin.id, branch_id=senior.id))
    db.session.commit()
    _login(client, admin)

    profile = client.get(f"/admin/student_profile/{first.id}")
    assert profile.status_code == 200
    assert b"Choose another school you can open" in profile.data
    assert b"Senior Move" in profile.data

    roster = client.post(
        "/admin/student_dash",
        data={"branch": primary.id, "grade_form": grade8.id, "stream": "A"},
    )
    assert roster.status_code == 200
    assert b"bulk-move-school" in roster.data
    assert b"Senior Move" in roster.data

    moved = client.post(
        "/admin/students/bulk-move",
        data={
            "source_branch_id": primary.id,
            "source_class_id": grade8.id,
            "source_stream": "A",
            "dest_branch_id": senior.id,
            "grade_form": grade9.id,
            "stream": "A",
            "student_ids": [first.id, second.id],
        },
        follow_redirects=True,
    )
    assert moved.status_code == 200
    assert b"Senior Move" in moved.data

    db.session.refresh(first)
    db.session.refresh(second)
    db.session.refresh(already)
    assert first.branch_id == senior.id
    assert first.class_id == grade9.id
    assert second.branch_id == senior.id
    assert second.class_id == grade9.id
    assert sorted([first.admission_number, second.admission_number]) == [5, 6]
    assert already.admission_number == 4
    assert already.class_id == grade9.id


def test_school_admin_cannot_move_students_to_another_school(db, client):
    primary = _school(db, "Primary Only", "PO001")
    senior = _school(db, "Senior Closed", "SC001")
    grade8 = _class(db, primary, "Grade 8")
    grade9 = _class(db, senior, "Grade 9")
    learner = _learner(db, primary, grade8, "Dina Wanjiku", 3)
    admin = Teacher(
        branch_id=primary.id,
        employer="TSC",
        fullname="One School Admin",
        gender="F",
        title="Mrs.",
        phone="0711000002",
        username="oneschool",
        password_hash=hash_staff_password("secret12"),
        is_admin=True,
    )
    db.session.add(admin)
    db.session.commit()
    _login(client, admin)

    refused = client.post(
        "/admin/students/bulk-move",
        data={
            "source_branch_id": primary.id,
            "source_class_id": grade8.id,
            "dest_branch_id": senior.id,
            "grade_form": grade9.id,
            "stream": "A",
            "student_ids": [learner.id],
        },
        follow_redirects=True,
    )
    assert b"cannot move students to that school" in refused.data
    db.session.refresh(learner)
    assert learner.branch_id == primary.id
    assert learner.class_id == grade8.id
    assert learner.admission_number == 3


def test_promote_stays_hidden_until_it_is_enabled(db, client, app):
    primary = _school(db, "Primary Closed", "PC001")
    admin = Teacher(
        branch_id=primary.id,
        employer="TSC",
        fullname="Closed Head",
        gender="F",
        title="Mrs.",
        phone="0711000005",
        username="closedpromo",
        password_hash=hash_staff_password("secret12"),
        is_admin=True,
    )
    db.session.add(admin)
    db.session.commit()
    _login(client, admin)
    app.config["PROMOTION_ENABLED"] = False

    page = client.get("/admin/student_dash")
    assert b">Promote<" not in page.data

    blocked = client.get("/admin/promote", follow_redirects=True)
    assert b"Promotion is not open yet." in blocked.data


def test_promote_tooltip_skips_form_4_for_a_primary_school(db, client):
    primary = _school(db, "Primary Tip", "PT001")
    _class(db, primary, "Grade 8")
    admin = Teacher(
        branch_id=primary.id,
        employer="TSC",
        fullname="Primary Head",
        gender="F",
        title="Mrs.",
        phone="0711000003",
        username="primarytip",
        password_hash=hash_staff_password("secret12"),
        is_admin=True,
    )
    db.session.add(admin)
    db.session.commit()
    _login(client, admin)

    page = client.get("/admin/student_dash")
    assert page.status_code == 200
    assert b'title="Close the year, move classes up, and keep repeaters."' in page.data
    assert b"and complete Form 4." not in page.data


def test_promote_tooltip_mentions_form_4_when_the_school_has_it(db, client):
    secondary = _school(db, "Secondary Tip", "ST001")
    _class(db, secondary, "Form 4")
    admin = Teacher(
        branch_id=secondary.id,
        employer="TSC",
        fullname="Secondary Head",
        gender="F",
        title="Mrs.",
        phone="0711000004",
        username="secondarytip",
        password_hash=hash_staff_password("secret12"),
        is_admin=True,
    )
    db.session.add(admin)
    db.session.commit()
    _login(client, admin)

    page = client.get("/admin/student_dash")
    assert b"complete Form 4" in page.data
