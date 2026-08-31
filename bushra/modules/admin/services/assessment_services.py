
from ....modals.assessment_db import Exam, ExamBranch, ExamPaper, StudentExamMark, db
from ....modals.branches_db import Branch
from sqlalchemy.orm import joinedload

from ..utils.branch_utils import user_can_access_branch


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


def branch_has_locked_exams(user):
    if not user or not getattr(user, "branch_id", None):
        return False

    return (
        db.session.query(Exam.id)
        .join(Exam.exam_branches)
        .filter(
            Exam.is_inactive == False,
            Exam.is_locked == True,
            ExamBranch.branch_id == user.branch_id,
        )
        .first()
        is not None
    )


def _exam_primary_branch(exam):
    return exam.exam_branches[0] if exam.exam_branches else None


def exam_has_papers(exam_id):
    return (
        db.session.query(ExamPaper.id)
        .filter(ExamPaper.exam_id == exam_id)
        .first()
        is not None
    )


def exam_has_marks(exam_id):
    return (
        db.session.query(StudentExamMark.id)
        .join(ExamPaper, StudentExamMark.exam_paper_id == ExamPaper.id)
        .filter(ExamPaper.exam_id == exam_id)
        .first()
        is not None
    )


def exam_edit_snapshot(exam):
    exam_branch = _exam_primary_branch(exam)
    branch = exam_branch.branch if exam_branch else None
    has_papers = exam_has_papers(exam.id)
    return {
        "id": exam.id,
        "name": exam.name,
        "year": exam.year,
        "term": exam.term,
        "branch_id": exam_branch.branch_id if exam_branch else None,
        "branch_name": branch.branch_name if branch else None,
        "is_locked": bool(exam.is_locked),
        "has_papers": has_papers,
        "has_marks": exam_has_marks(exam.id),
        "can_change_branch": not has_papers,
    }


def duplicate_exam_exists(name, year, term, branch_id, exclude_exam_id=None):
    query = (
        db.session.query(Exam.id)
        .join(ExamBranch)
        .filter(
            Exam.name == name,
            Exam.year == year,
            Exam.term == term,
            ExamBranch.branch_id == branch_id,
        )
    )
    if exclude_exam_id is not None:
        query = query.filter(Exam.id != exclude_exam_id)
    return query.first() is not None


def apply_exam_edits(exam, *, name, year, term, branch_id, user):
    """Mutate exam metadata in the current session. Does not commit.

    Returns {"ok", "unchanged", "error", "status", "changes"}.
    """
    name = (name or "").strip()
    try:
        year = int(year)
        branch_id = int(branch_id)
    except (TypeError, ValueError):
        return {
            "ok": False,
            "error": "Year and school are required.",
            "status": 400,
            "changes": [],
        }

    if term not in ("I", "II", "III"):
        return {
            "ok": False,
            "error": "Term is required.",
            "status": 400,
            "changes": [],
        }

    if len(name) < 3 or len(name) > 100:
        return {
            "ok": False,
            "error": "Exam name must be between 3 and 100 characters.",
            "status": 400,
            "changes": [],
        }

    exam_branch = _exam_primary_branch(exam)
    current_branch_id = exam_branch.branch_id if exam_branch else None

    if not getattr(user, "is_super_admin", False):
        branch_id = current_branch_id or getattr(user, "branch_id", None)
        try:
            branch_id = int(branch_id)
        except (TypeError, ValueError):
            return {
                "ok": False,
                "error": "This exam is not assigned to a school.",
                "status": 400,
                "changes": [],
            }

    if branch_id != current_branch_id:
        if exam_has_papers(exam.id):
            return {
                "ok": False,
                "error": (
                    "The school cannot be changed after exam papers or marks "
                    "have been created."
                ),
                "status": 409,
                "changes": [],
            }
        if not user_can_access_branch(branch_id):
            return {
                "ok": False,
                "error": "You cannot assign this exam to that school.",
                "status": 403,
                "changes": [],
            }
        if Branch.query.get(branch_id) is None:
            return {
                "ok": False,
                "error": "School not found.",
                "status": 400,
                "changes": [],
            }

    if duplicate_exam_exists(
        name, year, term, branch_id, exclude_exam_id=exam.id
    ):
        return {
            "ok": False,
            "error": (
                "An exam with the same name, year, term, and school already exists."
            ),
            "status": 409,
            "changes": [],
        }

    changes = []

    if name != exam.name:
        changes.append(
            {"field": "name", "label": "Name", "from": exam.name, "to": name}
        )
        exam.name = name

    if year != exam.year:
        changes.append(
            {
                "field": "year",
                "label": "Year",
                "from": str(exam.year),
                "to": str(year),
            }
        )
        exam.year = year

    if term != exam.term:
        changes.append(
            {
                "field": "term",
                "label": "Term",
                "from": f"Term {exam.term}",
                "to": f"Term {term}",
            }
        )
        exam.term = term

    if branch_id != current_branch_id:
        old_name = (
            exam_branch.branch.branch_name
            if exam_branch and exam_branch.branch
            else "—"
        )
        new_branch = Branch.query.get(branch_id)
        if exam_branch:
            exam_branch.branch_id = branch_id
        else:
            db.session.add(ExamBranch(exam_id=exam.id, branch_id=branch_id))
        changes.append(
            {
                "field": "branch",
                "label": "School",
                "from": old_name,
                "to": new_branch.branch_name,
            }
        )

    if not changes:
        return {"ok": True, "unchanged": True, "status": 200, "changes": []}

    return {"ok": True, "unchanged": False, "status": 200, "changes": changes}
