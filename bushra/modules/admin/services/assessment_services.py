
from ....modals.assessment_db import Exam, ExamBranch, ExamPaper, db
from sqlalchemy.orm import joinedload


def get_exams_for_user(user):
    query = (
        db.session.query(Exam)
        .options(joinedload(Exam.exam_branches))
        .join(Exam.exam_branches)
        .filter(Exam.is_inactive == False)
    )

    if user.is_super_admin:
        pass  # no extra filter

    elif user.is_admin:
        query = query.filter(ExamBranch.branch_id == user.branch_id)

    else:
        query = query.filter(
            ExamBranch.branch_id == user.branch_id,
            Exam.is_locked == False
        )

    return query.order_by(Exam.year.desc(), Exam.term).distinct()
