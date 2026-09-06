"""School SMS: Kenya numbers, merge fields, audience, and send."""

from __future__ import annotations

import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import date

from flask import current_app
from flask_login import current_user

from ....modals import db
from ....modals.branches_db import Branch, BranchClasses
from ....modals.sms_db import SmsMessage, SmsRecipient, SmsSettings, SmsTemplate
from ....modals.staff_db import Teacher
from ....modals.students_db import Student
from .grades import filter_active_classes, live_class_name


MAX_SMS_PARTS = 3
GSM_CHARSET = (
    "@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?"
    "¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà"
)
GSM_EXT = "^{}\\[~]|€"
TOKEN_RE = re.compile(r"\{([a-z_]+)\}")

DEFAULT_TEMPLATES = (
    {
        "name": "School opening",
        "purpose": "notice",
        "for_teachers": False,
        "body": "{school}: {student_name} ({class}) — school opens on {date}. Please be on time.",
    },
    {
        "name": "Collect report card",
        "purpose": "reports_ready",
        "for_teachers": False,
        "body": "{school}: {student_name}'s report is ready. Please collect it from the office.",
    },
    {
        "name": "Class meeting",
        "purpose": "notice",
        "for_teachers": False,
        "body": "{school}: class meeting for {class}. The class teacher will share the time.",
    },
    {
        "name": "Staff notice",
        "purpose": "staff",
        "for_teachers": True,
        "body": "{school} staff notice: ",
    },
)

PURPOSE_LABELS = {
    "notice": "General notice",
    "reminder": "Reminder",
    "reports_ready": "Reports are ready",
    "staff": "Staff notice",
    "custom": "Custom",
}


def kenya_mobile(phone):
    """Return 2547XXXXXXXX / 2541XXXXXXXX, or empty if not a Kenya mobile."""
    digits = "".join(ch for ch in str(phone or "") if ch.isdigit())
    if digits.startswith("254") and len(digits) == 12 and digits[3] in "17":
        return digits
    if digits.startswith("0") and len(digits) == 10 and digits[1] in "17":
        return "254" + digits[1:]
    if len(digits) == 9 and digits[0] in "17":
        return "254" + digits
    return ""


def display_phone(phone):
    if not phone:
        return ""
    if phone.startswith("254") and len(phone) == 12:
        return "0" + phone[3:]
    return phone


def is_gsm_text(text):
    return all(ch in GSM_CHARSET or ch in GSM_EXT for ch in text or "")


def sms_parts(text):
    text = text or ""
    if not text:
        return 0, True, 0
    gsm = is_gsm_text(text)
    length = 0
    if gsm:
        for ch in text:
            length += 2 if ch in GSM_EXT else 1
        limit = 160 if length <= 160 else 153
    else:
        length = len(text)
        limit = 70 if length <= 70 else 67
    parts = 1 if length == 0 else (length + limit - 1) // limit
    return parts, gsm, length


def render_body(template, fields):
    def replace(match):
        key = match.group(1)
        value = fields.get(key)
        if value is None or str(value).strip() == "":
            return ""
        return str(value).strip()

    text = TOKEN_RE.sub(replace, template or "")
    return re.sub(r"[ \t]{2,}", " ", text).strip()


def leftover_tokens(text):
    return TOKEN_RE.findall(text or "")


def provider_configured():
    return bool(
        os.environ.get("AFRICASTALKING_USERNAME")
        and os.environ.get("AFRICASTALKING_API_KEY")
    )


def get_or_create_settings(branch_id):
    settings = SmsSettings.query.filter_by(branch_id=branch_id).first()
    changed = False
    if not settings:
        settings = SmsSettings(
            branch_id=branch_id,
            sender_name=None,
            allow_class_teachers=True,
            credits=0,
            enabled=True,
        )
        db.session.add(settings)
        db.session.flush()
        changed = True
    before = SmsTemplate.query.filter_by(branch_id=branch_id).count()
    _ensure_templates(branch_id)
    if changed or SmsTemplate.query.filter_by(branch_id=branch_id).count() != before:
        db.session.commit()
    return settings


def _ensure_templates(branch_id):
    existing = SmsTemplate.query.filter_by(branch_id=branch_id).count()
    if existing:
        return
    for item in DEFAULT_TEMPLATES:
        db.session.add(
            SmsTemplate(
                branch_id=branch_id,
                name=item["name"],
                purpose=item["purpose"],
                body=item["body"],
                for_teachers=item["for_teachers"],
            )
        )


def class_streams(class_obj):
    streams = getattr(class_obj, "streams", None) or []
    if isinstance(streams, str):
        import json

        try:
            streams = json.loads(streams)
        except ValueError:
            streams = [s.strip() for s in streams.split(",") if s.strip()]
    return [str(s).strip() for s in streams if str(s).strip()]


def merge_fields_for_student(student, branch, class_obj=None):
    class_obj = class_obj or student.class_info
    class_name = live_class_name(class_obj.grade_form) if class_obj else ""
    stream = (student.stream or "").strip()
    parent = (student.parent_fullname or "").strip()
    student_name = (student.fullname or "").strip()
    if parent:
        parent_label = parent
    elif student_name:
        parent_label = f"Parent of {student_name}"
    else:
        parent_label = "Parent"
    return {
        "parent_name": parent_label,
        "student_name": student_name,
        "class": f"{class_name} {stream}".strip(),
        "stream": stream,
        "school": (branch.branch_name if branch else "").strip(),
        "exam": "",
        "date": date.today().strftime("%d %b %Y"),
        "teacher_name": "",
    }


def merge_fields_for_teacher(teacher, branch):
    return {
        "parent_name": "",
        "student_name": "",
        "class": "",
        "stream": "",
        "school": (branch.branch_name if branch else "").strip(),
        "exam": "",
        "date": date.today().strftime("%d %b %Y"),
        "teacher_name": (teacher.fullname or "").strip(),
    }


def _recipient_from_student(student, branch, class_obj=None):
    class_obj = class_obj or student.class_info
    class_name = live_class_name(class_obj.grade_form) if class_obj else ""
    stream = (student.stream or "").strip()
    detail = f"{class_name} {stream}".strip() or "Learner"
    raw = (student.parent_phone or "").strip()
    phone = kenya_mobile(raw)
    parent = (student.parent_fullname or "").strip()
    name = parent or (student.fullname or "Learner")
    if not raw:
        status, reason = "skipped", "No parent phone"
    elif not phone:
        status, reason = "skipped", "Not a Kenya mobile number"
    else:
        status, reason = "ready", None
    return {
        "key": f"student:{student.id}",
        "recipient_type": "parent",
        "student_id": student.id,
        "teacher_id": None,
        "display_name": name,
        "detail": f"{student.fullname} · {detail}" if student.fullname else detail,
        "phone_raw": raw,
        "phone": phone,
        "status": status,
        "skip_reason": reason,
        "fields": merge_fields_for_student(student, branch, class_obj),
    }


def _recipient_from_teacher(teacher, branch):
    raw = (teacher.phone or "").strip()
    phone = kenya_mobile(raw)
    if not raw:
        status, reason = "skipped", "No phone"
    elif not phone:
        status, reason = "skipped", "Not a Kenya mobile number"
    else:
        status, reason = "ready", None
    role = "Admin" if teacher.is_admin else "Teacher"
    return {
        "key": f"teacher:{teacher.id}",
        "recipient_type": "teacher",
        "student_id": None,
        "teacher_id": teacher.id,
        "display_name": teacher.fullname or "Teacher",
        "detail": role,
        "phone_raw": raw,
        "phone": phone,
        "status": status,
        "skip_reason": reason,
        "fields": merge_fields_for_teacher(teacher, branch),
    }


def build_audience(branch_id, audience_type, class_id=None, stream=None, student_id=None):
    branch = Branch.query.get(branch_id)
    if not branch:
        raise ValueError("School not found")

    audience_type = (audience_type or "").strip()
    stream = (stream or "").strip() or None
    rows = []
    label = branch.branch_name

    if audience_type == "parent_one":
        student = Student.query.get(student_id)
        if not student or student.branch_id != int(branch_id):
            raise ValueError("That learner is not in this school.")
        rows = [_recipient_from_student(student, branch)]
        label = student.fullname or "One parent"
    elif audience_type == "parents_class":
        class_obj = BranchClasses.query.get(class_id)
        if not class_obj or class_obj.branch_id != int(branch_id):
            raise ValueError("Choose a class.")
        query = Student.query.filter_by(branch_id=branch_id, class_id=class_obj.id)
        if stream:
            query = query.filter_by(stream=stream)
        students = query.order_by(Student.fullname.asc()).all()
        rows = [_recipient_from_student(s, branch, class_obj) for s in students]
        class_name = live_class_name(class_obj.grade_form)
        label = f"{class_name} {stream}".strip() + " parents"
    elif audience_type == "parents_school":
        classes = filter_active_classes(
            BranchClasses.query.filter_by(branch_id=branch_id).all()
        )
        class_ids = [c.id for c in classes]
        if class_ids:
            students = (
                Student.query.filter(
                    Student.branch_id == branch_id,
                    Student.class_id.in_(class_ids),
                )
                .order_by(Student.fullname.asc())
                .all()
            )
            rows = [_recipient_from_student(s, branch) for s in students]
        label = f"All parents · {branch.branch_name}"
    elif audience_type == "teachers":
        teachers = (
            Teacher.query.filter_by(branch_id=branch_id)
            .order_by(Teacher.fullname.asc())
            .all()
        )
        rows = [_recipient_from_teacher(t, branch) for t in teachers]
        label = f"Teachers · {branch.branch_name}"
    else:
        raise ValueError("Choose who should receive this message.")

    return {"label": label, "recipients": rows, "branch_name": branch.branch_name}


def apply_body(recipients, body):
    ready = []
    skipped = []
    for row in recipients:
        item = dict(row)
        if item["status"] != "ready":
            skipped.append(item)
            continue
        text = render_body(body, item.get("fields") or {})
        leftovers = leftover_tokens(text)
        if leftovers:
            item["status"] = "skipped"
            item["skip_reason"] = "Message still has unfilled fields"
            skipped.append(item)
            continue
        if not text:
            item["status"] = "skipped"
            item["skip_reason"] = "Message is empty for this person"
            skipped.append(item)
            continue
        parts, gsm, length = sms_parts(text)
        if parts > MAX_SMS_PARTS:
            item["status"] = "skipped"
            item["skip_reason"] = f"Longer than {MAX_SMS_PARTS} SMS"
            skipped.append(item)
            continue
        item["body"] = text
        item["parts"] = parts
        item["gsm"] = gsm
        item["length"] = length
        ready.append(item)
    return ready, skipped


def _deliver(phone, text, sender_name):
    if not provider_configured():
        return "logged", None
    username = os.environ.get("AFRICASTALKING_USERNAME")
    api_key = os.environ.get("AFRICASTALKING_API_KEY")
    payload = {
        "username": username,
        "to": "+" + phone,
        "message": text,
    }
    if sender_name:
        payload["from"] = sender_name
    data = urllib.parse.urlencode(payload).encode("utf-8")
    request = urllib.request.Request(
        "https://api.africastalking.com/version1/messaging",
        data=data,
        headers={
            "apiKey": api_key,
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            if 200 <= response.status < 300:
                return "sent", None
            return "failed", f"Provider returned {response.status}"
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="ignore")[:200]
        return "failed", detail or str(error)
    except Exception as error:
        current_app.logger.exception("SMS provider error")
        return "failed", str(error)[:200]


def send_message(
    *,
    branch_id,
    sender,
    audience_type,
    body,
    purpose="custom",
    class_id=None,
    stream=None,
    student_id=None,
    exclude_keys=None,
):
    body = (body or "").strip()
    if not body:
        raise ValueError("Write a message first.")

    settings = get_or_create_settings(branch_id)
    if not settings.enabled:
        raise ValueError("SMS is turned off for this school.")

    audience = build_audience(
        branch_id,
        audience_type,
        class_id=class_id,
        stream=stream,
        student_id=student_id,
    )
    exclude = set(exclude_keys or [])
    chosen = []
    left_out = []
    for row in audience["recipients"]:
        if row["key"] in exclude:
            item = dict(row)
            item["status"] = "skipped"
            item["skip_reason"] = "Left out of this send"
            left_out.append(item)
        else:
            chosen.append(row)
    ready, skipped = apply_body(chosen, body)
    skipped = left_out + skipped
    if not ready:
        raise ValueError("No one can receive this SMS. Check phone numbers and the message.")

    credits_needed = sum(row["parts"] for row in ready)
    if settings.credits < credits_needed:
        raise ValueError(
            f"Not enough SMS credit. This send needs {credits_needed} SMS; "
            f"{settings.credits} left."
        )

    uses_unicode = any(not row.get("gsm", True) for row in ready)
    if uses_unicode:
        pass  # still allowed; UI already warns

    message = SmsMessage(
        branch_id=branch_id,
        sender_id=sender.id if sender else None,
        purpose=purpose or "custom",
        audience_type=audience_type,
        audience_label=audience["label"],
        class_id=class_id,
        stream=(stream or "").strip() or None,
        student_id=student_id,
        body=body,
        status="queued",
        provider="africastalking" if provider_configured() else "log",
        credits_used=0,
        ready_count=len(ready),
        skipped_count=len(skipped),
    )
    db.session.add(message)
    db.session.flush()

    for row in skipped:
        db.session.add(
            SmsRecipient(
                message_id=message.id,
                recipient_type=row["recipient_type"],
                student_id=row.get("student_id"),
                teacher_id=row.get("teacher_id"),
                display_name=row["display_name"],
                detail=row.get("detail"),
                phone_raw=row.get("phone_raw"),
                phone=row.get("phone") or None,
                status="skipped",
                skip_reason=row.get("skip_reason"),
                parts=0,
            )
        )

    sent = 0
    failed = 0
    logged = 0
    used = 0
    sender_name = (settings.sender_name or "").strip() or None

    for row in ready:
        status, error = _deliver(row["phone"], row["body"], sender_name)
        if status in ("sent", "logged"):
            used += row["parts"]
            if status == "sent":
                sent += 1
            else:
                logged += 1
        else:
            failed += 1
        db.session.add(
            SmsRecipient(
                message_id=message.id,
                recipient_type=row["recipient_type"],
                student_id=row.get("student_id"),
                teacher_id=row.get("teacher_id"),
                display_name=row["display_name"],
                detail=row.get("detail"),
                phone_raw=row.get("phone_raw"),
                phone=row.get("phone"),
                status=status,
                body=row["body"],
                parts=row["parts"],
                error=error,
            )
        )

    settings.credits = max(0, settings.credits - used)
    message.credits_used = used
    message.sent_count = sent + logged
    message.failed_count = failed
    if failed and (sent or logged):
        message.status = "partial"
    elif failed:
        message.status = "failed"
    elif logged and not sent:
        message.status = "logged"
    else:
        message.status = "sent"
    db.session.commit()
    return message


def resend_failed(message, sender=None):
    settings = get_or_create_settings(message.branch_id)
    failed_rows = [row for row in message.recipients if row.status == "failed" and row.phone]
    if not failed_rows:
        raise ValueError("There are no failed numbers to resend.")
    credits_needed = sum(row.parts or 1 for row in failed_rows)
    if settings.credits < credits_needed:
        raise ValueError(
            f"Not enough SMS credit to resend ({credits_needed} SMS needed)."
        )
    sender_name = (settings.sender_name or "").strip() or None
    sent = 0
    still_failed = 0
    logged = 0
    used = 0
    for row in failed_rows:
        status, error = _deliver(row.phone, row.body or message.body, sender_name)
        row.status = status
        row.error = error
        if status in ("sent", "logged"):
            used += row.parts or 1
            if status == "sent":
                sent += 1
            else:
                logged += 1
        else:
            still_failed += 1
    settings.credits = max(0, settings.credits - used)
    message.credits_used += used
    message.failed_count = still_failed
    message.sent_count = (message.sent_count or 0) + sent + logged
    if still_failed and (sent or logged):
        message.status = "partial"
    elif still_failed:
        message.status = "failed"
    elif logged and not sent and message.status == "logged":
        message.status = "logged"
    else:
        message.status = "sent"
    db.session.commit()
    return message


def add_credits(branch_id, amount):
    amount = int(amount)
    if amount == 0:
        raise ValueError("Enter a credit amount.")
    settings = get_or_create_settings(branch_id)
    next_value = settings.credits + amount
    if next_value < 0:
        raise ValueError("Credits cannot go below zero.")
    settings.credits = next_value
    db.session.commit()
    return settings


def status_label(status):
    return {
        "queued": "Queued",
        "sent": "Sent",
        "logged": "Saved (not on phones yet)",
        "partial": "Some failed",
        "failed": "Failed",
        "skipped": "Skipped",
        "ready": "Will send",
    }.get(status, status)


def can_access_sms(user):
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_admin", False):
        return True
    return bool(getattr(user, "class_teacher_assignments", None))
