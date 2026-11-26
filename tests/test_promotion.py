from datetime import date

from ..bushra.modals.assessment_db import Exam, ExamPaper, StudentExamMark
from ..bushra.modals.branches_db import Branch, BranchClasses
from ..bushra.modals.staff_db import SuperAdminBranch, Teacher
from ..bushra.modals.students_db import Student, StudentEnrollment, StudentSubjectAllocation
from ..bushra.modals.subjects_db import Subject, SubjectEligibility
from ..bushra.modules.admin.routes.students import serialize_students
from ..bushra.modules.admin.services.leaving_certificate import is_leaving_certificate_eligible
from ..bushra.modules.admin.services.promotion import (
    ENROLLMENT_ACTIVE,
    ENROLLMENT_COMPLETED,
    ENROLLMENT_REPEATING,
    PromotionError,
    apply_promotion,
    build_plan,
    class_roster,
    continuation_targets,
    cohort_for_exam,
    live_students_query,
    next_grade_name,
    placement_year_for_new_student,
    sync_current_enrollment,
)
from ..bushra.modules.admin.services.report import (
    build_broadsheet_data,
    load_class_students_for_report,
)
from ..bushra.modules.admin.utils.teacher_utils import hash_staff_password

import pytest


def _branch(db, name="Hill School", code="HS001"):
    branch = Branch(
        branch_name=name,
        school_code=code,
        branch_manager="Head",
        branch_level="Mixed",
        school_gender="Co-ed",
        school_type="Day",
        email=f"{code.lower()}@example.com",
    )
    db.session.add(branch)
    db.session.flush()
    return branch


def _class(db, branch, grade_form, streams=None):
    school_class = BranchClasses(
        branch_id=branch.id,
        grade_form=grade_form,
        streams=streams if streams is not None else ["A"],
        class_year="2026",
    )
    db.session.add(school_class)
    db.session.flush()
    return school_class


def _student(db, branch, school_class, fullname, admission_number, stream="A", year=2026):
    student = Student(
        fullname=fullname,
        admission_number=admission_number,
        branch_id=branch.id,
        class_id=school_class.id,
        stream=stream,
        current_year=year,
        gender="Female",
        date_of_admission=date(year, 1, 10),
    )
    db.session.add(student)
    db.session.flush()
    return student


def _subject(db, name, code):
    subject = Subject(
        name=name,
        code=code,
        category="Sciences",
        is_examinable=True,
        is_compulsory=True,
    )
    db.session.add(subject)
    db.session.flush()
    db.session.add(SubjectEligibility(subject_id=subject.id, grade_form="Grade 2"))
    db.session.flush()
    return subject


def _mark(db, branch, school_class, student, subject, year=2026, stream="A", marks=72):
    exam = Exam(name="End Term", year=year, term="I")
    db.session.add(exam)
    db.session.flush()
    paper = ExamPaper(
        exam_id=exam.id,
        branch_id=branch.id,
        class_id=school_class.id,
        stream=stream,
        subject_id=subject.id,
        marks_out_of=100,
    )
    db.session.add(paper)
    db.session.flush()
    db.session.add(
        StudentExamMark(exam_paper_id=paper.id, student_id=student.id, marks=marks)
    )
    db.session.flush()
    return exam, paper


def _enrollment(student, year):
    return StudentEnrollment.query.filter_by(student_id=student.id, year=year).one()


def test_next_grade_names():
    assert next_grade_name("Grade 2") == "Grade 3"
    assert next_grade_name("PP2") == "Grade 1"
    assert next_grade_name("Form 3") == "Form 4"
    assert next_grade_name("Form 4") is None
    assert next_grade_name("Grade 12") is None
    assert next_grade_name("IGCSE") is None


def test_grade_2_moves_and_keeps_the_old_year(db):
    branch = _branch(db)
    grade2 = _class(db, branch, "Grade 2")
    grade3 = _class(db, branch, "Grade 3")
    amina = _student(db, branch, grade2, "Amina Otieno", 10)
    subject = _subject(db, "Science", "SCI")
    exam, paper = _mark(db, branch, grade2, amina, subject)
    db.session.commit()

    plan = apply_promotion(branch.id, 2026, 2027)

    assert plan["counts"]["move"] == 1
    db.session.refresh(amina)
    assert amina.class_id == grade3.id
    assert amina.current_year == 2027
    assert amina.enrollment_status == ENROLLMENT_ACTIVE

    old = _enrollment(amina, 2026)
    assert old.class_id == grade2.id
    assert old.status == ENROLLMENT_ACTIVE
    new = _enrollment(amina, 2027)
    assert new.class_id == grade3.id

    saved, year = class_roster(branch.id, grade2.id, year=2026)
    assert year == 2026
    assert [learner.id for learner in saved] == [amina.id]
    live_grade2 = live_students_query(branch.id, grade2.id).all()
    assert live_grade2 == []
    assert [learner.id for learner in live_students_query(branch.id, grade3.id).all()] == [amina.id]

    mark = StudentExamMark.query.filter_by(exam_paper_id=paper.id, student_id=amina.id).one()
    assert mark.marks == 72
    assert paper.class_id == grade2.id
    assert exam.year == 2026


def test_repeater_stays_and_form_4_completes(db):
    branch = _branch(db)
    grade2 = _class(db, branch, "Grade 2")
    _class(db, branch, "Grade 3")
    form3 = _class(db, branch, "Form 3")
    form4 = _class(db, branch, "Form 4")
    repeater = _student(db, branch, grade2, "Benta Kariuki", 11)
    rising = _student(db, branch, form3, "Cate Njeri", 12)
    graduate = _student(db, branch, form4, "Dina Wanjiku", 13)
    subject = _subject(db, "English", "101")
    db.session.add(
        StudentSubjectAllocation(student_id=graduate.id, subject_id=subject.id)
    )
    exam, _paper = _mark(db, branch, form4, graduate, subject, marks=81)
    db.session.commit()

    plan = apply_promotion(branch.id, 2026, 2027, repeat_ids=[repeater.id])

    assert plan["counts"]["repeat"] == 1
    assert plan["counts"]["complete"] == 1
    assert plan["counts"]["move"] == 1

    db.session.refresh(repeater)
    db.session.refresh(rising)
    db.session.refresh(graduate)
    assert repeater.class_id == grade2.id
    assert repeater.current_year == 2027
    assert _enrollment(repeater, 2027).status == ENROLLMENT_REPEATING
    assert rising.class_id == form4.id
    assert graduate.class_id == form4.id
    assert graduate.enrollment_status == ENROLLMENT_COMPLETED
    assert graduate.subject_allocations == []
    assert _enrollment(graduate, 2026).status == ENROLLMENT_COMPLETED
    assert is_leaving_certificate_eligible(graduate)
    assert StudentExamMark.query.filter_by(student_id=graduate.id).count() == 1

    live_form4 = [learner.id for learner in live_students_query(branch.id, form4.id).all()]
    assert live_form4 == [rising.id]
    saved_form4, _year = class_roster(branch.id, form4.id, year=2026)
    assert [learner.id for learner in saved_form4] == [graduate.id]
    assert saved_form4[0].roster_status == ENROLLMENT_COMPLETED

    old_cohort, historical = cohort_for_exam(branch.id, form4.id, exam.id)
    assert historical is True
    assert [learner.id for learner in old_cohort] == [graduate.id]
    assert "completed" in serialize_students([graduate])[0]["grade_form"]


def test_form_4_repeater_stays_on_the_live_list(db):
    branch = _branch(db)
    form4 = _class(db, branch, "Form 4")
    learner = _student(db, branch, form4, "Esha Hassan", 14)
    db.session.commit()

    apply_promotion(branch.id, 2026, 2027, repeat_ids=[learner.id])

    db.session.refresh(learner)
    assert learner.enrollment_status == ENROLLMENT_ACTIVE
    assert learner.class_id == form4.id
    assert [row.id for row in live_students_query(branch.id, form4.id).all()] == [learner.id]
    assert _enrollment(learner, 2027).status == ENROLLMENT_REPEATING


def test_missing_next_class_stays_put(db):
    branch = _branch(db)
    grade6 = _class(db, branch, "Grade 6")
    learner = _student(db, branch, grade6, "Fiona Achieng", 15)
    db.session.commit()

    plan = apply_promotion(branch.id, 2026, 2027)

    assert plan["counts"]["stay"] == 1
    assert plan["counts"]["move"] == 0
    db.session.refresh(learner)
    assert learner.class_id == grade6.id
    assert learner.current_year == 2026
    assert _enrollment(learner, 2026).class_id == grade6.id
    assert StudentEnrollment.query.filter_by(student_id=learner.id, year=2027).count() == 0


def test_stream_is_cleared_when_the_next_class_does_not_offer_it(db):
    branch = _branch(db)
    grade2 = _class(db, branch, "Grade 2", streams=["A"])
    grade3 = _class(db, branch, "Grade 3", streams=["B"])
    learner = _student(db, branch, grade2, "Grace Mwangi", 16, stream="A")
    db.session.commit()

    apply_promotion(branch.id, 2026, 2027)

    db.session.refresh(learner)
    assert learner.class_id == grade3.id
    assert learner.stream is None
    assert _enrollment(learner, 2026).stream == "A"
    assert _enrollment(learner, 2027).stream is None


def test_pp2_moves_to_grade_1(db):
    branch = _branch(db)
    pp2 = _class(db, branch, "PP2")
    grade1 = _class(db, branch, "Grade 1")
    learner = _student(db, branch, pp2, "Hana Yusuf", 17)
    db.session.commit()

    apply_promotion(branch.id, 2026, 2027)

    db.session.refresh(learner)
    assert learner.class_id == grade1.id


def test_running_promotion_twice_does_not_move_them_again(db):
    branch = _branch(db)
    grade2 = _class(db, branch, "Grade 2")
    grade3 = _class(db, branch, "Grade 3")
    _class(db, branch, "Grade 4")
    learner = _student(db, branch, grade2, "Imani Kamau", 18)
    db.session.commit()

    apply_promotion(branch.id, 2026, 2027)
    second = apply_promotion(branch.id, 2026, 2027)

    db.session.refresh(learner)
    assert second["counts"]["move"] == 0
    assert learner.class_id == grade3.id
    assert StudentEnrollment.query.filter_by(student_id=learner.id).count() == 2


def test_another_school_is_left_alone(db):
    home = _branch(db, "Home", "HM001")
    other = _branch(db, "Other", "OT001")
    home_grade2 = _class(db, home, "Grade 2")
    _class(db, home, "Grade 3")
    other_grade2 = _class(db, other, "Grade 2")
    _class(db, other, "Grade 3")
    home_learner = _student(db, home, home_grade2, "Joy Atieno", 19)
    other_learner = _student(db, other, other_grade2, "Ken Oduor", 20)
    db.session.commit()

    apply_promotion(home.id, 2026, 2027)

    db.session.refresh(other_learner)
    assert other_learner.class_id == other_grade2.id
    assert StudentEnrollment.query.filter_by(student_id=other_learner.id).count() == 0
    db.session.refresh(home_learner)
    assert home_learner.current_year == 2027


def test_year_must_be_the_next_year(db):
    branch = _branch(db)
    db.session.commit()
    with pytest.raises(PromotionError):
        build_plan(branch.id, 2026, 2028)


def test_move_updates_the_current_year_and_keeps_the_old_one(db):
    branch = _branch(db)
    grade2 = _class(db, branch, "Grade 2")
    grade3 = _class(db, branch, "Grade 3")
    learner = _student(db, branch, grade2, "Lina Chebet", 21)
    sync_current_enrollment(learner)
    db.session.commit()

    learner.class_id = grade3.id
    learner.stream = "A"
    db.session.flush()
    sync_current_enrollment(learner)
    db.session.commit()

    assert _enrollment(learner, 2026).class_id == grade3.id
    assert StudentEnrollment.query.filter_by(student_id=learner.id, year=2025).count() == 0

    learner.current_year = 2025
    learner.class_id = grade2.id
    upsert_old = sync_current_enrollment(learner)
    db.session.commit()
    assert upsert_old.year == 2025
    assert upsert_old.class_id == grade2.id
    assert _enrollment(learner, 2026).class_id == grade3.id


def test_new_learner_joins_the_year_the_school_is_already_in(db):
    branch = _branch(db)
    grade3 = _class(db, branch, "Grade 3")
    settled = _student(db, branch, grade3, "Mary Ann", 22, year=2027)
    newcomer = Student(
        fullname="Nelly Bosibori",
        admission_number=23,
        branch_id=branch.id,
        class_id=grade3.id,
        stream="A",
        date_of_admission=date(2020, 3, 1),
    )
    db.session.add(newcomer)
    db.session.flush()

    assert placement_year_for_new_student(newcomer) == 2027
    assert newcomer.date_of_admission.year == 2020
    sync_current_enrollment(newcomer)
    db.session.commit()

    assert newcomer.current_year == 2027
    assert _enrollment(newcomer, 2027).class_id == grade3.id
    assert settled.current_year == 2027

    fresh = _branch(db, "New School", "NS001")
    fresh_class = _class(db, fresh, "Grade 1")
    first = Student(
        fullname="First Learner",
        admission_number=1,
        branch_id=fresh.id,
        class_id=fresh_class.id,
        date_of_admission=date(2019, 1, 5),
    )
    db.session.add(first)
    db.session.flush()
    assert placement_year_for_new_student(first) == date.today().year


def test_saved_year_broadsheet_uses_the_old_class_and_the_exam_paper(db):
    branch = _branch(db)
    grade2 = _class(db, branch, "Grade 2")
    grade3 = _class(db, branch, "Grade 3")
    old_learner = _student(db, branch, grade2, "Olive Wambui", 24)
    subject = _subject(db, "Science", "SCI2")
    exam, _paper = _mark(db, branch, grade2, old_learner, subject, marks=64)
    db.session.commit()

    apply_promotion(branch.id, 2026, 2027)
    newcomer = _student(db, branch, grade2, "Paul Kimani", 25, year=2027)
    db.session.add(
        StudentSubjectAllocation(student_id=newcomer.id, subject_id=subject.id)
    )
    db.session.commit()

    data = build_broadsheet_data(branch.id, grade2.id, exam.id, stream="A")
    names = [row["full_name"] for row in data["students"]]
    assert names == ["OLIVE WAMBUI"]
    assert data["subjects"][0]["name"] == "Science"
    mark = data["students"][0]["marks"][subject.id]["marks"]
    assert mark == 64

    class_report = load_class_students_for_report(branch.id, grade2.id, exam_id=exam.id)
    assert [learner.id for learner in class_report] == [old_learner.id]

    db.session.refresh(old_learner)
    assert old_learner.class_id == grade3.id


def test_promote_page_previews_and_saves(db, client):
    branch = _branch(db)
    grade2 = _class(db, branch, "Grade 2")
    grade3 = _class(db, branch, "Grade 3")
    learner = _student(db, branch, grade2, "Queenie Auma", 26)
    admin = Teacher(
        branch_id=branch.id,
        employer="TSC",
        fullname="School Admin",
        gender="F",
        title="Mrs.",
        phone="0711222333",
        username="promoteadmin",
        password_hash=hash_staff_password("secret12"),
        is_admin=True,
    )
    db.session.add(admin)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["_user_id"] = str(admin.id)
        sess["_fresh"] = True

    preview = client.post(
        "/admin/promote",
        data={
            "branch_id": branch.id,
            "from_year": 2026,
            "action": "preview",
        },
    )
    assert preview.status_code == 200
    assert b"Queenie Auma" in preview.data
    assert b"Grade 3" in preview.data

    saved = client.post(
        "/admin/promote",
        data={
            "branch_id": branch.id,
            "from_year": 2026,
            "action": "apply",
        },
        follow_redirects=True,
    )
    assert saved.status_code == 200
    assert b"Promotion saved" in saved.data

    db.session.refresh(learner)
    assert learner.class_id == grade3.id


def test_last_grade_moves_to_a_school_that_has_the_next_class(db):
    primary = _branch(db, "Primary", "PR008")
    senior = _branch(db, "Senior", "SR008")
    grade2 = _class(db, primary, "Grade 2")
    grade3 = _class(db, primary, "Grade 3")
    grade8 = _class(db, primary, "Grade 8", streams=["A"])
    grade9 = _class(db, senior, "Grade 9", streams=["A"])
    rising = _student(db, primary, grade2, "Rita Akinyi", 8)
    mover = _student(db, primary, grade8, "Sara Njoki", 4, stream="A")
    already = _student(db, senior, grade9, "Talia Omar", 4, stream="A")
    subject = _subject(db, "Science", "SCI8")
    _exam, paper = _mark(db, primary, grade8, mover, subject, marks=70)
    db.session.commit()

    allowed = [primary.id, senior.id]
    plan = apply_promotion(
        primary.id,
        2026,
        2027,
        continue_to={grade8.id: senior.id},
        allowed_branch_ids=allowed,
    )

    assert plan["counts"]["move"] == 2
    assert plan["counts"]["continued"] == 1
    db.session.refresh(rising)
    db.session.refresh(mover)
    db.session.refresh(already)
    assert rising.class_id == grade3.id
    assert rising.branch_id == primary.id
    assert rising.admission_number == 8
    assert mover.branch_id == senior.id
    assert mover.class_id == grade9.id
    assert mover.stream == "A"
    assert mover.current_year == 2027
    assert mover.admission_number == 5
    assert already.admission_number == 4
    assert already.class_id == grade9.id

    old = _enrollment(mover, 2026)
    assert old.branch_id == primary.id
    assert old.class_id == grade8.id
    assert old.stream == "A"
    new = _enrollment(mover, 2027)
    assert new.branch_id == senior.id
    assert new.class_id == grade9.id
    assert live_students_query(primary.id, grade8.id).all() == []
    assert mover in live_students_query(senior.id, grade9.id).all()
    mark = StudentExamMark.query.filter_by(exam_paper_id=paper.id, student_id=mover.id).one()
    assert mark.marks == 70
    assert paper.class_id == grade8.id

    second = apply_promotion(primary.id, 2026, 2027, allowed_branch_ids=allowed)
    db.session.refresh(mover)
    assert second["counts"]["continued"] == 0
    assert mover.class_id == grade9.id


def test_last_grade_stays_until_a_school_is_chosen(db):
    primary = _branch(db, "Primary Stay", "PR009")
    senior = _branch(db, "Senior Stay", "SR009")
    grade8 = _class(db, primary, "Grade 8")
    _class(db, senior, "Grade 9")
    learner = _student(db, primary, grade8, "Uma Wairimu", 9)
    db.session.commit()

    plan = apply_promotion(
        primary.id,
        2026,
        2027,
        allowed_branch_ids=[primary.id, senior.id],
    )

    assert plan["counts"]["stay"] == 1
    assert plan["counts"]["continued"] == 0
    group = plan["groups"][0]
    assert group["can_continue"] is True
    assert group["next_label"] == "Grade 9"
    assert [option["id"] for option in group["continue_options"]] == [senior.id]
    db.session.refresh(learner)
    assert learner.branch_id == primary.id
    assert learner.class_id == grade8.id
    assert learner.current_year == 2026


def test_repeater_stays_when_the_class_moves_to_another_school(db):
    primary = _branch(db, "Primary Repeat", "PR010")
    senior = _branch(db, "Senior Repeat", "SR010")
    grade8 = _class(db, primary, "Grade 8")
    grade9 = _class(db, senior, "Grade 9")
    staying = _student(db, primary, grade8, "Vera Cherono", 11)
    leaving = _student(db, primary, grade8, "Wanja Kariuki", 12)
    db.session.commit()

    plan = apply_promotion(
        primary.id,
        2026,
        2027,
        repeat_ids=[staying.id],
        continue_to={grade8.id: senior.id},
        allowed_branch_ids=[primary.id, senior.id],
    )

    assert plan["counts"]["repeat"] == 1
    assert plan["counts"]["continued"] == 1
    db.session.refresh(staying)
    db.session.refresh(leaving)
    assert staying.branch_id == primary.id
    assert staying.class_id == grade8.id
    assert staying.admission_number == 11
    assert staying.current_year == 2027
    assert _enrollment(staying, 2027).status == ENROLLMENT_REPEATING
    assert leaving.branch_id == senior.id
    assert leaving.class_id == grade9.id


def test_stream_clears_when_the_other_school_does_not_offer_it(db):
    primary = _branch(db, "Primary Stream", "PR011")
    senior = _branch(db, "Senior Stream", "SR011")
    grade8 = _class(db, primary, "Grade 8", streams=["A"])
    grade9 = _class(db, senior, "Grade 9", streams=["B"])
    learner = _student(db, primary, grade8, "Xena Odhiambo", 13, stream="A")
    db.session.commit()

    apply_promotion(
        primary.id,
        2026,
        2027,
        continue_to={grade8.id: senior.id},
        allowed_branch_ids=[primary.id, senior.id],
    )

    db.session.refresh(learner)
    assert learner.class_id == grade9.id
    assert learner.stream is None
    assert _enrollment(learner, 2026).stream == "A"
    assert _enrollment(learner, 2027).stream is None


def test_cannot_send_the_last_grade_to_a_school_you_cannot_open(db):
    primary = _branch(db, "Primary Locked", "PR012")
    senior = _branch(db, "Senior Locked", "SR012")
    grade8 = _class(db, primary, "Grade 8")
    _class(db, senior, "Grade 9")
    learner = _student(db, primary, grade8, "Yara Hassan", 14)
    db.session.commit()

    with pytest.raises(PromotionError):
        apply_promotion(
            primary.id,
            2026,
            2027,
            continue_to={grade8.id: senior.id},
            allowed_branch_ids=[primary.id],
        )

    db.session.refresh(learner)
    assert learner.branch_id == primary.id
    assert learner.class_id == grade8.id
    assert continuation_targets(primary.id, "Grade 9", [primary.id]) == []
    assert continuation_targets(primary.id, "Grade 9", [primary.id, senior.id])[0]["id"] == senior.id


def test_a_school_without_the_next_grade_is_not_offered(db):
    primary = _branch(db, "Primary End", "PR013")
    other = _branch(db, "Other End", "OT013")
    grade8 = _class(db, primary, "Grade 8")
    _class(db, other, "Grade 7")
    learner = _student(db, primary, grade8, "No Move", 16)
    db.session.commit()

    targets = continuation_targets(primary.id, "Grade 9", [primary.id, other.id])
    assert targets == []
    plan = build_plan(
        primary.id,
        2026,
        2027,
        allowed_branch_ids=[primary.id, other.id],
    )
    assert plan["groups"][0]["can_continue"] is False
    db.session.refresh(learner)
    assert learner.class_id == grade8.id


def test_promote_page_can_send_the_last_grade_to_another_school(db, client):
    primary = _branch(db, "Primary Page", "PR014")
    senior = _branch(db, "Senior Page", "SR014")
    grade8 = _class(db, primary, "Grade 8")
    grade9 = _class(db, senior, "Grade 9")
    learner = _student(db, primary, grade8, "Zawadi Achieng", 15)
    admin = Teacher(
        branch_id=primary.id,
        employer="TSC",
        fullname="Two School Admin",
        gender="F",
        title="Mrs.",
        phone="0711222444",
        username="continueadmin",
        password_hash=hash_staff_password("secret12"),
        is_admin=True,
        is_super_admin=True,
    )
    db.session.add(admin)
    db.session.flush()
    db.session.add(SuperAdminBranch(teacher_id=admin.id, branch_id=primary.id))
    db.session.add(SuperAdminBranch(teacher_id=admin.id, branch_id=senior.id))
    db.session.commit()

    with client.session_transaction() as sess:
        sess["_user_id"] = str(admin.id)
        sess["_fresh"] = True

    preview = client.post(
        "/admin/promote",
        data={
            "branch_id": primary.id,
            "from_year": 2026,
            "action": "preview",
        },
    )
    assert preview.status_code == 200
    assert b"Send Grade 8" in preview.data
    assert b"Senior Page" in preview.data

    saved = client.post(
        "/admin/promote",
        data={
            "branch_id": primary.id,
            "from_year": 2026,
            "action": "apply",
            f"continue_branch_{grade8.id}": senior.id,
        },
        follow_redirects=True,
    )
    assert saved.status_code == 200
    assert b"another school" in saved.data
    db.session.refresh(learner)
    assert learner.branch_id == senior.id
    assert learner.class_id == grade9.id
