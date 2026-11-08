"""In-app notices between staff accounts. SMS is reserved and not sent."""

from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.orm import joinedload, subqueryload

from ....modals.branches_db import Branch, BranchClasses
from ....modals.messages_db import StaffMessage, StaffMessageRecipient
from ....modals.staff_db import ClassTeacher, Teacher
from ....modals.subjects_db import Lesson
from ....modals import db
from ..utils.branch_utils import (
    is_system_admin,
    user_can_access_branch,
    user_can_select_branch,
)


class MessageError(ValueError):
    pass


# School dropdown value for a system admin message to every staff account.
ALL_USERS = "all"


def is_full_sender(user):
    return _is_full_sender(user)


def can_send_messages(user):
    """School admin, super admin, or system admin."""
    if not getattr(user, "is_authenticated", False):
        return False
    return _is_full_sender(user)


def _is_full_sender(user):
    return bool(
        getattr(user, "is_admin", False)
        or getattr(user, "is_super_admin", False)
        or is_system_admin(user)
    )


def unread_count(user):
    if not getattr(user, "is_authenticated", False):
        return 0
    return StaffMessageRecipient.query.filter_by(
        teacher_id=user.id, opened_at=None
    ).count()


def resolve_branch_id(user, requested_branch_id):
    if not user_can_select_branch(user):
        branch_id = getattr(user, "branch_id", None)
        if branch_id is None or not user_can_access_branch(branch_id, user):
            raise MessageError("You do not have a school to message.")
        return int(branch_id)

    if requested_branch_id in (None, ""):
        branch = (
            Branch.query.filter(Branch.id.in_(_accessible_ids(user)))
            .order_by(Branch.branch_name.asc())
            .first()
            if _accessible_ids(user) is not None
            else Branch.query.order_by(Branch.branch_name.asc()).first()
        )
        if branch is None:
            raise MessageError("There is no school to message.")
        return branch.id

    try:
        branch_id = int(requested_branch_id)
    except (TypeError, ValueError):
        raise MessageError("Choose a school.")
    if not user_can_access_branch(branch_id, user):
        raise MessageError("You cannot send messages for that school.")
    return branch_id


def _accessible_ids(user):
    from ..utils.branch_utils import accessible_branch_ids

    return accessible_branch_ids(user)


def class_choices(user, branch_id):
    """Options are 'class_id|stream'."""
    if _is_full_sender(user):
        classes = (
            BranchClasses.query.filter_by(branch_id=branch_id)
            .order_by(BranchClasses.grade_form.asc())
            .all()
        )
        options = []
        for cls in classes:
            streams = [stream for stream in (cls.streams or []) if stream]
            if streams:
                for stream in streams:
                    options.append(
                        {
                            "value": f"{cls.id}|{stream}",
                            "label": f"{cls.grade_form} — {stream}",
                        }
                    )
            else:
                options.append({"value": f"{cls.id}|", "label": cls.grade_form})
        return options

    options = []
    seen = set()
    for assignment in getattr(user, "class_teacher_assignments", []) or []:
        if int(assignment.branch_id) != int(branch_id) or assignment.class_ is None:
            continue
        stream = assignment.stream or ""
        key = (assignment.class_id, stream)
        if key in seen:
            continue
        seen.add(key)
        label = assignment.class_.grade_form
        if stream:
            label = f"{label} — {stream}"
        options.append({"value": f"{assignment.class_id}|{stream}", "label": label})
    return options


def teacher_choices(user, branch_id):
    if not _is_full_sender(user):
        return []
    teachers = (
        Teacher.query.filter_by(branch_id=branch_id)
        .filter(Teacher.id != user.id)
        .order_by(Teacher.fullname.asc())
        .all()
    )
    return [{"id": teacher.id, "name": teacher.fullname} for teacher in teachers]


PAGE_SIZE = 10


def _inbox_query(user):
    return (
        StaffMessageRecipient.query.options(
            joinedload(StaffMessageRecipient.message).joinedload(StaffMessage.sender),
            joinedload(StaffMessageRecipient.message).joinedload(StaffMessage.branch),
        )
        .join(StaffMessage)
        .filter(StaffMessageRecipient.teacher_id == user.id)
        .order_by(StaffMessage.created_at.desc(), StaffMessageRecipient.id.desc())
    )


def inbox_for(user):
    return _inbox_query(user).all()


def inbox_page(user, page, per_page=PAGE_SIZE):
    return _inbox_query(user).paginate(page=page, per_page=per_page, error_out=False)


def _sent_rows(messages):
    rows = []
    for message in messages:
        recipients = list(message.recipients)
        rows.append(
            {
                "message": message,
                "sent_count": len(recipients),
                "opened_count": sum(1 for row in recipients if row.opened_at),
            }
        )
    return rows


def _sent_query(user):
    return (
        StaffMessage.query.options(subqueryload(StaffMessage.recipients))
        .filter_by(sender_id=user.id)
        .order_by(StaffMessage.created_at.desc())
    )


def sent_for(user):
    return _sent_rows(_sent_query(user).all())


def sent_page(user, page, per_page=PAGE_SIZE):
    pagination = _sent_query(user).paginate(
        page=page, per_page=per_page, error_out=False
    )
    pagination.items = _sent_rows(pagination.items)
    return pagination


def open_inbox_item(user, recipient_id):
    item = StaffMessageRecipient.query.options(
        joinedload(StaffMessageRecipient.message).joinedload(StaffMessage.sender),
        joinedload(StaffMessageRecipient.message).joinedload(StaffMessage.branch),
    ).filter_by(id=recipient_id, teacher_id=user.id).first()
    if item is None:
        return None
    if item.opened_at is None:
        item.opened_at = datetime.utcnow()
        db.session.commit()
    return item


def sent_detail(user, message_id):
    message = StaffMessage.query.options(
        joinedload(StaffMessage.recipients).joinedload(StaffMessageRecipient.teacher)
    ).filter_by(id=message_id, sender_id=user.id).first()
    return message


def delete_sent_message(user, message_id):
    """Remove a notice the user sent, including every recipient's copy."""
    message = StaffMessage.query.filter_by(id=message_id, sender_id=user.id).first()
    if message is None:
        return False
    db.session.delete(message)
    db.session.commit()
    return True


def send_in_app(
    user,
    *,
    branch_id,
    audience,
    title,
    body,
    teacher_id=None,
    class_value=None,
    channel="in_app",
):
    if channel != "in_app":
        raise MessageError("SMS is not available yet. Send this as an in-app message.")
    if not can_send_messages(user):
        raise MessageError("You cannot send messages.")

    title = (title or "").strip()
    body = (body or "").strip()
    if not title:
        raise MessageError("Add a title.")
    if len(title) > 160:
        raise MessageError("The title must be 160 characters or fewer.")
    if not body:
        raise MessageError("Write the message.")
    if len(body) > 2000:
        raise MessageError("The message must be 2,000 characters or fewer.")

    if str(branch_id or "") == ALL_USERS:
        if not is_system_admin(user):
            raise MessageError("Only a system admin can message every school.")
        audience_key = (audience or "all").strip()
        if audience_key == "school":
            audience_key = "all"
        labels = {
            "all": "All users, every school",
            "admins": "Admins, every school",
            "super_admins": "Super admins, every school",
        }
        if audience_key not in labels:
            raise MessageError("Choose who should receive this message.")
        query = Teacher.query.filter(Teacher.id != user.id)
        if audience_key == "admins":
            query = query.filter(Teacher.is_admin.is_(True))
        elif audience_key == "super_admins":
            query = query.filter(Teacher.is_super_admin.is_(True))
        teachers = query.order_by(Teacher.fullname.asc()).all()
        if not teachers:
            raise MessageError("Nobody else in that group can receive this message.")
        message = StaffMessage(
            sender_id=user.id,
            branch_id=None,
            channel="in_app",
            title=title,
            body=body,
            audience_label=labels[audience_key],
            created_at=datetime.utcnow(),
        )
        db.session.add(message)
        db.session.flush()
        for teacher in teachers:
            db.session.add(
                StaffMessageRecipient(message_id=message.id, teacher_id=teacher.id)
            )
        db.session.commit()
        return message

    branch_id = resolve_branch_id(user, branch_id)
    branch = Branch.query.get(branch_id)
    if branch is None:
        raise MessageError("That school does not exist.")

    teachers, audience_label = _recipients_for(
        user,
        branch,
        audience,
        teacher_id=teacher_id,
        class_value=class_value,
    )
    if not teachers:
        raise MessageError("Nobody else in that group can receive this message.")

    message = StaffMessage(
        sender_id=user.id,
        branch_id=branch.id,
        channel="in_app",
        title=title,
        body=body,
        audience_label=audience_label,
        created_at=datetime.utcnow(),
    )
    db.session.add(message)
    db.session.flush()
    for teacher in teachers:
        db.session.add(
            StaffMessageRecipient(message_id=message.id, teacher_id=teacher.id)
        )
    db.session.commit()
    return message


def _recipients_for(user, branch, audience, teacher_id=None, class_value=None):
    full = _is_full_sender(user)
    if audience == "school":
        if not full:
            raise MessageError("You can only message teachers in your own class.")
        teachers = (
            Teacher.query.filter_by(branch_id=branch.id)
            .filter(Teacher.id != user.id)
            .order_by(Teacher.fullname.asc())
            .all()
        )
        return teachers, f"All teachers at {branch.branch_name}"

    if audience == "teacher":
        if not full:
            raise MessageError("You can only message teachers in your own class.")
        try:
            chosen_id = int(teacher_id)
        except (TypeError, ValueError):
            raise MessageError("Choose a teacher.")
        teacher = Teacher.query.filter_by(id=chosen_id, branch_id=branch.id).first()
        if teacher is None or teacher.id == user.id:
            raise MessageError("Choose a teacher in this school.")
        return [teacher], teacher.fullname

    if audience == "class":
        class_id, stream = _parse_class_value(class_value)
        allowed = {
            (int(row["value"].split("|", 1)[0]), row["value"].split("|", 1)[1])
            for row in class_choices(user, branch.id)
        }
        if (class_id, stream) not in allowed:
            raise MessageError("Choose a class you can message.")
        teachers = _teachers_for_class(branch.id, class_id, stream, exclude_id=user.id)
        cls = BranchClasses.query.get(class_id)
        label = cls.grade_form if cls is not None else "Class"
        if stream:
            label = f"{label} — {stream}"
        return teachers, f"Teachers of {label}"

    raise MessageError("Choose who should receive this message.")


def _parse_class_value(class_value):
    raw = (class_value or "").strip()
    if "|" not in raw:
        raise MessageError("Choose a class.")
    class_part, stream = raw.split("|", 1)
    try:
        class_id = int(class_part)
    except ValueError:
        raise MessageError("Choose a class.")
    return class_id, stream


def _teachers_for_class(branch_id, class_id, stream, exclude_id=None):
    teacher_ids = set()
    class_teachers = ClassTeacher.query.filter_by(
        branch_id=branch_id, class_id=class_id
    )
    lessons = Lesson.query.filter_by(branch_id=branch_id, class_id=class_id)
    if stream:
        class_teachers = class_teachers.filter(ClassTeacher.stream == stream)
        lessons = lessons.filter(Lesson.stream == stream)
    else:
        class_teachers = class_teachers.filter(
            or_(ClassTeacher.stream.is_(None), ClassTeacher.stream == "")
        )
        lessons = lessons.filter(or_(Lesson.stream.is_(None), Lesson.stream == ""))

    for row in class_teachers:
        if row.teacher_id:
            teacher_ids.add(row.teacher_id)
    for row in lessons:
        if row.teacher_id:
            teacher_ids.add(row.teacher_id)
    if exclude_id is not None:
        teacher_ids.discard(exclude_id)
    if not teacher_ids:
        return []
    return (
        Teacher.query.filter(Teacher.id.in_(teacher_ids))
        .order_by(Teacher.fullname.asc())
        .all()
    )
