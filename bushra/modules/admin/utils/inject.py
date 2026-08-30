# Inject forms and other functionalities that is meant
# to appear in all routes.

from flask import has_request_context, session
from flask_login import current_user

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
    if not has_request_context():
        return {
            "form": None,
            "teacher_passport_upload_form": None,
            "user": None,
            "marks_deadline_banner": None,
        }

    student_search_form = StudentSearchForm()
    teacher_passport_form = TeacherPassportUploadForm()

    user = None
    user_id = session.get("user_id")
    if user_id:
        user = Teacher.query.get(user_id)

    marks_deadline_banner = None
    try:
        if getattr(current_user, "is_authenticated", False):
            from ..services.assessment_services import get_exams_for_user
            from .exam_deadlines import nearest_open_deadline

            exams = get_exams_for_user(current_user).all()
            marks_deadline_banner = nearest_open_deadline(exams)
    except Exception:
        marks_deadline_banner = None

    return dict(
        form=student_search_form,
        teacher_passport_upload_form=teacher_passport_form,
        user=user,
        marks_deadline_banner=marks_deadline_banner,
    )

