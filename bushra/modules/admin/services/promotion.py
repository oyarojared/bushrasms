"""Move a school cohort into the next year without rewriting exam marks.

Classes stay put. Learners move. Each student keeps one enrollment row
per year, so a saved year still lists the class they were in then.
Exam papers keep the marks.
"""

import re
from datetime import date

from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload

from ....modals import db
from ....modals.assessment_db import Exam
from ....modals.branches_db import Branch, BranchClasses
from ....modals.students_db import Student, StudentEnrollment
from .grades import format_grade_form, is_archived_class_name, live_class_name, sort_grade_list
from .subs import auto_allocate_subjects


ENROLLMENT_ACTIVE = "active"
ENROLLMENT_REPEATING = "repeating"
ENROLLMENT_COMPLETED = "completed"

_TERMINAL_REASON = "Completed. They stay on record and leave the live class list."


class PromotionError(ValueError):
    """The promotion request cannot be carried out."""


def not_completed_clause():
    """SQL filter that keeps learners who are still on a live class list."""
    return or_(
        Student.enrollment_status.is_(None),
        Student.enrollment_status != ENROLLMENT_COMPLETED,
    )


def live_students_query(branch_id, class_id, stream=None):
    query = Student.query.filter_by(branch_id=branch_id, class_id=class_id)
    query = query.filter(not_completed_clause())
    if stream:
        query = query.filter(Student.stream == stream)
    return query.order_by(Student.fullname.asc(), Student.admission_number.asc())


def enrolled_students_query(branch_id, class_id, year, stream=None):
    query = (
        Student.query.join(
            StudentEnrollment, StudentEnrollment.student_id == Student.id
        )
        .filter(
            StudentEnrollment.branch_id == branch_id,
            StudentEnrollment.class_id == class_id,
            StudentEnrollment.year == int(year),
        )
    )
    if stream:
        query = query.filter(StudentEnrollment.stream == stream)
    return query.order_by(Student.fullname.asc(), Student.admission_number.asc())


def class_year_has_enrollments(branch_id, class_id, year):
    if not year:
        return False
    return (
        db.session.query(StudentEnrollment.id)
        .filter_by(branch_id=branch_id, class_id=class_id, year=int(year))
        .first()
        is not None
    )


def attach_year_placement(students, year):
    """Remember the class stream and status saved for this year."""
    if not students:
        return students
    rows = StudentEnrollment.query.filter(
        StudentEnrollment.student_id.in_([student.id for student in students]),
        StudentEnrollment.year == int(year),
    ).all()
    by_student = {row.student_id: row for row in rows}
    for student in students:
        row = by_student.get(student.id)
        student.loaded_from_enrollment = True
        student.roster_status = row.status if row else None
        student.roster_stream = row.stream if row else None
    return students


def class_roster(branch_id, class_id, stream=None, year=None):
    """
    Current class list, or the list saved for a year.

    Returns (students, year). Year is None for the live list.
    A requested year with no saved rows returns an empty list.
    """
    if year:
        year = int(year)
        if class_year_has_enrollments(branch_id, class_id, year):
            students = enrolled_students_query(
                branch_id, class_id, year, stream=stream
            ).all()
            attach_year_placement(students, year)
            return students, year
        return [], year
    return live_students_query(branch_id, class_id, stream=stream).all(), None


def cohort_for_exam(branch_id, class_id, exam_id, stream=None):
    """
    Learners who belong on an exam screen.

    A year that has been saved uses that enrollment. Otherwise the live
    class is used, which leaves completed learners off the list.
    """
    exam = db.session.get(Exam, exam_id) if exam_id else None
    if exam is not None and class_year_has_enrollments(branch_id, class_id, exam.year):
        students = enrolled_students_query(
            branch_id, class_id, exam.year, stream=stream
        ).all()
        attach_year_placement(students, exam.year)
        return students, True
    return live_students_query(branch_id, class_id, stream=stream).all(), False


def uses_current_subjects(student, class_id):
    """Current subject lists belong only to learners still in that class."""
    if getattr(student, "enrollment_status", None) == ENROLLMENT_COMPLETED:
        return False
    try:
        return int(student.class_id) == int(class_id)
    except (TypeError, ValueError):
        return False


def placement_year_for_new_student(student):
    """
    Year a newly added learner joins.

    After a promotion the rest of the school is already in the new year,
    so a late admission joins that year rather than the year just closed.
    """
    latest = (
        db.session.query(func.max(Student.current_year))
        .filter(
            Student.branch_id == student.branch_id,
            Student.id != student.id,
            not_completed_clause(),
        )
        .scalar()
    )
    if latest:
        return int(latest)
    return date.today().year


def _clean_stream(stream):
    text = (stream or "").strip()
    return text or None


def upsert_enrollment(student, year, class_id, stream, status):
    year = int(year)
    stream = _clean_stream(stream)
    row = StudentEnrollment.query.filter_by(student_id=student.id, year=year).first()
    if row is None:
        row = StudentEnrollment(
            student_id=student.id,
            branch_id=student.branch_id,
            year=year,
        )
        db.session.add(row)
    row.branch_id = student.branch_id
    row.class_id = class_id
    row.stream = stream
    row.status = status
    return row


def snapshot_year_if_missing(student, year):
    """Record the current class for a year that has no row yet."""
    year = int(year)
    row = StudentEnrollment.query.filter_by(student_id=student.id, year=year).first()
    if row:
        return row
    return upsert_enrollment(
        student,
        year,
        student.class_id,
        student.stream,
        ENROLLMENT_ACTIVE,
    )


def sync_current_enrollment(student):
    """
    Write the learner's current class onto this year's enrollment.

    Called when a learner is added or moved. Past years are left alone.
    Moving a completed learner places them in the live year again.
    """
    if not student or not getattr(student, "id", None):
        return None

    was_completed = student.enrollment_status == ENROLLMENT_COMPLETED
    if was_completed:
        student.enrollment_status = ENROLLMENT_ACTIVE
        year = placement_year_for_new_student(student)
        if student.current_year and year <= int(student.current_year):
            year = int(student.current_year) + 1
        student.current_year = year
    elif not student.current_year:
        student.current_year = placement_year_for_new_student(student)

    return upsert_enrollment(
        student,
        student.current_year,
        student.class_id,
        student.stream,
        ENROLLMENT_ACTIVE,
    )


def enrollment_history(student):
    rows = (
        StudentEnrollment.query.options(joinedload(StudentEnrollment.school_class))
        .filter_by(student_id=student.id)
        .order_by(StudentEnrollment.year.desc())
        .all()
    )
    history = []
    for row in rows:
        school_class = row.school_class
        history.append(
            {
                "year": row.year,
                "grade_form": live_class_name(school_class.grade_form) if school_class else "",
                "stream": row.stream or "",
                "status": row.status,
            }
        )
    return history


def _compact_grade(name):
    return format_grade_form(live_class_name(name)).replace(" ", "")


def is_terminal_grade(name):
    compact = _compact_grade(name)
    if compact == "IGCSE":
        return True
    grade_match = re.match(r"GRADE(\d+)$", compact)
    if grade_match and int(grade_match.group(1)) >= 12:
        return True
    form_match = re.match(r"FORM(\d+)$", compact)
    if form_match and int(form_match.group(1)) >= 4:
        return True
    return False


def schools_have_form_4(branch_ids=None):
    """True when these schools run Form 4. None means every school."""
    query = db.session.query(BranchClasses.grade_form)
    if branch_ids is not None:
        branch_ids = [int(value) for value in branch_ids]
        if not branch_ids:
            return False
        query = query.filter(BranchClasses.branch_id.in_(branch_ids))
    for (name,) in query.all():
        if name and not is_archived_class_name(name) and _compact_grade(name) == "FORM4":
            return True
    return False


def next_grade_name(name):
    """Next grade label, or None when the ladder ends or the name is unknown."""
    raw = format_grade_form(live_class_name(name))
    compact = raw.replace(" ", "")

    if raw in {"PLAY GROUP", "PLAYGROUP", "PLAY-GROUP"}:
        return "PP1"
    if compact == "PP1":
        return "PP2"
    if compact == "PP2":
        return "Grade 1"

    grade_match = re.match(r"GRADE(\d+)$", compact)
    if grade_match:
        number = int(grade_match.group(1))
        if number >= 12:
            return None
        return f"Grade {number + 1}"

    form_match = re.match(r"FORM(\d+)$", compact)
    if form_match:
        number = int(form_match.group(1))
        if number >= 4:
            return None
        return f"Form {number + 1}"

    return None


def class_named(branch_id, grade_name):
    key = format_grade_form(grade_name)
    classes = BranchClasses.query.filter_by(branch_id=branch_id).all()
    for school_class in classes:
        if is_archived_class_name(school_class.grade_form):
            continue
        if format_grade_form(live_class_name(school_class.grade_form)) == key:
            return school_class
    return None


def destination_stream(dest_class, current_stream):
    """Keep the stream when the next class offers it. Otherwise clear it."""
    stream = _clean_stream(current_stream)
    offered = [item for item in (dest_class.streams or []) if item]
    if not offered:
        return None, bool(stream)
    if stream in offered:
        return stream, False
    return None, True


def _check_years(from_year, to_year):
    try:
        from_year = int(from_year)
        to_year = int(to_year)
    except (TypeError, ValueError):
        raise PromotionError("Choose the year you are closing.")
    if to_year != from_year + 1:
        raise PromotionError("Promotion moves a cohort into the next year only.")
    return from_year, to_year


def _classify_class(branch_id, school_class):
    if is_archived_class_name(school_class.grade_form):
        return {
            "kind": "stay",
            "reason": "This class is archived.",
        }

    nxt_name = next_grade_name(school_class.grade_form)
    if nxt_name is None:
        if is_terminal_grade(school_class.grade_form):
            return {"kind": "complete", "reason": _TERMINAL_REASON}
        return {
            "kind": "stay",
            "reason": "This class has no next grade.",
        }

    dest = class_named(branch_id, nxt_name)
    if dest is None:
        return {
            "kind": "stay",
            "reason": f"This school has no {nxt_name} class.",
            "can_continue": True,
            "next_label": nxt_name,
        }
    return {"kind": "move", "dest": dest, "reason": ""}


def _candidate_students(branch_id, from_year):
    students = (
        Student.query.options(joinedload(Student.class_info))
        .filter_by(branch_id=branch_id)
        .order_by(Student.fullname.asc(), Student.admission_number.asc())
        .all()
    )
    chosen = []
    for student in students:
        if student.enrollment_status == ENROLLMENT_COMPLETED:
            continue
        if student.current_year not in (None, from_year):
            continue
        if not student.class_id:
            continue
        chosen.append(student)
    return chosen


def continuation_targets(source_branch_id, next_label, allowed_branch_ids=None):
    """Schools that have the next grade and that the caller may use.

    allowed_branch_ids None means every school. The source school is omitted.
    """
    if not next_label:
        return []
    query = Branch.query.filter(Branch.id != int(source_branch_id))
    if allowed_branch_ids is not None:
        allowed = [int(value) for value in allowed_branch_ids if int(value) != int(source_branch_id)]
        if not allowed:
            return []
        query = query.filter(Branch.id.in_(allowed))
    found = []
    for branch in query.order_by(Branch.branch_name.asc()).all():
        if class_named(branch.id, next_label) is None:
            continue
        found.append({"id": branch.id, "name": branch.branch_name})
    return found


def _coerce_continue_to(continue_to):
    chosen = {}
    for key, value in (continue_to or {}).items():
        try:
            chosen[int(key)] = int(value)
        except (TypeError, ValueError):
            continue
    return chosen


def _continuation_choice(source_branch_id, class_id, decision, continue_to, allowed_branch_ids):
    """Where a stuck class may go, and the school chosen for this preview."""
    if not decision.get("can_continue"):
        return None
    options = continuation_targets(
        source_branch_id, decision.get("next_label"), allowed_branch_ids
    )
    chosen = continue_to.get(class_id)
    dest = None
    dest_name = ""
    if chosen:
        match = next((option for option in options if option["id"] == chosen), None)
        if match is None:
            raise PromotionError("You cannot send learners to that school.")
        dest = class_named(chosen, decision["next_label"])
        if dest is None:
            raise PromotionError(f"That school has no {decision['next_label']} class.")
        dest_name = match["name"]
    return {
        "options": options,
        "chosen": chosen if dest is not None else None,
        "dest": dest,
        "dest_name": dest_name,
        "next_label": decision.get("next_label") or "",
    }


def _next_admission_number(branch_id, reserved):
    branch_id = int(branch_id)
    if branch_id not in reserved:
        largest = (
            db.session.query(func.max(Student.admission_number))
            .filter(Student.branch_id == branch_id)
            .scalar()
        )
        reserved[branch_id] = int(largest or 0)
    reserved[branch_id] += 1
    return reserved[branch_id]


def build_plan(
    branch_id,
    from_year,
    to_year,
    repeat_ids=None,
    continue_to=None,
    allowed_branch_ids=None,
):
    from_year, to_year = _check_years(from_year, to_year)
    repeat_ids = {int(value) for value in (repeat_ids or []) if str(value).strip()}
    continue_to = _coerce_continue_to(continue_to)

    grouped = {}
    resolved = {}
    for student in _candidate_students(branch_id, from_year):
        school_class = student.class_info
        if school_class is None:
            continue
        decision = _classify_class(branch_id, school_class)
        if school_class.id not in resolved:
            resolved[school_class.id] = _continuation_choice(
                branch_id,
                school_class.id,
                decision,
                continue_to,
                allowed_branch_ids,
            )
        choice = resolved[school_class.id]
        if choice and choice["dest"] is not None:
            decision = {
                "kind": "move",
                "dest": choice["dest"],
                "reason": "",
                "continued": True,
                "dest_branch_id": choice["chosen"],
                "dest_branch_name": choice["dest_name"],
            }
        label = live_class_name(school_class.grade_form)
        base_kind = decision["kind"]
        natural_dest = decision.get("dest") or school_class
        base_reason = decision.get("reason") or ""
        base_dest_stream = _clean_stream(student.stream)

        if base_kind == "move":
            base_dest_label = live_class_name(natural_dest.grade_form)
            base_dest_stream, stream_cleared = destination_stream(
                natural_dest, student.stream
            )
            if decision.get("continued"):
                school_name = decision.get("dest_branch_name") or "the other school"
                if stream_cleared and student.stream:
                    base_reason = (
                        f"Moves to {school_name}. Stream {student.stream} is not "
                        f"offered in {base_dest_label}, so the stream is cleared."
                    )
                else:
                    base_reason = f"Moves to {school_name}."
            elif stream_cleared and student.stream:
                base_reason = (
                    f"Stream {student.stream} is not offered in "
                    f"{base_dest_label}, so the stream is cleared."
                )
        elif base_kind == "complete":
            base_dest_label = "Completed"
            base_dest_stream = ""
        else:
            base_dest_label = label

        kind = base_kind
        dest_label = base_dest_label
        dest_stream = base_dest_stream
        reason = base_reason
        if base_kind in ("move", "complete") and student.id in repeat_ids:
            kind = "repeat"
            dest_label = label
            dest_stream = _clean_stream(student.stream)
            reason = "Staying behind to repeat."

        bucket = grouped.get(school_class.id)
        if bucket is None:
            bucket = {
                "class_id": school_class.id,
                "from_label": label,
                "students": [],
                "can_continue": bool(choice and choice["options"]),
                "next_label": (choice or {}).get("next_label") or "",
                "continue_options": (choice or {}).get("options") or [],
                "continue_branch_id": (choice or {}).get("chosen"),
            }
            grouped[school_class.id] = bucket

        bucket["students"].append(
            {
                "id": student.id,
                "fullname": student.fullname,
                "admission_number": student.admission_number,
                "stream": student.stream or "",
                "kind": kind,
                "dest_label": dest_label,
                "dest_stream": dest_stream or "",
                "dest_branch_id": decision.get("dest_branch_id"),
                "continued": bool(decision.get("continued")),
                "reason": reason,
                "can_repeat": base_kind in ("move", "complete"),
                "base_kind": base_kind,
                "base_dest_label": base_dest_label,
                "base_dest_stream": base_dest_stream or "",
                "base_reason": base_reason,
            }
        )

    ordered = sort_grade_list(
        [(class_id, bucket["from_label"]) for class_id, bucket in grouped.items()],
        dedupe=False,
    )
    groups = []
    counts = {"move": 0, "repeat": 0, "complete": 0, "stay": 0, "continued": 0}
    for class_id, _label in ordered:
        bucket = grouped[class_id]
        for item in bucket["students"]:
            counts[item["kind"]] = counts.get(item["kind"], 0) + 1
            if item["kind"] == "move" and item.get("continued"):
                counts["continued"] += 1
        groups.append(bucket)

    return {
        "from_year": from_year,
        "to_year": to_year,
        "groups": groups,
        "counts": counts,
    }


def _clear_subject_allocations(student):
    for allocation in list(student.subject_allocations or []):
        student.subject_allocations.remove(allocation)


def apply_promotion(
    branch_id,
    from_year,
    to_year,
    repeat_ids=None,
    continue_to=None,
    allowed_branch_ids=None,
):
    """Save the plan. Marks are not copied or deleted."""
    plan = build_plan(
        branch_id,
        from_year,
        to_year,
        repeat_ids=repeat_ids,
        continue_to=continue_to,
        allowed_branch_ids=allowed_branch_ids,
    )
    from_year = plan["from_year"]
    to_year = plan["to_year"]

    students = {
        student.id: student
        for student in _candidate_students(branch_id, from_year)
    }
    decisions = {}
    for group in plan["groups"]:
        for item in group["students"]:
            decisions[item["id"]] = item

    next_admission = {}
    try:
        for student_id, item in decisions.items():
            student = students.get(student_id)
            if student is None:
                continue
            kind = item["kind"]

            if kind == "move":
                dest_branch_id = int(item.get("dest_branch_id") or branch_id)
                dest = class_named(dest_branch_id, item["dest_label"])
                if dest is None:
                    raise PromotionError(
                        f"Could not find {item['dest_label']} for this promotion."
                    )
                snapshot_year_if_missing(student, from_year)
                previous_class_id = student.class_id
                dest_stream = _clean_stream(item["dest_stream"])
                if dest_branch_id != int(branch_id):
                    student.admission_number = _next_admission_number(
                        dest_branch_id, next_admission
                    )
                    student.branch_id = dest_branch_id
                student.class_id = dest.id
                student.stream = dest_stream
                student.current_year = to_year
                student.enrollment_status = ENROLLMENT_ACTIVE
                db.session.flush()
                db.session.expire(student, ["class_info"])
                if dest.id != previous_class_id:
                    auto_allocate_subjects(
                        student, previous_class_id=previous_class_id
                    )
                upsert_enrollment(
                    student, to_year, dest.id, dest_stream, ENROLLMENT_ACTIVE
                )
            elif kind == "repeat":
                snapshot_year_if_missing(student, from_year)
                student.current_year = to_year
                student.enrollment_status = ENROLLMENT_ACTIVE
                upsert_enrollment(
                    student,
                    to_year,
                    student.class_id,
                    student.stream,
                    ENROLLMENT_REPEATING,
                )
            elif kind == "complete":
                row = snapshot_year_if_missing(student, from_year)
                row.status = ENROLLMENT_COMPLETED
                student.enrollment_status = ENROLLMENT_COMPLETED
                student.current_year = from_year
                _clear_subject_allocations(student)
            else:
                snapshot_year_if_missing(student, from_year)
                if student.current_year is None:
                    student.current_year = from_year

        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return plan


def describe_promotion(plan):
    counts = plan.get("counts") or {}
    parts = []
    continued = counts.get("continued") or 0
    stayed_move = (counts.get("move") or 0) - continued
    if stayed_move:
        parts.append(f"{stayed_move} moved to the next grade")
    if continued:
        parts.append(f"{continued} moved to the next grade at another school")
    if counts.get("repeat"):
        parts.append(f"{counts['repeat']} kept back to repeat")
    if counts.get("complete"):
        parts.append(
            f"{counts['complete']} completed and removed from the live class list"
        )
    if counts.get("stay"):
        parts.append(
            f"{counts['stay']} left in place because the next class is not in this school"
        )
    if not parts:
        return "No learners were due to move for that year."
    return "Promotion saved. " + ", ".join(parts) + "."
