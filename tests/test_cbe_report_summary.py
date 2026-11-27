from datetime import date
from types import SimpleNamespace

from flask import render_template

from ..bushra.modals.assessment_db import Exam, ExamPaper, StudentExamMark
from ..bushra.modals.branches_db import Branch, BranchClasses
from ..bushra.modals.students_db import Student
from ..bushra.modals.subjects_db import Subject, SubjectEligibility
from ..bushra.modules.admin.services.report import (
    _change_label,
    _previous_mark_label,
    previous_cbe_subject_marks,
    recent_cbe_exam_summaries,
)


def _branch(db):
    branch = Branch(
        branch_name="CBC School",
        school_code="CB001",
        branch_manager="Head",
        branch_level="Primary",
        school_gender="Co-ed",
        school_type="Day",
        email="cb001@example.com",
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


def _student(db, branch, school_class):
    student = Student(
        fullname="Amina Otieno",
        admission_number=10,
        branch_id=branch.id,
        class_id=school_class.id,
        stream="A",
        current_year=2026,
        gender="Female",
        date_of_admission=date(2026, 1, 10),
    )
    db.session.add(student)
    db.session.flush()
    return student


def _sitting(
    db, branch, school_class, student, subject, name, year, term, marks, marks_out_of=100
):
    exam = Exam(name=name, year=year, term=term)
    db.session.add(exam)
    db.session.flush()
    paper = ExamPaper(
        exam_id=exam.id,
        branch_id=branch.id,
        class_id=school_class.id,
        stream="A",
        subject_id=subject.id,
        marks_out_of=marks_out_of,
    )
    db.session.add(paper)
    db.session.flush()
    db.session.add(
        StudentExamMark(exam_paper_id=paper.id, student_id=student.id, marks=marks)
    )
    db.session.flush()
    return exam


def test_recent_results_keep_three_cbe_exams_ending_at_the_current_one(db):
    branch = _branch(db)
    grade = _class(db, branch, "Grade 6")
    form4 = _class(db, branch, "Form 4")
    student = _student(db, branch, grade)
    subject = Subject(
        name="Science",
        code="SCI",
        category="Sciences",
        is_examinable=True,
        is_compulsory=True,
    )
    db.session.add(subject)
    db.session.flush()
    db.session.add(SubjectEligibility(subject_id=subject.id, grade_form="Grade 6"))
    db.session.flush()

    _sitting(db, branch, grade, student, subject, "CAT", 2025, "III", 50)
    _sitting(db, branch, grade, student, subject, "Opener", 2026, "I", 60)
    _sitting(db, branch, grade, student, subject, "Mid Term", 2026, "II", 70)
    current = _sitting(db, branch, grade, student, subject, "End Term", 2026, "III", 80)
    _sitting(db, branch, grade, student, subject, "Next Opener", 2027, "I", 90)
    _sitting(db, branch, form4, student, subject, "Form Paper", 2026, "I", 40)
    db.session.commit()

    summary = recent_cbe_exam_summaries([student.id], current.id)

    rows = summary[student.id]
    assert [row["name"] for row in rows] == ["Opener", "Mid Term", "End Term"]
    assert rows[-1]["is_current"] is True
    assert [row["mean"] for row in rows] == [60, 70, 80]
    assert "CAT" not in [row["name"] for row in rows]
    assert "Form Paper" not in [row["name"] for row in rows]
    assert "Next Opener" not in [row["name"] for row in rows]


def test_previous_subject_column_uses_the_cbe_exam_just_before_this_one(db):
    branch = _branch(db)
    grade = _class(db, branch, "Grade 6")
    earlier = _class(db, branch, "Grade 5")
    form4 = _class(db, branch, "Form 4")
    student = _student(db, branch, grade)
    science = Subject(
        name="Science",
        code="SCI",
        category="Sciences",
        is_examinable=True,
        is_compulsory=True,
    )
    maths = Subject(
        name="Mathematics",
        code="MAT",
        category="Sciences",
        is_examinable=True,
        is_compulsory=True,
    )
    db.session.add_all([science, maths])
    db.session.flush()

    _sitting(db, branch, grade, student, science, "Opener", 2026, "I", 50)
    _sitting(
        db, branch, earlier, student, science, "Mid Term", 2026, "II", 18, marks_out_of=20
    )
    _sitting(db, branch, form4, student, science, "Form Paper", 2026, "II", 90)
    current = _sitting(db, branch, grade, student, science, "End Term", 2026, "III", 80)
    _sitting(db, branch, grade, student, maths, "End Term Maths", 2026, "III", 70)
    db.session.commit()

    prior = previous_cbe_subject_marks([student.id], current.id)

    assert prior[student.id]["name"] == "Mid Term"
    assert prior[student.id]["subjects"][science.id]["label"] == "18/20"
    assert prior[student.id]["subjects"][science.id]["percent"] == 90
    assert prior[student.id]["marks"] == 18
    assert prior[student.id]["out_of"] == 20
    assert maths.id not in prior[student.id]["subjects"]
    assert "grade" in prior[student.id]


def test_previous_mark_always_shows_what_the_paper_was_out_of():
    assert _previous_mark_label(72, 100) == "72/100"
    assert _previous_mark_label(45, 60) == "45/60"
    assert _previous_mark_label(18, 20) == "18/20"


def test_change_is_the_difference_in_percentage_points():
    assert _change_label(78, 100, 75) == "+3"
    assert _change_label(72, 100, 75) == "-3"
    assert _change_label(80, 100, 90) == "-10"
    assert _change_label(70, 100, 70) == "0"
    assert _change_label(None, 100, 70) is None


def test_report_card_puts_recent_results_beside_the_grading_key(app):
    data = {
        "branch": {
            "name": "CBC School",
            "logo": None,
            "motto": None,
            "email": "a@b.c",
            "class_name": "Grade 6",
        },
        "exam": {"name": "End Term", "term": "III", "year": 2026},
        "max_points": 4,
        "grading_boundaries": [
            SimpleNamespace(
                min_score=0,
                max_score=100,
                performance_level="ME",
                points=3,
                descriptor="Meets expectation",
            )
        ],
        "students": [
            {
                "fullname": "AMINA OTIENO",
                "admission_number": 10,
                "assessment_no": None,
                "gender": "Female",
                "stream": "A",
                "pathway": None,
                "passport_path": "",
                "class_teacher": "Ms A",
                "overall_position": 1,
                "class_total": 1,
                "stream_position": 1,
                "stream_total": 1,
                "previous_exam_name": "Mid Term",
                "previous_exam_grade": "ME",
                "previous_exam_marks": 18,
                "previous_exam_out_of": 20,
                "subjects": [
                    {
                        "subject_code": "SCI",
                        "subject_name": "Science",
                        "marks": 80,
                        "marks_out_of": 100,
                        "previous_mark": "18/20",
                        "change": "-10",
                        "performance_level": "ME",
                        "points": 3,
                        "descriptor": "Meets expectation",
                        "teacher_initials": "A.B",
                    }
                ],
                "recent_exams": [
                    {
                        "name": "Opener",
                        "term": "I",
                        "year": 2026,
                        "mean": 60,
                        "grade": "ME",
                        "is_current": False,
                    },
                    {
                        "name": "End Term",
                        "term": "III",
                        "year": 2026,
                        "mean": 80,
                        "grade": "ME",
                        "is_current": True,
                    },
                ],
            }
        ],
    }
    with app.app_context():
        html = render_template(
            "academics/report_card.html",
            data=data,
            school=SimpleNamespace(school_code="CB001"),
            include_ranking=True,
            opening_date=None,
        )

    row_at = html.index('class="rc-key-row"')
    recent_at = html.index("Recent results")
    key_at = html.index("Grading Key")
    assert row_at < recent_at < key_at
    assert "Opener" in html
    assert "I 26" in html
    assert "exam-summary-current" in html
    assert "CB001 · a@b.c" in html
    assert "End Term · Term III 2026" in html
    info = html[html.index('class="school-info"'):html.index('class="student-passport"')]
    assert info.index("school-name") < info.index("report-title") < info.index("report-sitting") < info.index("school-quiet")
    assert "Term:" not in html
    assert "text-primary" not in html
    header = html[html.index('class="marks-table"'):html.index("</thead>")]
    assert header.index("Mid Term") < header.index("Change") < header.index(">Marks<")
    assert 'class="prev-out">/20</span>' in html
    assert "marks-focus" in html
    assert 'class="out-of">/100</span>' in html
    assert "<td>—</td>" not in html
    assert "mark-down" in html
    assert "-10" in html
    assert 'class="prev-total">18<span class="prev-out">/20</span>' in html
    assert "prev-grade" in html
    total_row = html[html.index('class="total-row"'):]
    assert "mark-down" in total_row
    assert "-10" in total_row
    assert "<small>Grade</small>" in html
    assert "Overall Perf" not in html


def test_one_mark_drop_on_the_same_total_is_not_rounded_to_zero(app):
    data = {
        "branch": {
            "name": "CBC School",
            "logo": None,
            "motto": None,
            "email": "a@b.c",
            "class_name": "Grade 6",
        },
        "exam": {"name": "End Term", "term": "III", "year": 2026},
        "max_points": 4,
        "grading_boundaries": [],
        "students": [
            {
                "fullname": "AMINA OTIENO",
                "admission_number": 10,
                "assessment_no": None,
                "gender": "Female",
                "stream": "A",
                "pathway": None,
                "passport_path": "",
                "class_teacher": "Ms A",
                "overall_position": 1,
                "class_total": 1,
                "stream_position": 1,
                "stream_total": 1,
                "previous_exam_name": "Mid Term",
                "previous_exam_grade": "EE",
                "previous_exam_marks": 484,
                "previous_exam_out_of": 500,
                "subjects": [
                    {
                        "subject_code": "ENG",
                        "subject_name": "English",
                        "marks": 483,
                        "marks_out_of": 500,
                        "previous_mark": "484/500",
                        "change": "0",
                        "performance_level": "EE",
                        "points": 4,
                        "descriptor": "Exceeds expectation",
                        "teacher_initials": "A.B",
                    }
                ],
                "recent_exams": [],
            }
        ],
    }
    with app.app_context():
        html = render_template(
            "academics/report_card.html",
            data=data,
            school=SimpleNamespace(school_code="CB001"),
            include_ranking=False,
            opening_date=None,
        )

    total_row = html[html.index('class="total-row"'):]
    assert ">-1<" in total_row
    assert "mark-down" in total_row
