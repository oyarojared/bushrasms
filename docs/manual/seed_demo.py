"""Build an isolated demo database for user-manual screenshots.

Does not touch app.db. Run from the repo root:
  .venv\\Scripts\\python.exe docs\\manual\\seed_demo.py
"""
from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEMO_DB = ROOT / "docs" / "manual_demo.db"
os.environ["DATABASE_URL"] = "sqlite:///" + str(DEMO_DB).replace("\\", "/")

from bushra import create_app  # noqa: E402
from bushra.modals import db  # noqa: E402
from bushra.modals.assessment_db import (  # noqa: E402
    Exam,
    ExamBranch,
    ExamPaper,
    GradeGradingScheme,
    GradingBoundary,
    GradingScheme,
    GradingSystem,
    StudentExamMark,
)
from bushra.modals.branches_db import Branch, BranchClasses  # noqa: E402
from bushra.modals.staff_db import ClassTeacher, SuperAdminBranch, Teacher  # noqa: E402
from bushra.modals.students_db import Student, StudentSubjectAllocation  # noqa: E402
from bushra.modals.subjects_db import Lesson, Subject, SubjectEligibility  # noqa: E402
from bushra.modules.admin.utils.teacher_utils import hash_staff_password  # noqa: E402

PASSWORD = "DemoPass12"


def make_teacher(branch, *, fullname, phone, username, title="Mr.", gender="M", **flags):
    teacher = Teacher(
        branch_id=branch.id,
        employer="TSC",
        fullname=fullname,
        gender=gender,
        title=title,
        phone=phone,
        username=username,
        password_hash=hash_staff_password(PASSWORD),
        email=f"{username}@riverside.example",
        **flags,
    )
    db.session.add(teacher)
    db.session.flush()
    return teacher


def main():
    if DEMO_DB.exists():
        DEMO_DB.unlink()

    app = create_app()
    with app.app_context():
        db.create_all()

        riverside = Branch(
            branch_name="Riverside Junior School",
            school_code="RJS001",
            branch_manager="Joyce Wanjiku",
            branch_level="Junior Secondary",
            school_gender="Co-ed",
            school_type="Day",
            email="office@riverside.example",
            motto="Learn, serve, lead",
        )
        hilltop = Branch(
            branch_name="Hilltop Primary School",
            school_code="HPS002",
            branch_manager="Peter Otieno",
            branch_level="Primary",
            school_gender="Co-ed",
            school_type="Day",
            email="office@hilltop.example",
            motto="Every child can shine",
        )
        db.session.add_all([riverside, hilltop])
        db.session.flush()

        grade7 = BranchClasses(
            branch_id=riverside.id,
            class_year="2026",
            grade_form="Grade 7",
            streams=["A", "B"],
        )
        grade8 = BranchClasses(
            branch_id=riverside.id,
            class_year="2026",
            grade_form="Grade 8",
            streams=["A"],
        )
        grade4 = BranchClasses(
            branch_id=hilltop.id,
            class_year="2026",
            grade_form="Grade 4",
            streams=["A"],
        )
        db.session.add_all([grade7, grade8, grade4])
        db.session.flush()

        subjects = []
        catalog = [
            ("English", "ENG", "Languages"),
            ("Kiswahili", "KIS", "Languages"),
            ("Mathematics", "MAT", "Sciences"),
            ("Integrated Science", "ISC", "Sciences"),
            ("Social Studies", "SST", "Humanities"),
        ]
        for name, code, category in catalog:
            subject = Subject(
                name=name,
                code=code,
                category=category,
                is_examinable=True,
                is_compulsory=True,
            )
            db.session.add(subject)
            db.session.flush()
            for grade_name in ("Grade 7", "Grade 8"):
                db.session.add(
                    SubjectEligibility(subject_id=subject.id, grade_form=grade_name)
                )
            subjects.append(subject)

        sysadmin = make_teacher(
            riverside,
            fullname="System Owner",
            phone="0711000001",
            username="sysadmin",
            is_admin=True,
            is_super_admin=True,
            is_system_admin=True,
        )
        super_admin = make_teacher(
            riverside,
            fullname="Mercy Chebet",
            phone="0711000002",
            username="mchebet",
            title="Mrs.",
            gender="F",
            is_admin=True,
            is_super_admin=True,
        )
        db.session.add(
            SuperAdminBranch(teacher_id=super_admin.id, branch_id=riverside.id)
        )
        school_admin = make_teacher(
            riverside,
            fullname="Daniel Kariuki",
            phone="0711000003",
            username="dkariuki",
            is_admin=True,
        )
        class_teacher = make_teacher(
            riverside,
            fullname="Jane Mwangi",
            phone="0711000004",
            username="jmwangi",
            title="Mrs.",
            gender="F",
        )
        subject_teacher = make_teacher(
            riverside,
            fullname="Amos Kemboi",
            phone="0711000005",
            username="akemboi",
        )
        riverside.branch_head = str(school_admin.id)

        db.session.add(
            ClassTeacher(
                branch_id=riverside.id,
                class_id=grade7.id,
                stream="A",
                teacher_id=class_teacher.id,
            )
        )
        db.session.add(
            Lesson(
                branch_id=riverside.id,
                class_id=grade7.id,
                stream="A",
                subject_id=subjects[0].id,
                teacher_id=class_teacher.id,
            )
        )
        db.session.add(
            Lesson(
                branch_id=riverside.id,
                class_id=grade7.id,
                stream="A",
                subject_id=subjects[2].id,
                teacher_id=subject_teacher.id,
            )
        )

        learners = [
            ("Amina Hassan", "F", "A", 1),
            ("Brian Odhiambo", "M", "A", 2),
            ("Cynthia Njeri", "F", "A", 3),
            ("David Kiprono", "M", "A", 4),
            ("Faith Wambui", "F", "B", 5),
        ]
        student_rows = []
        for name, gender, stream, adm in learners:
            student = Student(
                branch_id=riverside.id,
                class_id=grade7.id,
                stream=stream,
                admission_number=adm,
                fullname=name,
                gender="Female" if gender == "F" else "Male",
                dob=date(2013, 3, adm),
                parent_fullname=f"Parent of {name.split()[0]}",
                parent_phone=f"072200000{adm}",
                boarding_status="Day",
            )
            db.session.add(student)
            db.session.flush()
            student_rows.append(student)
            for subject in subjects:
                db.session.add(
                    StudentSubjectAllocation(
                        student_id=student.id, subject_id=subject.id
                    )
                )

        cbc = GradingSystem(name="CBC", description="Competency based assessment")
        db.session.add(cbc)
        db.session.flush()
        scheme = GradingScheme(system_id=cbc.id, name="Junior school 8-point", is_active=True)
        db.session.add(scheme)
        db.session.flush()
        bands = [
            (90, 100, "EE1", 8, "Exceeding Expectation 1"),
            (75, 89, "EE2", 7, "Exceeding Expectation 2"),
            (58, 74, "ME1", 6, "Meeting Expectation 1"),
            (41, 57, "ME2", 5, "Meeting Expectation 2"),
            (21, 40, "AE", 4, "Approaching Expectation"),
            (0, 20, "BE", 3, "Below Expectation"),
        ]
        for lo, hi, level, points, descriptor in bands:
            db.session.add(
                GradingBoundary(
                    scheme_id=scheme.id,
                    min_score=lo,
                    max_score=hi,
                    performance_level=level,
                    points=points,
                    descriptor=descriptor,
                )
            )
        db.session.add(GradeGradingScheme(grade_id=grade7.id, scheme_id=scheme.id))
        db.session.add(GradeGradingScheme(grade_id=grade8.id, scheme_id=scheme.id))

        exam = Exam(name="Mid Term Assessment", year=2026, term="II", is_locked=False)
        db.session.add(exam)
        db.session.flush()
        db.session.add(ExamBranch(exam_id=exam.id, branch_id=riverside.id))

        papers = []
        for subject in subjects:
            paper = ExamPaper(
                exam_id=exam.id,
                branch_id=riverside.id,
                class_id=grade7.id,
                stream="A",
                subject_id=subject.id,
                marks_out_of=100,
            )
            db.session.add(paper)
            db.session.flush()
            papers.append(paper)

        sample_marks = {
            "Amina Hassan": [78, 72, 81, 69, 74],
            "Brian Odhiambo": [64, 58, 71, 60, 55],
            "Cynthia Njeri": [88, 84, 91, 79, 82],
            "David Kiprono": [45, 51, 48, 53, 40],
        }
        for student in student_rows:
            scores = sample_marks.get(student.fullname)
            if not scores:
                continue
            for paper, score in zip(papers, scores):
                db.session.add(
                    StudentExamMark(
                        exam_paper_id=paper.id,
                        student_id=student.id,
                        marks=score,
                    )
                )

        db.session.commit()
        print(f"Demo database: {DEMO_DB}")
        print("Sign-in password for every demo account:", PASSWORD)
        print("sysadmin / mchebet / dkariuki / jmwangi / akemboi")


if __name__ == "__main__":
    main()
