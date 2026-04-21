import re

from flask import current_app, flash, redirect, request, send_file, url_for

from ....modals.branches_db import Branch
from ....modals.staff_db import Teacher
from ....modals.students_db import Student
from .. import admin_bp
from ..utils import generate_excel_file
from flask_login import login_required

student_fields = [
    "admission_number",
    "fullname",
    "gender",
    "dob",
    "kcpe_marks",
    "kcpe_index_no",
    "kcpe_year",
    "parent_fullname",
    "parent_phone",
    "boarding_status",
    "birth_cert_no",
    "nemis_number",
    "pathway",
    "date_of_admission",
]

student_headers = [
    "ADM NO",
    "FULLNAME",
    "GENDER",
    "DOB",
    "KCPE",
    "KCPE INDEX NO",
    "KCPE YEAR",
    "PARENT NAME",
    "PHONE",
    "BOARDING STATUS",
    "BIRTH CERT NO",
    "NEMIS NO",
    "PATHWAY",
    "DATE OF ADMISSION",
]


def sanitize_filename(s):
    return re.sub(r"[^\w\- ]", "_", s)


def get_students(branch_id, class_id, stream=None):
    """
    Fetch students by branch, grade/form, and optional stream.
    """
    if stream == "":
        stream = None
    all_students = Student.query.filter(
        Student.branch_id == branch_id, Student.class_id == class_id
    ).all()

    if stream is None:
        return all_students

    # Filter by stream
    filtered_students = [s for s in all_students if s.stream == stream]
    return filtered_students


@admin_bp.route("/download_students_excel", methods=["POST", "GET"])
@login_required
def download_students_excel():
    """
    Download students list of the selected branch, grade/form and (stream)
    """
    branch_id = request.form.get("branch", type=int)
    grade_id = request.form.get("gradeid", type=int)
    grade_name = request.form.get("grade") or ""
    stream = request.form.get("stream") or None
    if stream:
        stream = stream.strip()

    if not branch_id or not grade_id:
        flash(
            "Please select a branch and grade/form to generate excel file!", "warning"
        )
        return redirect(url_for("admin.student_dash"))

    branch = Branch.query.get(branch_id)
    if not branch:
        flash("Selected branch not found.", "danger")
        return redirect(url_for("admin.student_dash"))

    students = get_students(branch_id, grade_id, stream=stream)

    if not students:
        flash(
            "No students found for the selected branch, grade/form, and stream.", "info"
        )

    # Prepare download filename
    downloaded_file_name = (
        f"{grade_name.upper()}_{stream or ''}_{branch.branch_name.upper()}_STUDENTS"
    )
    downloaded_file_name = sanitize_filename(downloaded_file_name)

    excel_file = generate_excel_file(
        fields=student_fields, 
        headers=student_headers, 
        data=students
    )

    return send_file(
        excel_file,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=f"{downloaded_file_name}.xlsx",
    )


@admin_bp.route("download_teachers_excel_file", methods=["GET"])
@login_required
def dowload_teachers_excel_file():
    headers = ["FULLNAME","TEACHER CODE","TSC NUMBER","ID NUMBER","PHONE",
        "EMAIL","EMPLOYER"
    ]
    fields = ["fullname","staff_id","tsc_no","id_no","phone","email",
        "employer"
    ]
      
    try: 
        teachers = Teacher.query.all()
        if not teachers:
            flash("No teachers in the system yet.", "warning")
            return redirect(url_for("admin.school_staff")) 
        
        excel_file = generate_excel_file(
            headers=headers, 
            fields=fields, 
            data=teachers
        )

        return send_file(
            excel_file,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name="ALL_TEACHERS_LIST.xlsx",
        )
        
    except Exception as e:
        current_app.logger.error(f"Can't generate teacher excel file: {e}") 
        
    # -------- Incase generation of excel file fails -------- #
    flash(
        "An Error occured during the generation of teachers excel sheet! Try later.",
        "danger"
    )  
    return redirect(url_for("admin.school_staff"))
    