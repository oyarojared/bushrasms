# Inject forms and other functionalities that is meant
# to appear in all routes.

from flask import session

from ....modals.staff_db import Teacher
from ...admin.forms.staff_forms import TeacherPassportUploadForm
from ...admin.forms.students_forms import StudentSearchForm
from .. import admin_bp


@admin_bp.context_processor
def inject_global_context():
    """
    Inject shared forms and the logged-in teacher into
    all admin blueprint templates.
    """
    # Forms
    student_search_form = StudentSearchForm()
    teacher_passport_form = TeacherPassportUploadForm()

    # Logged-in User
    user = None
    user_id = session.get("user_id")
    if user_id:
        user = Teacher.query.get(user_id)

    return dict(
        form=student_search_form, 
        teacher_passport_upload_form=teacher_passport_form,
        user=user
    )

