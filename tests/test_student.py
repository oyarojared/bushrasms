import pytest
from flask import url_for

from ..bushra.modals.students_db import Student


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
