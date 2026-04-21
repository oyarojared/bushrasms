from . import Branch, BranchClasses, db


def test_student_dash_get(client):
    response = client.get("/admin/student_dash")
    assert response.status_code == 200 
