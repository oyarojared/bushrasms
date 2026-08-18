from ..bushra.modals.assessment_db import Exam, ExamPaper, StudentExamMark
from ..bushra.modals.branches_db import Branch, BranchClasses
from ..bushra.modals.students_db import Student, StudentSubjectAllocation
from ..bushra.modals.subjects_db import Subject, SubjectEligibility
from ..bushra.modules.admin.services.subs import auto_allocate_subjects


def _make_branch(db, name="Test School", code="TS001"):
    branch = Branch(
        branch_name=name,
        school_code=code,
        branch_manager="Manager",
        branch_level="secondary",
        school_gender="Co-ed",
        school_type="Day",
        email=f"{code.lower()}@example.com",
    )
    db.session.add(branch)
    db.session.flush()
    return branch


def _make_class(db, branch, grade_form, year="2026"):
    cls = BranchClasses(
        branch_id=branch.id,
        grade_form=grade_form,
        streams=["A"],
        class_year=year,
    )
    db.session.add(cls)
    db.session.flush()
    return cls


def _make_subject(db, name, code, grades):
    subject = Subject(
        name=name,
        code=code,
        category="Languages",
        is_examinable=True,
        is_compulsory=False,
    )
    db.session.add(subject)
    db.session.flush()
    for grade in grades:
        db.session.add(
            SubjectEligibility(subject_id=subject.id, grade_form=grade)
        )
    db.session.flush()
    return subject


def _make_student(db, branch, cls, admission_number=1):
    student = Student(
        branch_id=branch.id,
        class_id=cls.id,
        stream="A",
        admission_number=admission_number,
        fullname="Test Student",
    )
    db.session.add(student)
    db.session.flush()
    return student


def _allocated_names(student):
    return sorted(
        alloc.subject.name
        for alloc in student.subject_allocations
        if alloc.subject
    )


def test_non_form34_student_gets_all_class_subjects(db):
    branch = _make_branch(db)
    grade4 = _make_class(db, branch, "Grade 4")
    _make_subject(db, "English", "ENG", ["Grade 4"])
    _make_subject(db, "Mathematics", "MAT", ["Grade 4"])
    _make_subject(db, "Science", "SCI", ["Grade 4"])

    student = _make_student(db, branch, grade4)
    auto_allocate_subjects(student)
    db.session.commit()

    assert _allocated_names(student) == ["English", "Mathematics", "Science"]


def test_form3_student_gets_only_default_subjects(db):
    branch = _make_branch(db)
    form3 = _make_class(db, branch, "Form 3")
    _make_subject(db, "English", "101", ["Form 3", "Form 4"])
    _make_subject(db, "Kiswahili", "102", ["Form 3", "Form 4"])
    _make_subject(db, "Mathematics", "121", ["Form 3", "Form 4"])
    _make_subject(db, "Chemistry", "233", ["Form 3", "Form 4"])
    _make_subject(db, "Physics", "232", ["Form 3", "Form 4"])
    _make_subject(db, "Biology", "231", ["Form 3", "Form 4"])

    student = _make_student(db, branch, form3)
    auto_allocate_subjects(student)
    db.session.commit()

    assert _allocated_names(student) == [
        "Chemistry",
        "English",
        "Kiswahili",
        "Mathematics",
    ]


def test_move_to_unmatched_class_replaces_subjects_but_keeps_exam_marks(db):
    branch = _make_branch(db)
    grade4 = _make_class(db, branch, "Grade 4")
    form3 = _make_class(db, branch, "Form 3")

    english = _make_subject(db, "English", "101", ["Grade 4", "Form 3"])
    science = _make_subject(db, "Science", "SCI", ["Grade 4"])
    _make_subject(db, "Kiswahili", "102", ["Form 3"])
    _make_subject(db, "Mathematics", "121", ["Grade 4", "Form 3"])
    _make_subject(db, "Chemistry", "233", ["Form 3"])
    _make_subject(db, "Physics", "232", ["Form 3"])

    student = _make_student(db, branch, grade4)
    auto_allocate_subjects(student)
    db.session.flush()

    exam = Exam(name="Term 1", year=2026, term="I")
    db.session.add(exam)
    db.session.flush()

    paper = ExamPaper(
        exam_id=exam.id,
        branch_id=branch.id,
        class_id=grade4.id,
        stream="A",
        subject_id=science.id,
        marks_out_of=100,
    )
    db.session.add(paper)
    db.session.flush()

    mark = StudentExamMark(
        exam_paper_id=paper.id,
        student_id=student.id,
        marks=72,
    )
    db.session.add(mark)
    db.session.flush()

    previous_grade = student.class_info.grade_form
    student.class_id = form3.id
    db.session.flush()
    db.session.expire(student, ["class_info"])

    auto_allocate_subjects(student, previous_grade_form=previous_grade)
    db.session.commit()

    assert _allocated_names(student) == [
        "Chemistry",
        "English",
        "Kiswahili",
        "Mathematics",
    ]
    assert science.id not in {
        alloc.subject_id for alloc in student.subject_allocations
    }
    assert english.id in {
        alloc.subject_id for alloc in student.subject_allocations
    }

    preserved = StudentExamMark.query.filter_by(
        student_id=student.id,
        exam_paper_id=paper.id,
    ).one()
    assert preserved.marks == 72
    assert paper.subject_id == science.id
    assert paper.class_id == grade4.id


def test_move_to_matching_class_keeps_existing_allocations(db):
    branch = _make_branch(db)
    form3 = _make_class(db, branch, "Form 3")
    form4 = _make_class(db, branch, "Form 4")

    _make_subject(db, "English", "101", ["Form 3", "Form 4"])
    _make_subject(db, "Kiswahili", "102", ["Form 3", "Form 4"])
    _make_subject(db, "Mathematics", "121", ["Form 3", "Form 4"])
    _make_subject(db, "Chemistry", "233", ["Form 3", "Form 4"])
    physics = _make_subject(db, "Physics", "232", ["Form 3", "Form 4"])

    student = _make_student(db, branch, form3)
    auto_allocate_subjects(student)
    db.session.add(
        StudentSubjectAllocation(student_id=student.id, subject_id=physics.id)
    )
    db.session.flush()

    previous_grade = student.class_info.grade_form
    student.class_id = form4.id
    db.session.flush()
    db.session.expire(student, ["class_info"])

    auto_allocate_subjects(student, previous_grade_form=previous_grade)
    db.session.commit()

    names = _allocated_names(student)
    assert "Physics" in names
    assert "English" in names
    assert "Chemistry" in names


def test_auto_allocate_ignores_subjects_not_eligible_for_class(db):
    branch = _make_branch(db)
    form3 = _make_class(db, branch, "Form 3")
    _make_subject(db, "English", "101", ["Form 3"])
    _make_subject(db, "Chemistry", "233", ["Form 2"])

    student = _make_student(db, branch, form3)
    auto_allocate_subjects(student)
    db.session.commit()

    assert _allocated_names(student) == ["English"]
