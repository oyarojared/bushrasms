from ....modals.subjects_db import Subject, SubjectEligibility
from ....modals import db
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from flask import current_app
from datetime import datetime
from ....modals.subjects_db import Subject, SubjectEligibility, Lesson
from ....modals.students_db import Student, StudentSubjectAllocation
from ....modals.staff_db import Teacher
from ....modals.branches_db import BranchClasses
from ....modals.assessment_db import ExamPaper, StudentExamMark


from sqlalchemy import func


FORM_3_4_DEFAULT_SUBJECTS = frozenset(
    ("english", "kiswahili", "mathematics", "chemistry")
)

FORM_3_4_SUBJECT_ALIASES = {
    "english": "english",
    "english language": "english",
    "kiswahili": "kiswahili",
    "kiswahili language": "kiswahili",
    "swahili": "kiswahili",
    "mathematics": "mathematics",
    "maths": "mathematics",
    "math": "mathematics",
    "chemistry": "chemistry",
    "chem": "chemistry",
}


def get_subjects():
    try:
        subjects = (
            Subject.query
            .order_by(Subject.created_at.desc())
            .all()
        )

        return subjects, None

    except SQLAlchemyError as e:
        current_app.logger.exception(
            "Database error while fetching subjects"
        )
        return [], "Database error occurred"

    except Exception as e:
        current_app.logger.exception(
            "Unexpected error while fetching subjects"
        )
        return [], "Unexpected system error! The admin has been notified."



def delete_subject_service(subject_id):
    subject = Subject.query.get(subject_id)

    if not subject:
        return False, "Subject not found"

    try:
        # 1️⃣ Get exam papers
        papers = ExamPaper.query.filter_by(subject_id=subject_id).all()
        paper_ids = [p.id for p in papers]

        # 2️⃣ Get marks
        marks = StudentExamMark.query.filter(
            StudentExamMark.exam_paper_id.in_(paper_ids)
        ).all()

        current_app.logger.info(
            f"[SUBJECT_DELETE] subject_id={subject_id} | "
            f"papers={len(papers)} | marks={len(marks)}"
        )

        # 3️⃣ Delete marks first
        for m in marks:
            db.session.delete(m)

        # 4️⃣ Delete exam papers
        for p in papers:
            db.session.delete(p)

        # 5️⃣ Delete lessons (your existing logic)
        lessons = Lesson.query.filter_by(subject_id=subject_id).all()
        for l in lessons:
            db.session.delete(l)

        # 6️⃣ Delete subject
        db.session.delete(subject)

        db.session.commit()
        return True, None

    except Exception as e:
        db.session.rollback()

        current_app.logger.exception(
            f"[ERR_SUBJECT_DELETE_002] subject_id={subject_id} | error={str(e)}"
        )

        return False, "Delete failed"

def add_subject(form, selected_grades):
    # Expect form validated data
    if not selected_grades:
        return False, "NO_GRADES"

    try:
        subject = Subject(
            name=form.name.data.strip().capitalize(),
            code=form.code.data,
            category=form.category.data,
            is_examinable=form.is_examinable.data,
            is_compulsory=form.is_compulsory.data,
        )

        db.session.add(subject)
        db.session.flush()

        for grade in selected_grades:
            eligibility = SubjectEligibility(
                subject_id=subject.id,
                grade_form=grade
            )
            db.session.add(eligibility)   

        db.session.commit()
        return True, None

    except IntegrityError:
        db.session.rollback()
        current_app.logger.exception(
            "Integrity error while adding subject"
        )
        return False, "DUPLICATE"

    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception(
            "Database error while adding subject"
        )
        return False, "DB_ERROR"

    except Exception:
        db.session.rollback()
        current_app.logger.exception(
            "Unexpected error while adding subject"
        )
        return False, "SYSTEM_ERROR"


def remove_subject_from_grade(grade_form, subject_id):
    """
    Removes subject eligibility AND all student allocations
    for students belonging to the given grade.
    """

    # 1️⃣ Remove eligibility
    SubjectEligibility.query.filter_by(
        subject_id=subject_id,
        grade_form=grade_form
    ).delete(synchronize_session=False) 

    # 2️⃣ Subquery: students in this grade
    student_ids_subq = (
        db.session.query(Student.id)
        .join(BranchClasses, Student.class_id == BranchClasses.id)
        .filter(BranchClasses.grade_form == grade_form)
        .subquery()
    )

    # 3️⃣ Delete allocations safely (NO JOIN here)
    StudentSubjectAllocation.query.filter(
        StudentSubjectAllocation.subject_id == subject_id,
        StudentSubjectAllocation.student_id.in_(student_ids_subq)
    ).delete(synchronize_session=False)

    db.session.commit()


def update_subject_service(subject_id, form, selected_grades):
    subject = Subject.query.get(subject_id)

    if not subject:
        return None, "Invalid subject."

    try:
        # 1️⃣ Update subject fields
        subject.name = form.name.data.strip()
        subject.code = form.code.data
        subject.category = form.category.data
        subject.is_examinable = form.is_examinable.data
        subject.is_compulsory = form.is_compulsory.data
        subject.updated_at = datetime.utcnow()

        # 2️⃣ Current eligibility
        existing = SubjectEligibility.query.filter_by(
            subject_id=subject.id
        ).all()
        

        existing_grades = {e.grade_form for e in existing}
        new_grades = set(selected_grades)

        removed_grades = existing_grades - new_grades
        added_grades = new_grades - existing_grades 

        # 3️⃣ Remove only what was removed
        for grade in removed_grades:
            remove_subject_from_grade(
                grade_form=grade,
                subject_id=subject.id
            )

        # 4️⃣ Add only what is new
        for grade in added_grades:
            db.session.add(
                SubjectEligibility(
                    subject_id=subject.id,
                    grade_form=grade
                )
            )

        db.session.commit()
        return subject, "Subject updated successfully."

    except IntegrityError:
        db.session.rollback()
        return None, "Duplicate subject eligibility detected."

    except Exception:
        db.session.rollback()
        return None, "Failed to update subject."



def get_subjects_by_grade(grade_form):
    if not grade_form:
        return []

    return (
        Subject.query
        .join(SubjectEligibility)
        .filter(
            func.lower(SubjectEligibility.grade_form)
            == func.lower(grade_form)
        )
        .order_by(Subject.name.asc())
        .all()
    )


def _normalize_subject_name(name):
    if not name:
        return ""
    return " ".join(str(name).strip().lower().split())


def _is_form_3_or_4(grade_form):
    if not grade_form:
        return False
    name = str(grade_form).strip().lower()
    if "form" not in name:
        return False
    number = "".join(ch for ch in name if ch.isdigit())
    return number in ("3", "4")


def _canonical_form34_subject(name):
    normalized = _normalize_subject_name(name)
    if normalized in FORM_3_4_DEFAULT_SUBJECTS:
        return normalized
    return FORM_3_4_SUBJECT_ALIASES.get(normalized)


def _form34_default_subjects(eligible_subjects):
    """
    Pick at most one eligible subject per default Form 3/4 learning area.
    Exact names win over aliases if both exist.
    """
    selected = {}

    for subject in eligible_subjects:
        canonical = _canonical_form34_subject(subject.name)
        if not canonical:
            continue

        current = selected.get(canonical)
        if current is None or _normalize_subject_name(subject.name) == canonical:
            selected[canonical] = subject

    return list(selected.values())


def _compulsory_subjects_for_grade(grade_form):
    if not grade_form:
        return []

    return (
        Subject.query
        .join(SubjectEligibility)
        .filter(
            func.lower(SubjectEligibility.grade_form) == func.lower(grade_form),
            Subject.is_compulsory.is_(True),
        )
        .order_by(Subject.name.asc())
        .all()
    )


def get_subjects_offered_in_class(class_obj):
    """
    Subjects actually taught in this school class, not every school
    with the same grade name.

    If no teachers have been assigned yet, falls back to compulsory
    subjects eligible for that grade.
    """
    if not class_obj:
        return []

    lesson_ids = {
        subject_id
        for (subject_id,) in db.session.query(Lesson.subject_id)
        .filter(
            Lesson.branch_id == class_obj.branch_id,
            Lesson.class_id == class_obj.id,
        )
        .distinct()
        .all()
        if subject_id
    }

    if lesson_ids:
        return (
            Subject.query.filter(Subject.id.in_(lesson_ids))
            .order_by(Subject.name.asc())
            .all()
        )

    return _compulsory_subjects_for_grade(class_obj.grade_form)


def default_subjects_for_class(class_obj):
    """
    Subjects assigned automatically for a specific school class.

    Form 3 and Form 4: English, Kiswahili, Mathematics, Chemistry.
    Other classes: subjects taught in that school class.
    """
    if not class_obj:
        return []

    if _is_form_3_or_4(class_obj.grade_form):
        return _form34_default_subjects(
            get_subjects_by_grade(class_obj.grade_form)
        )

    return get_subjects_offered_in_class(class_obj)


def _subject_id_set(subjects):
    return {subject.id for subject in subjects}


def auto_allocate_subjects(student, previous_class_id=None):
    """
    Allocate the default subjects for the student's current school class.

    If the student moved from a class whose offered subjects differ,
    previous allocations are replaced. Exam papers and marks are not touched.
    Does not commit; the caller owns the transaction.
    """
    if not student or not getattr(student, "id", None) or not student.class_info:
        return

    new_class = student.class_info
    previous_class = (
        BranchClasses.query.get(previous_class_id) if previous_class_id else None
    )

    desired_subjects = default_subjects_for_class(new_class)
    desired_ids = _subject_id_set(desired_subjects)

    should_replace = False
    if previous_class:
        previous_ids = _subject_id_set(default_subjects_for_class(previous_class))
        should_replace = previous_ids != desired_ids

    if should_replace:
        for alloc in list(student.subject_allocations):
            if alloc.subject_id not in desired_ids:
                student.subject_allocations.remove(alloc)

    existing_subject_ids = {
        alloc.subject_id for alloc in student.subject_allocations
    }

    new_allocations = []
    for subject in desired_subjects:
        if subject.id in existing_subject_ids:
            continue
        new_allocations.append(
            StudentSubjectAllocation(
                student_id=student.id,
                subject_id=subject.id,
            )
        )

    if new_allocations:
        db.session.add_all(new_allocations)

    current_app.logger.info(
        "[AUTO-ALLOC] student_id=%s class_id=%s grade=%s replaced=%s assigned=%s",
        student.id,
        new_class.id,
        new_class.grade_form,
        should_replace,
        len(new_allocations),
    )