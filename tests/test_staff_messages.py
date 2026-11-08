import pytest

from ..bushra import create_app
from ..bushra import db as _db
from ..bushra.config import DevelopmentConfig
from ..bushra.modals.branches_db import Branch, BranchClasses
from ..bushra.modals.messages_db import StaffMessage, StaffMessageRecipient
from ..bushra.modals.staff_db import ClassTeacher, Teacher
from ..bushra.modals.subjects_db import Lesson, Subject
from ..bushra.modules.admin.services.staff_messages import (
    MessageError,
    can_send_messages,
    delete_sent_message,
    inbox_for,
    inbox_page,
    open_inbox_item,
    send_in_app,
    sent_for,
    sent_page,
    unread_count,
)
from ..bushra.modules.admin.utils.teacher_utils import hash_staff_password


@pytest.fixture()
def app(tmp_path, monkeypatch):
    uri = "sqlite:///" + str(tmp_path / "messages.db").replace("\\", "/")
    monkeypatch.setattr(DevelopmentConfig, "SQLALCHEMY_DATABASE_URI", uri)
    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def db(app):
    return _db


def _branch(db, name, code):
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


def _teacher(db, branch, phone, fullname, **flags):
    teacher = Teacher(
        branch_id=branch.id,
        employer="TSC",
        fullname=fullname,
        gender="M",
        title="Mr.",
        phone=phone,
        username=f"user{phone[-4:]}",
        password_hash=hash_staff_password("secret12"),
        is_admin=flags.get("is_admin", False),
        is_super_admin=flags.get("is_super_admin", False),
        is_system_admin=flags.get("is_system_admin", False),
    )
    db.session.add(teacher)
    db.session.flush()
    return teacher


def test_in_app_send_open_and_history(app, db):
    school = _branch(db, "Bushra Academy", "BA01")
    sender = _teacher(db, school, "0711000001", "Admin One", is_admin=True)
    recipient = _teacher(db, school, "0711000002", "Teacher Two")
    db.session.commit()

    message = send_in_app(
        sender,
        branch_id=school.id,
        audience="teacher",
        title="Staff meeting",
        body="Meet at the hall after classes.",
        teacher_id=recipient.id,
    )

    assert unread_count(recipient) == 1
    assert unread_count(sender) == 0
    sent = sent_for(sender)
    assert sent[0]["sent_count"] == 1
    assert sent[0]["opened_count"] == 0

    item = inbox_for(recipient)[0]
    open_inbox_item(recipient, item.id)
    assert unread_count(recipient) == 0
    opened = StaffMessageRecipient.query.filter_by(message_id=message.id).one()
    assert opened.opened_at is not None
    assert sent_for(sender)[0]["opened_count"] == 1


def test_sender_can_delete_a_message_from_every_inbox(app, db):
    school = _branch(db, "Delete Academy", "DA01")
    sender = _teacher(db, school, "0711000031", "Sender Admin", is_admin=True)
    other = _teacher(db, school, "0711000032", "Other Admin", is_admin=True)
    recipient = _teacher(db, school, "0711000033", "Inbox Teacher")
    db.session.commit()

    message = send_in_app(
        sender,
        branch_id=school.id,
        audience="teacher",
        title="Withdraw this",
        body="Sent by mistake.",
        teacher_id=recipient.id,
    )
    item = inbox_for(recipient)[0]
    open_inbox_item(recipient, item.id)
    assert unread_count(recipient) == 0

    assert delete_sent_message(other, message.id) is False
    assert inbox_for(recipient)

    client = app.test_client()
    with client.session_transaction() as session:
        session["_user_id"] = str(sender.id)
        session["_fresh"] = True

    detail = client.get(f"/admin/messages/sent/{message.id}")
    page = detail.get_data(as_text=True)
    assert "Delete message" in page
    assert "disappear from every inbox" in page

    blocked = client.get(f"/admin/messages/sent/{message.id}/delete")
    assert blocked.status_code == 405
    assert StaffMessage.query.get(message.id) is not None

    response = client.post(f"/admin/messages/sent/{message.id}/delete")
    assert response.status_code == 302
    assert "tab=sent" in response.location
    follow = client.get(response.location)
    assert "Message deleted." in follow.get_data(as_text=True)
    assert inbox_for(recipient) == []
    assert sent_for(sender) == []
    assert StaffMessage.query.get(message.id) is None
    assert (
        StaffMessageRecipient.query.filter_by(message_id=message.id).count() == 0
    )


def test_sms_is_not_sent(app, db):
    school = _branch(db, "Fafi Academy", "FA01")
    sender = _teacher(db, school, "0711000011", "Admin", is_admin=True)
    other = _teacher(db, school, "0711000012", "Other")
    db.session.commit()

    with pytest.raises(MessageError, match="SMS"):
        send_in_app(
            sender,
            branch_id=school.id,
            audience="teacher",
            title="Result",
            body="Please check.",
            teacher_id=other.id,
            channel="sms",
        )
    assert inbox_for(other) == []


def test_only_admins_can_send(app, db):
    school = _branch(db, "Ihsan Academy", "IA01")
    grade = BranchClasses(
        branch_id=school.id,
        class_year="2026",
        grade_form="Grade 7",
        streams=["East", "West"],
    )
    db.session.add(grade)
    db.session.flush()
    class_teacher = _teacher(db, school, "0711000021", "Class Teacher")
    admin = _teacher(db, school, "0711000023", "School Admin", is_admin=True)
    east_teacher = _teacher(db, school, "0711000022", "East Teacher")
    db.session.add(
        ClassTeacher(
            branch_id=school.id,
            class_id=grade.id,
            stream="East",
            teacher_id=class_teacher.id,
        )
    )
    subject = Subject(name="English", code="ENG7", category="Core")
    db.session.add(subject)
    db.session.flush()
    db.session.add(
        Lesson(
            branch_id=school.id,
            class_id=grade.id,
            stream="East",
            subject_id=subject.id,
            teacher_id=east_teacher.id,
        )
    )
    db.session.commit()

    with pytest.raises(MessageError, match="cannot send"):
        send_in_app(
            class_teacher,
            branch_id=school.id,
            audience="class",
            title="Homework",
            body="Collect the books.",
            class_value=f"{grade.id}|East",
        )

    message = send_in_app(
        admin,
        branch_id=school.id,
        audience="class",
        title="Homework",
        body="Collect the books.",
        class_value=f"{grade.id}|East",
    )
    names = {row.teacher.fullname for row in message.recipients}
    assert names == {"Class Teacher", "East Teacher"}


def test_cannot_message_a_teacher_in_another_school(app, db):
    home = _branch(db, "Home School", "HS01")
    other = _branch(db, "Other School", "OS01")
    sender = _teacher(db, home, "0711000031", "Home Admin", is_admin=True)
    outsider = _teacher(db, other, "0711000032", "Outsider")
    db.session.commit()

    with pytest.raises(MessageError):
        send_in_app(
            sender,
            branch_id=other.id,
            audience="teacher",
            title="Hello",
            body="You should not get this.",
            teacher_id=outsider.id,
        )


def test_system_admin_can_message_every_school(app, db):
    first = _branch(db, "First Academy", "FA11")
    second = _branch(db, "Second Academy", "SA11")
    sender = _teacher(
        db, first, "0711000041", "Platform Admin", is_system_admin=True
    )
    home_teacher = _teacher(db, first, "0711000042", "Home Teacher")
    away_teacher = _teacher(db, second, "0711000043", "Away Teacher")
    school_admin = _teacher(db, first, "0711000044", "School Admin", is_admin=True)
    db.session.commit()

    message = send_in_app(
        sender,
        branch_id="all",
        audience="school",
        title="Platform notice",
        body="This reaches every school.",
    )

    assert message.branch_id is None
    assert message.audience_label == "All users, every school"
    names = {row.teacher.fullname for row in message.recipients}
    assert names == {"Home Teacher", "Away Teacher", "School Admin"}

    with pytest.raises(MessageError, match="system admin"):
        send_in_app(
            school_admin,
            branch_id="all",
            audience="school",
            title="Not allowed",
            body="A school admin cannot message every school.",
        )


def test_system_admin_can_message_admins_or_super_admins(app, db):
    first = _branch(db, "North Academy", "NA11")
    second = _branch(db, "South Academy", "SO11")
    sender = _teacher(
        db, first, "0711000051", "Platform Admin", is_system_admin=True
    )
    school_admin = _teacher(db, second, "0711000052", "School Admin", is_admin=True)
    super_admin = _teacher(
        db, first, "0711000053", "Super Admin", is_super_admin=True
    )
    teacher = _teacher(db, second, "0711000054", "Ordinary Teacher")
    db.session.commit()

    admins = send_in_app(
        sender,
        branch_id="all",
        audience="admins",
        title="For admins",
        body="School admins only.",
    )
    assert {row.teacher.fullname for row in admins.recipients} == {"School Admin"}
    assert admins.audience_label == "Admins, every school"

    supers = send_in_app(
        sender,
        branch_id="all",
        audience="super_admins",
        title="For super admins",
        body="Super admins only.",
    )
    assert {row.teacher.fullname for row in supers.recipients} == {"Super Admin"}
    assert supers.audience_label == "Super admins, every school"
    assert inbox_for(teacher) == []


def test_successful_send_returns_to_compose_with_flash(app, db):
    school = _branch(db, "Flash Academy", "FL01")
    sender = _teacher(db, school, "0711000061", "Flash Admin", is_admin=True)
    recipient = _teacher(db, school, "0711000062", "Flash Teacher")
    db.session.commit()

    client = app.test_client()
    with client.session_transaction() as session:
        session["_user_id"] = str(sender.id)
        session["_fresh"] = True

    response = client.post(
        "/admin/messages",
        data={
            "branch_id": school.id,
            "audience": "teacher",
            "teacher_id": recipient.id,
            "title": "Hello",
            "body": "Sent from the form.",
            "channel": "in_app",
        },
    )

    assert response.status_code == 302
    assert "/admin/messages/sent/" not in response.location
    assert "tab=compose" in response.location

    page = client.get(response.location)
    body = page.get_data(as_text=True)
    assert "Message sent." in body
    assert 'name="title"' in body
    assert "Sent from the form." not in body


def test_senders_open_messages_on_compose(app, db):
    school = _branch(db, "Compose Academy", "CA01")
    admin = _teacher(db, school, "0711000093", "Composer", is_admin=True)
    db.session.commit()

    client = app.test_client()
    with client.session_transaction() as session:
        session["_user_id"] = str(admin.id)
        session["_fresh"] = True

    response = client.get("/admin/messages")
    assert response.status_code == 302
    assert "tab=compose" in response.location

    page = client.get("/admin/messages?tab=inbox")
    text = page.get_data(as_text=True)
    assert page.status_code == 200
    assert "Your inbox is empty." in text
    assert "Compose a message" not in text


def test_receivers_land_on_the_inbox_without_tabs(app, db):
    school = _branch(db, "Reader Academy", "RA01")
    teacher = _teacher(db, school, "0711000091", "Reader")
    admin = _teacher(db, school, "0711000092", "Sender", is_admin=True)
    db.session.commit()

    client = app.test_client()
    with client.session_transaction() as session:
        session["_user_id"] = str(teacher.id)
        session["_fresh"] = True
    page = client.get("/admin/messages")
    text = page.get_data(as_text=True)
    assert page.status_code == 200
    assert "msg-tabs" not in text
    assert "Your inbox is empty." in text
    sent = client.get("/admin/messages?tab=sent")
    assert sent.status_code == 200
    assert "msg-tabs" not in sent.get_data(as_text=True)
    assert can_send_messages(admin)
    assert not can_send_messages(teacher)


def test_inbox_and_sent_lists_are_paged(app, db):
    school = _branch(db, "Page Academy", "PA01")
    sender = _teacher(db, school, "0711000071", "Page Admin", is_admin=True)
    recipient = _teacher(db, school, "0711000072", "Page Teacher")
    db.session.commit()

    for number in range(1, 4):
        send_in_app(
            sender,
            branch_id=school.id,
            audience="teacher",
            title="Notice %s" % number,
            body="Body %s" % number,
            teacher_id=recipient.id,
        )

    first = inbox_page(recipient, 1, per_page=2)
    second = inbox_page(recipient, 2, per_page=2)
    assert first.total == 3
    assert [item.message.title for item in first.items] == ["Notice 3", "Notice 2"]
    assert [item.message.title for item in second.items] == ["Notice 1"]

    sent = sent_page(sender, 1, per_page=2)
    assert sent.total == 3
    assert sent.pages == 2
    assert [row["message"].title for row in sent.items] == ["Notice 3", "Notice 2"]
    assert len(inbox_for(recipient)) == 3
    assert len(sent_for(sender)) == 3
